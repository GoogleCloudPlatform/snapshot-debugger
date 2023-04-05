import { DebugProtocol } from '@vscode/debugprotocol';
import { sourceBreakpointToString, stringToSourceBreakpoint } from './util';

export interface IdeBreakpointsDiff {
  added: DebugProtocol.SourceBreakpoint[];
  deleted: DebugProtocol.SourceBreakpoint[];
}

/**
 * Class for the adaptor to track the current breakpoints the IDE has.
 */
export class IdeBreakpoints {
    private breakpoints: Map<string, DebugProtocol.SourceBreakpoint[]> = new Map();

    public applyNewIdeSnapshot(path: string, newSnapshot: DebugProtocol.SourceBreakpoint[]): IdeBreakpointsDiff {
        const prevBPs: DebugProtocol.SourceBreakpoint[] = this.breakpoints.get(path) ?? [];
        const currBPs: DebugProtocol.SourceBreakpoint[] = newSnapshot;
        const prevBPSet = new Set(prevBPs.map(bp => sourceBreakpointToString(bp)));
        const currBPSet = new Set(currBPs.map(bp => sourceBreakpointToString(bp)));

        const newBPs = [...currBPSet].filter(bp => !prevBPSet.has(bp));
        const delBPs = [...prevBPSet].filter(bp => !currBPSet.has(bp));

        const bpDiff = {
            added: newBPs.map(bp => stringToSourceBreakpoint(bp)),
            deleted: delBPs.map(bp => stringToSourceBreakpoint(bp)),
        }

        this.breakpoints.set(path, newSnapshot);
        return bpDiff;
    }

    public add(path: string, breakpoint: DebugProtocol.SourceBreakpoint): void {
        const bps: DebugProtocol.SourceBreakpoint[] = this.breakpoints.get(path) ?? [];
        bps.push(breakpoint);
        this.breakpoints.set(path, bps);
    }

    public remove(path: string, breakpoint: DebugProtocol.SourceBreakpoint): void {
        const bps = this.breakpoints.get(path) ?? [];
        const bpString = sourceBreakpointToString(breakpoint);
        this.breakpoints.set(path, bps.filter(b => bpString !== sourceBreakpointToString(b)));
    }

    public updateLine(path: string, originalLine: number, newLine: number) : void {
        const bps: DebugProtocol.SourceBreakpoint[] = this.breakpoints.get(path) ?? [];
        const bp = bps?.find(b => b.line === originalLine);
        if (bp) { bp.line = newLine; }
    }
}
