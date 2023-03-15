import {
    Source, Breakpoint
} from '@vscode/debugadapter';
import { DebugProtocol } from '@vscode/debugprotocol';
import { DataSnapshot } from 'firebase-admin/database';
import { addPwd, stripPwd } from './util';

function unixTimeToString(timeUnixMsec: number | undefined): string {
    return timeUnixMsec ?  new Date(timeUnixMsec).toISOString() : "";
}

type StatusMessageRefersTo =
  | 'UNSPECIFIED'
  | 'BREAKPOINT_SOURCE_LOCATION'
  | 'BREAKPOINT_CONDITION'
  | 'BREAKPOINT_EXPRESSION'
  | 'BREAKPOINT_AGE'
  | 'BREAKPOINT_CANARY_FAILED'
  | 'VARIABLE_NAME'
  | 'VARIABLE_VALUE';

interface FormatMessage {
  format?: string;
  // TODO: The code expects the `parameters` field to be optional.
  //       Verify if this aligns with the API reference.
  parameters?: string[];
}

export interface StatusMessage {
  isError?: boolean;
  refersTo?: StatusMessageRefersTo;
  description?: FormatMessage;
}

export interface Variable {
    name?: string;
    value?: string;
    type?: string;
    members?: Variable[];
    varTableIndex?: number;
    status?: StatusMessage;
}

interface ServerLocation {
    path: string;
    line: number;
}

interface ServerStackFrame {
    function?: string;
    location?: ServerLocation;
    arguments?: Variable[];
    locals?: Variable[];
  }

export interface ServerBreakpoint {
    id: string;
    action: string;
    location: ServerLocation;
    condition?: string;
    expressions?: string[];
    status?: StatusMessage;
    stackFrames?: ServerStackFrame[];
    evaluatedExpressions?: Variable[];
    isFinalState: boolean;
    createTimeUnixMsec?: {} | number;
    finalTimeUnixMsec?: number;
    variableTable?: Variable[];
}

const kUnknown = 'unknown';

export class CdbgBreakpoint {
    // Not all Variables have their own entry in the breakpoints variable table.
    // For the purposes of handing a `variablesReference` back to the UI, an
    // entry for these variables gets added to this array. Any variable table
    // indexes that equal or exceed the size of the main variable table, can be
    // found found in this table. The index to use for this table can be
    // obtained by subtracting the size of the main variable table from the
    // index.
    extendedVariableTable: Variable[] = new Array();

    // Preserve some state about the breakpoint's data.
    public hasServerData = false;
    public hasLocalData = false;
    public hasUnsavedData = false;

    private constructor(
        public localBreakpoint: DebugProtocol.Breakpoint,
        public serverBreakpoint: ServerBreakpoint) {}

    public get id(): string {
        return this.serverBreakpoint.id;
    }

    public get numericId(): number {
        return parseInt(this.id.substring(2));
    }

    public set id(bpId: string) {
        this.serverBreakpoint.id = bpId;
    }

    /** Returns the full path to the file. */
    public get path() {
        return this.localBreakpoint.source!.path;
    }

    public get shortPath() {
        return this.serverBreakpoint.location.path;
    }

    public get line() {
        return this.localBreakpoint.line;
    }

    public get finalTime(): string {
        return unixTimeToString(this.serverBreakpoint.finalTimeUnixMsec);
    }

    public isSnapshot(): boolean {
        return !this.isLogpoint();
    }

    public isLogpoint(): boolean {
        return this.serverBreakpoint.action == 'LOG';
    }

    public hasSnapshot(): boolean {
        return this.serverBreakpoint.stackFrames !== undefined;
    }

    public hasError(): boolean {
        return this.serverBreakpoint.status?.isError ?? false;
    }

    public isActive(): boolean {
        return !this.serverBreakpoint.isFinalState;
    }

    public matches(other: CdbgBreakpoint): Boolean {
        if (this.id != kUnknown && other.id === this.id) {
            return true;
        }

        return other.path === this.path && other.line === this.line;
    }

    public updateServerData(snapshot: DataSnapshot): void {
        this.serverBreakpoint = snapshot.val();
        this.hasServerData = true;
    }

    public static fromSnapshot(snapshot: DataSnapshot): CdbgBreakpoint {
        const serverBreakpoint = snapshot.val();
        const path = serverBreakpoint.location.path;
        const localBreakpoint: DebugProtocol.Breakpoint = {
            verified: !serverBreakpoint.isFinalState, // final -> unverified; active -> verified
            line: serverBreakpoint.location.line,
            source: {
                name: path,
                path: addPwd(path)
            }
        };
        const bp = new CdbgBreakpoint(localBreakpoint, serverBreakpoint);
        bp.hasServerData = true;

        // TODO: Set message on localBreakpoint.

        return bp;
    }

    public static fromSourceBreakpoint(source: DebugProtocol.Source, sourceBreakpoint: DebugProtocol.SourceBreakpoint): CdbgBreakpoint {
        const bpId = kUnknown;

        const localBreakpoint: DebugProtocol.Breakpoint = {
            verified: true,
            line: sourceBreakpoint.line,
            source: {
                name: source.name ?? kUnknown,
                path: source.path
            }
        };

        const serverBreakpoint = {
            id: bpId,
            action: 'CAPTURE',
            isFinalState: false,
            location: {
                path: stripPwd(source.path!),
                line: sourceBreakpoint.line,
            },
            ...(sourceBreakpoint.condition && {condition: sourceBreakpoint.condition})
        };

        const bp = new CdbgBreakpoint(localBreakpoint, serverBreakpoint);
        bp.hasLocalData = true;
        return bp;
    }
}
