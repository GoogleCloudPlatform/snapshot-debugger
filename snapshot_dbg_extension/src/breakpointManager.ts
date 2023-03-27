import { Database, DataSnapshot } from "firebase-admin/database";
import { DebugProtocol } from '@vscode/debugprotocol';
import { CdbgBreakpoint } from "./breakpoint";
import { sleep, sourceBreakpointToString } from "./util";

export class BreakpointManager {
    private breakpoints: Map<string, CdbgBreakpoint> = new Map();

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
        for (let [bipId, cdbgBreakpoint] of this.breakpoints) {
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
        activeSnapshot.forEach((breakpoint) => this.addInitServerBreakpoint(CdbgBreakpoint.fromSnapshot(breakpoint)));
        console.log('Breakpoints loaded from server');
    }

    public setUpServerListeners() {
        const activeBreakpointRef = this.db.ref(`cdbg/breakpoints/${this.debuggeeId}/active`);

        activeBreakpointRef.on(
            'child_added',
            (snapshot: DataSnapshot) => {
                console.log(`new breakpoint received from server: ${snapshot.key}`);
                this.addServerBreakpoint(CdbgBreakpoint.fromSnapshot(snapshot));
            });
        activeBreakpointRef.on(
            'child_removed',
            async (snapshot: DataSnapshot) => {
                const bpId = snapshot.key!;
                console.log(`breakpoint removed from server: ${snapshot.key}`);

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
    // complete and full filled in. We just need to store it and get it reloaded in the UI.
    public loadCompleteSnapshot(cdbgBreakpoint: CdbgBreakpoint): void {
        const bpId = cdbgBreakpoint.id;
        this.breakpoints.set(bpId, cdbgBreakpoint);
        if (this.onNewBreakpoint) { this.onNewBreakpoint(cdbgBreakpoint); }
        if (this.onCompletedBreakpoint) { this.onCompletedBreakpoint(cdbgBreakpoint); }
    }

    initializeWithLocalBreakpoints(localBreakpoints: CdbgBreakpoint[]) {
        const bpIds = new Set<string>();  // Keep track of which breakpoints we've seen.
        for (const cdbgBreakpoint of localBreakpoints) {
            let found = false;
            for (const bp of this.getBreakpoints()) {
                // TODO: Handle multiple matches in a considered manner.  Not sure what's best to do right now.
                if (bp.matches(cdbgBreakpoint)) {
                    found = true;
                    bpIds.add(bp.id);  // Say that we've seen this breakpoint even if there's more than one match.
                }
            }

            if (!found) {
                // Server breakpoints should have already been loaded.
                console.log('did not find a matching breakpoint on server; creating a new one.');
                this.saveBreakpointToServer(cdbgBreakpoint);
            }
        }

        this.getBreakpoints().forEach((bp) => {
            if (!bpIds.has(bp.id)) {
                if (this.onNewBreakpoint) { this.onNewBreakpoint(bp) };
            }
        })
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

}
