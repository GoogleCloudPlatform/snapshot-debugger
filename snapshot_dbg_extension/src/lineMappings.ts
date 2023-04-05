import { DebugProtocol } from '@vscode/debugprotocol';
import { sourceBreakpointToString, stringToSourceBreakpoint } from './util';

export interface IdeBreakpointsDiff {
  added: DebugProtocol.SourceBreakpoint[];
  deleted: DebugProtocol.SourceBreakpoint[];
}

/**
 * Class to track line number that got remapped by the agent.
 *
 * When a BP gets set on a line the agent doesn't find code on, it may find the
 * closest line with code, set the BP and report back the updated line number.
 * This class tracks thes remappings per path.
 */
export class LineMappings {
    // Key: File path.
    // Value: Map of requested line to actual line agent reported back with code.
    private paths: Map<string, Map<number, number>> = new Map();

    public add(path: string, requestedLine: number, actualLine: number): void {
        let lineMappings = this.paths.get(path);
        if (lineMappings === undefined) {
            lineMappings = new Map();
            this.paths.set(path, lineMappings);
        }

        lineMappings.set(requestedLine, actualLine);
    }

    public get(path: string, line: number): number|undefined {
        return this.paths.get(path)?.get(line);
    }
}
