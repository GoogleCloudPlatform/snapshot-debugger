import { Database, DataSnapshot } from "firebase-admin/database";
import { DebugProtocol } from '@vscode/debugprotocol';
import { CdbgBreakpoint } from "./breakpoint";
import { InitialActiveBreakpoints } from "./initialActiveBreakpoints";
import { sleep, sourceBreakpointToString } from "./util";
import { debugLog } from "./debugUtil";

export class BreakpointManager {
    private breakpoints: Map<string, CdbgBreakpoint> = new Map();
    private initialActiveBreakpoints?: InitialActiveBreakpoints;

    public constructor(readonly debuggeeId: string, readonly db: Database) {}

    public onNewBreakpoint?: ((bp: CdbgBreakpoint) => void);
    public onCompletedBreakpoint?: ((bp: CdbgBreakpoint) => void);

    public getBreakpointIds(): string[] {
        return [...this.breakpoints.keys()];
    }

    public getBreakpointsAtPath(path: string): CdbgBreakpoint[] {
        return [...this.breakpoints.values()].filter(bp => bp.path === path);
    }

    public getBreakpoints(): CdbgBreakpoint[] {
        return [...this.breakpoints.values()];
    }

    public getBreakpoint(id: string): CdbgBreakpoint | undefined {
        return this.breakpoints.get(id);
    }

    public getBreakpointBySourceBreakpoint(sourceBreakpoint: DebugProtocol.SourceBreakpoint): CdbgBreakpoint | undefined {
        return this.getBreakpointBySourceBreakpointString(sourceBreakpointToString(sourceBreakpoint));
    }

    public getBreakpointBySourceBreakpointString(sourceBreakpointString: string): CdbgBreakpoint | undefined {
        // TODO: May want to also add an extra breakpoint map indexed on source breakpoint string
        for (let [bpId, cdbgBreakpoint] of this.breakpoints) {
            if (sourceBreakpointToString(cdbgBreakpoint.ideBreakpoint) === sourceBreakpointString) {
                // TODO: Figure out what to do for duplicates, here we return first hit
                return cdbgBreakpoint;
            }
        }

        return undefined;
    }

    public async loadServerBreakpoints() {
        const activeBreakpointRef = this.db.ref(`cdbg/breakpoints/${this.debuggeeId}/active`);
        const activeSnapshot: DataSnapshot = await activeBreakpointRef.get();
        this.initialActiveBreakpoints = new InitialActiveBreakpoints(activeSnapshot);
        debugLog('Active breakpoints loaded from server');
    }

    public setUpServerListeners() {
        const activeBreakpointRef = this.db.ref(`cdbg/breakpoints/${this.debuggeeId}/active`);

        activeBreakpointRef.on(
            'child_removed',
            async (snapshot: DataSnapshot) => {
                const bpId = snapshot.key!;
                debugLog(`breakpoint removed from server: ${snapshot.key}`);

                if (this.breakpoints.has(bpId)) {
                    // Breakpoint finalized server-side.  Find out what to do next by loading /snapshot on the breakpoint.
                    await this.loadSnapshotDetails(bpId);
                    if (this.onCompletedBreakpoint) { this.onCompletedBreakpoint(this.getBreakpoint(bpId)!); }
                } else {
                    // Breakpoint removed from UI.  We should have already handled this in setBreakPointsRequest.
                    this.breakpoints.delete(bpId);
                }
            });

    }

    public async addHistoricalSnapshot(cdbgBreakpoint: CdbgBreakpoint): Promise<void> {
        const bpId = cdbgBreakpoint.id;
        this.addServerBreakpoint(cdbgBreakpoint);
        await this.loadSnapshotDetails(bpId);
        if (this.onCompletedBreakpoint) { this.onCompletedBreakpoint(this.getBreakpoint(bpId)!); }
    }

    // Supports the case of the step operations we don't support. The breakpoint passed in here is already
    // complete and fully filled in. We just need to store it and get it reloaded in the UI.
    public loadCompleteSnapshot(cdbgBreakpoint: CdbgBreakpoint): void {
        const bpId = cdbgBreakpoint.id;
        this.breakpoints.set(bpId, cdbgBreakpoint);
        if (this.onNewBreakpoint) { this.onNewBreakpoint(cdbgBreakpoint); }
        if (this.onCompletedBreakpoint) { this.onCompletedBreakpoint(cdbgBreakpoint); }
    }

    public initializeWithLocalBreakpoints(path: string, localBreakpoints: CdbgBreakpoint[]): void {
        const matches = this.initialActiveBreakpoints!.match(path, localBreakpoints);
        const linesSeen: Set<number> = new Set();
        for (let i = 0; i < localBreakpoints.length; i++) {
            const localBP = localBreakpoints[i];
            const matchedBP = matches[i];
            linesSeen.add(localBP.line!);
            if (matchedBP === undefined) {
                this.saveBreakpointToServer(localBP);
            } else {
                this.addInitServerBreakpoint(matchedBP);
            }
        }

        const newBPsForIDE = this.initialActiveBreakpoints!.getBreakpointsToSyncToIDEForPath(path, linesSeen);
        for (const bp of newBPsForIDE) {
            this.scrubBreakpointToSyncToIDE(bp);
            this.addInitServerBreakpoint(bp);
            if (this.onNewBreakpoint) { this.onNewBreakpoint(bp); }
        }
    }

    public syncInitialActiveBreakpointsToIDE(excludePaths: Set<string>) {
        const newBPsForIDE = this.initialActiveBreakpoints!.getBreakpointsToSyncToIDE(excludePaths);
        for (const bp of newBPsForIDE) {
            this.scrubBreakpointToSyncToIDE(bp);
            this.addInitServerBreakpoint(bp);
            if (this.onNewBreakpoint) { this.onNewBreakpoint(bp); }
        }
    }

    public saveBreakpointToServer(breakpoint: CdbgBreakpoint): void {
        const numericId = this.generateBreakpointId();
        const bpId = `b-${numericId}`;
        debugLog(`creating new breakpoint in firebase: ${bpId}`);
        breakpoint.id = bpId;
        breakpoint.localBreakpoint.id = numericId;
        breakpoint.serverBreakpoint.createTimeUnixMsec = { '.sv': 'timestamp' };
        breakpoint.hasUnsavedData = true;
        this.breakpoints.set(bpId, breakpoint);
        this.db?.ref(`cdbg/breakpoints/${this.debuggeeId}/active/${bpId}`).set(breakpoint.serverBreakpoint);
        debugLog(this.breakpoints);
    }

    public deleteBreakpointLocally(id: string): void {
        this.breakpoints.delete(id);
    }

    public deleteBreakpointFromServer(bpId: string): void {
        debugLog(`deleting breakpoint from server: ${bpId}`);
        this.breakpoints.delete(bpId);
        this.db?.ref(`cdbg/breakpoints/${this.debuggeeId}/active/${bpId}`).set(null);
    }

    /** Generate a safe numeric breakpoint ID for a new breakpoint.
     * Breakpoints generated in quick succession resulting in collisions.  This function avoids that. */
    private lastBreakpointId: number = 0;
    private generateBreakpointId(): number {
        let attempt = Math.floor(Date.now() / 1000);
        if (attempt <= this.lastBreakpointId) {
            attempt = this.lastBreakpointId + 1;
        }
        this.lastBreakpointId = attempt;
        return attempt;
    }

    private addInitServerBreakpoint(breakpoint: CdbgBreakpoint): void {
        const bpId = breakpoint.id!;
        debugLog(`adding initial breakpoint ${bpId}, state: ${breakpoint.isActive() ? 'active' : 'final'}`);
        this.breakpoints.set(bpId, breakpoint);
        debugLog(this.breakpoints);
    }

    private addServerBreakpoint(breakpoint: CdbgBreakpoint): void {
        const bpId = breakpoint.id!;
        debugLog(this.breakpoints);
        if (this.breakpoints.has(bpId)) {
            const bp = this.breakpoints.get(bpId)!;
            debugLog(`Breakpoint was already set; replacing server breakpoint data for ${bpId}`);
            // This is completing the flow of a user setting a breakpoint in the UI, saving to db, and getting a confirmed update.
            bp.serverBreakpoint = breakpoint.serverBreakpoint;
            bp.hasUnsavedData = false;
        } else {
            debugLog(`New breakpoint from unknown source: ${bpId}`);
            this.breakpoints.set(bpId, breakpoint);
            if (this.onNewBreakpoint) { this.onNewBreakpoint(breakpoint); }
        }
    }

    private async loadSnapshotDetails(bpId: string): Promise<void> {
        // Just try loading it from the /snapshot table.
        debugLog('loading snapshot details');
        const snapshotRef = this.db!.ref(`cdbg/breakpoints/${this.debuggeeId}/snapshot/${bpId}`);
        let dataSnapshot: DataSnapshot = await snapshotRef.get();
        let retryCount = 0;
        while (!dataSnapshot.val() && retryCount < 4) {
            await (sleep(250));
            dataSnapshot = await snapshotRef.get();
            retryCount += 1;
            debugLog(`retrying: ${retryCount}`);
        }
        if (dataSnapshot.val()) {
            this.breakpoints.get(bpId)!.updateServerData(dataSnapshot);
            debugLog(`Loaded snapshot details for ${bpId}`);
            debugLog(this.breakpoints.get(bpId));
        } else {
            debugLog(`Failed to load snapshot details for ${bpId}`);
            // TODO: Figure out how to fail gracefully.
        }
    }

    /**
     * Handles the scenario where at initial attach time, a breakpoint from the
     * backend gets added to the IDE (ie the IDE did not already have a
     * breakpoint listed at the location).  The DebbugProtocol.Breakpoint type
     * is used to transmit the  breakpoint to the IDE. This type does not
     * support some fields, like logMessage or conditions. The issue that arises
     * is on setBreakpointRequests that will then occur, the SourceBreakpoint it
     * passes in will be missing these fields, which will cause confusion when
     * performing matches, so we scrub these fields to avoid issues.
     *
     * @param cdbgBreakpoint breakpoint to scrub
     */
    private scrubBreakpointToSyncToIDE(cdbgBreakpoint: CdbgBreakpoint) {
        if (cdbgBreakpoint.isLogpoint()) {
            // Do to the limitation of the logMessage not being present in
            // DebugProtocol.Breakpoint we do not sync logpoints from the
            // backend to the IDE at initialization time.
            debugLog("ERROR, unexpected call to scrub logpoint.")
        }

        cdbgBreakpoint.ideBreakpoint.condition = undefined;
        cdbgBreakpoint.serverBreakpoint.condition = undefined;
    }
}
