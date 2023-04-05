import { Database, DataSnapshot } from "firebase-admin/database";
import { DebugProtocol } from '@vscode/debugprotocol';
import { CdbgBreakpoint } from "./breakpoint";
import { InitialActiveBreakpoints } from "./initialActiveBreakpoints";
import { sleep, sourceBreakpointToString } from "./util";
import { LineMappings } from "./lineMappings";

export class BreakpointManager {
    private lineMappings: LineMappings = new LineMappings();
    private breakpoints: Map<string, CdbgBreakpoint> = new Map();
    private initialActiveBreakpoints?: InitialActiveBreakpoints;

    public constructor(readonly debuggeeId: string, readonly db: Database) {}

    public onNewBreakpoint?: ((bp: CdbgBreakpoint) => void);
    public onChangedBreakpoint?: ((bp: CdbgBreakpoint, originalLine: number) => void);
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

    // Here the sourecBreatkpointString argument is a string obtained by the
    // sourceBreakpointToString utility function.
    public getBreakpointBySourceBreakpointString(sourceBreakpointString: string): CdbgBreakpoint | undefined {
        for (let [bpId, cdbgBreakpoint] of this.breakpoints) {
            if (sourceBreakpointToString(cdbgBreakpoint.ideBreakpoint) === sourceBreakpointString) {
                return cdbgBreakpoint;
            }
        }

        return undefined;
    }

    // Here the locationString argument is a string obtained by the
    // CdbgBreakpoint.locationString() method.
    public getBreakpointByLocation(locationString: string): CdbgBreakpoint | undefined {
        for (let [bpId, cdbgBreakpoint] of this.breakpoints) {
            if (cdbgBreakpoint.locationString === locationString) {
                return cdbgBreakpoint;
            }
        }

        return undefined;
    }

    public getLineMapping(path: string, line: number): number|undefined {
        return this.lineMappings.get(path, line);
    }

    public async loadServerBreakpoints() {
        const activeBreakpointRef = this.db.ref(`cdbg/breakpoints/${this.debuggeeId}/active`);
        const activeSnapshot: DataSnapshot = await activeBreakpointRef.get();
        this.initialActiveBreakpoints = new InitialActiveBreakpoints(activeSnapshot);
        console.log('Active breakpoints loaded from server');
    }

    public setUpServerListeners() {
        const activeBreakpointRef = this.db.ref(`cdbg/breakpoints/${this.debuggeeId}/active`);

        activeBreakpointRef.on(
            'child_changed',
            async (snapshot: DataSnapshot) => {
                const bpId = snapshot.key!;
                console.log(`breakpoint changed on server: ${snapshot.key}`);
                this.handleActiveBreakpointUpdate(CdbgBreakpoint.fromSnapshot(snapshot));
            });

        activeBreakpointRef.on(
            'child_removed',
            async (snapshot: DataSnapshot) => {
                const bpId = snapshot.key!;
                console.log(`breakpoint removed from server: ${snapshot.key}`);

                const bp = this.breakpoints.get(bpId);

                // We check if the bp is active or not. One situation where we may have
                // the BP but it's already finalized is the case of a changed breakpoint
                // where the agent notifies us that the line number changed. We  may
                // have already locally failed that BP if the UI already had a BP at
                // the line the BP was changed to.
                if (bp && bp.isActive()) {
                    // Breakpoint finalized server-side.  Find out what to do next by loading /snapshot on the breakpoint.
                    await this.loadSnapshotDetails(bpId);
                    if (this.onCompletedBreakpoint) { this.onCompletedBreakpoint(this.getBreakpoint(bpId)!); }
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
        console.log(`creating new breakpoint in firebase: ${bpId}`);
        breakpoint.id = bpId;
        breakpoint.localBreakpoint.id = numericId;
        breakpoint.serverBreakpoint.createTimeUnixMsec = { '.sv': 'timestamp' };
        breakpoint.hasUnsavedData = true;
        this.breakpoints.set(bpId, breakpoint);
        this.db?.ref(`cdbg/breakpoints/${this.debuggeeId}/active/${bpId}`).set(breakpoint.serverBreakpoint);
        console.log(this.breakpoints);
    }

    public deleteBreakpointLocally(id: string): void {
        this.breakpoints.delete(id);
    }

    public deleteBreakpointFromServer(bpId: string): void {
        console.log(`deleting breakpoint from server: ${bpId}`);
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
        console.log(`adding initial breakpoint ${bpId}, state: ${breakpoint.isActive() ? 'active' : 'final'}`);
        this.breakpoints.set(bpId, breakpoint);
        console.log(this.breakpoints);
    }

    private addServerBreakpoint(breakpoint: CdbgBreakpoint): void {
        const bpId = breakpoint.id!;
        console.log(this.breakpoints);
        if (this.breakpoints.has(bpId)) {
            const bp = this.breakpoints.get(bpId)!;
            console.log(`Breakpoint was already set; replacing server breakpoint data for ${bpId}`);
            // This is completing the flow of a user setting a breakpoint in the UI, saving to db, and getting a confirmed update.
            bp.serverBreakpoint = breakpoint.serverBreakpoint;
            bp.hasUnsavedData = false;
        } else {
            console.log(`New breakpoint from unknown source: ${bpId}`);
            this.breakpoints.set(bpId, breakpoint);
            if (this.onNewBreakpoint) { this.onNewBreakpoint(breakpoint); }
        }
    }

    private async loadSnapshotDetails(bpId: string): Promise<void> {
        // Just try loading it from the /snapshot table.
        console.log('loading snapshot details');
        const snapshotRef = this.db!.ref(`cdbg/breakpoints/${this.debuggeeId}/snapshot/${bpId}`);
        let dataSnapshot: DataSnapshot = await snapshotRef.get();
        let retryCount = 0;
        while (!dataSnapshot.val() && retryCount < 4) {
            await (sleep(250));
            dataSnapshot = await snapshotRef.get();
            retryCount += 1;
            console.log(`retrying: ${retryCount}`);
        }
        if (dataSnapshot.val()) {
            this.breakpoints.get(bpId)!.updateServerData(dataSnapshot);
            console.log(`Loaded snapshot details for ${bpId}`);
            console.log(this.breakpoints.get(bpId));
        } else {
            console.log(`Failed to load snapshot details for ${bpId}`);
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
            console.log("ERROR, unexpected call to scrub logpoint.")
        }

        cdbgBreakpoint.ideBreakpoint.condition = undefined;
        cdbgBreakpoint.serverBreakpoint.condition = undefined;
    }

    private handleActiveBreakpointUpdate(updatedBP: CdbgBreakpoint) {
        console.log(updatedBP);
        const currentBP = this.breakpoints.get(updatedBP.id);

        // There are two types of changes we expect on an active breakpoint .
        // 1. createActive
        // is the line
        // number, which can occur if the agent found no code at the requested
        // line but it then chooses to set to the breakpoint on a nearby line
        // and sends an update indicating this. To note, not all agents
        // actually do this, some will simply fail the breakpoint request
        // with an error indicating not code was found  at the given line.
        // The Snapshot Debugger Java agent is an example of an agent known to
        // update the line in this manner.
        if (!currentBP || (currentBP.line === updatedBP.line)) {
            return;
        }

        if (this.getBreakpointByLocation(updatedBP.locationString) === undefined) {
            this.lineMappings.add(currentBP.path, currentBP.line, updatedBP.line);
            console.log(this.lineMappings);
            const originalLine = currentBP.line;
            currentBP.line = updatedBP.line;
            if (this.onChangedBreakpoint) { this.onChangedBreakpoint(currentBP, originalLine); }
        } else {
            currentBP.markFailedUnknownLocation();
            if (this.onCompletedBreakpoint) { this.onCompletedBreakpoint(currentBP); }
        }

    }
}
