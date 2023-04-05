import { DataSnapshot } from "firebase-admin/database";
import { LogpointMessage } from './logpointMessage';
import { CdbgBreakpoint } from "./breakpoint";
import { sourceBreakpointToString } from "./util";

class LineEntry {
    public logpoints: Array<CdbgBreakpoint> = [];
    public snapshots: Array<CdbgBreakpoint> = [];

    public add(cdbgBreakpoint: CdbgBreakpoint): void {
        if (cdbgBreakpoint.isSnapshot()) {
            this.snapshots.push(cdbgBreakpoint);
        } else {
            this.logpoints.push(cdbgBreakpoint);
        }
    }

    public match(cdbgBreakpoint: CdbgBreakpoint): CdbgBreakpoint|undefined {
        if (cdbgBreakpoint.isSnapshot()) {
            return this.matchSnapshot(cdbgBreakpoint);
        } else {
            return this.matchLogpoint(cdbgBreakpoint);
        }
    }

    public matchSnapshot(cdbgBreakpoint: CdbgBreakpoint): CdbgBreakpoint|undefined {
        // If there are multiple BPs, we have to choose only one, for
        // consistency we always choose the newest one.
        return this.newestBreakpoint(this.snapshots.filter(bp => this.doBreakpointsMatch(cdbgBreakpoint, bp)));
    }

    public matchLogpoint(cdbgBreakpoint: CdbgBreakpoint): CdbgBreakpoint|undefined {
        for (const bp of this.logpoints) {
            const logpointMessage = LogpointMessage.fromBreakpoint(bp.serverBreakpoint);
            if (logpointMessage.userMessage === cdbgBreakpoint.ideBreakpoint.logMessage) {
                return bp;
            }
        }

        return undefined;
    }

    public newestBreakpoint(breakpoints: CdbgBreakpoint[]): CdbgBreakpoint|undefined {
        let newestBP = breakpoints.length === 0 ? undefined : this.snapshots[0];
        for (const bp of breakpoints) {
            if (bp.createTimeUnixMsec > newestBP!.createTimeUnixMsec) {
                newestBP = bp;
            }
        }

        return newestBP;
    }

    public getBreakpointToSyncToIDE(): CdbgBreakpoint|undefined {
        // We only sync active snapshots to the IDE and not logpoints. We do
        // this because the DebugProtocol.Breakpoint type the adapter sends to
        // the IDE does not support a log message field, so it's not possible
        // to communicate to the IDE that a breakpoint is a logpoint.
        //
        // In addition, can only sync 1 breakpoint per line. For consistency we
        // use the newest snapshot for this.
        return this.newestBreakpoint(this.snapshots);
    }

    private doBreakpointsMatch(bp1: CdbgBreakpoint, bp2: CdbgBreakpoint): boolean {
        return sourceBreakpointToString(bp1.ideBreakpoint) === sourceBreakpointToString(bp2.ideBreakpoint);
    }
}

export class InitialActiveBreakpoints {
    constructor(activeSnapshot: DataSnapshot) {
        activeSnapshot.forEach((breakpoint) => {
            this.store(CdbgBreakpoint.fromSnapshot(breakpoint));
        });
    }

    public match(path: string, breakpoints: CdbgBreakpoint[]): Array<CdbgBreakpoint|undefined> {
        const response: Array <CdbgBreakpoint|undefined> = [];
        const backendBPs = this.breakpoints.get(path) ?? new Map();

        for (let i = 0; i < breakpoints.length; i++) {
            const lineEntry = backendBPs.get(breakpoints[i].line);
            response.push(lineEntry?.match(breakpoints[i]));
        }

        return response;
    }

    public getBreakpointsToSyncToIDEForPath(path: string, excludeLines: Set<number>): CdbgBreakpoint[] {
        const syncBPs: CdbgBreakpoint[] = [];
        const pathEntry = this.breakpoints.get(path) ?? new Map();
        for (let [line, lineEntry] of pathEntry) {
            if (!excludeLines.has(line)) {
                const bp = lineEntry.getBreakpointToSyncToIDE();
                if (bp) { syncBPs.push(bp); }
            }
        }

        return syncBPs;
    }

    public getBreakpointsToSyncToIDE(excludePaths: Set<string>): CdbgBreakpoint[] {
        let syncBPs: CdbgBreakpoint[] = [];
        const excludeLines = new Set<number>();
        for (let [path, pathEntry] of this.breakpoints) {
            if (!excludePaths.has(path)) {
                syncBPs = syncBPs.concat(this.getBreakpointsToSyncToIDEForPath(path, excludeLines));
            }
        }

        return syncBPs;
    }

    // First key is the breakpoint path (file), second key is the line number.
    private breakpoints: Map<string, Map<number, LineEntry>> = new Map();

    private store(cdbgBreakpoint: CdbgBreakpoint): void {
        let pathEntry = this.breakpoints.get(cdbgBreakpoint.path);
        if (!pathEntry) {
            pathEntry = new Map();
            this.breakpoints.set(cdbgBreakpoint.path, pathEntry);
        }

        let lineEntry = pathEntry.get(cdbgBreakpoint.line!);
        if (!lineEntry) {
            lineEntry = new LineEntry();
            pathEntry.set(cdbgBreakpoint.line!, lineEntry);
        }

        lineEntry.add(cdbgBreakpoint);
    }
}

