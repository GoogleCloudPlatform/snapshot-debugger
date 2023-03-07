import {
    Source, Breakpoint
} from '@vscode/debugadapter';
import { DebugProtocol } from '@vscode/debugprotocol';
import { DataSnapshot } from 'firebase-admin/database';
import { addPwd, stripPwd } from './util';

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
    isFinal: boolean;
    createTimeUnixMsec?: {} | number;
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

    private constructor(
        public localBreakpoint: DebugProtocol.Breakpoint,
        public serverBreakpoint: ServerBreakpoint) {}

    public get id() {
        return this.serverBreakpoint.id;
    }

    public set id(bpId: string) {
        this.serverBreakpoint.id = bpId;
    }

    /** Returns the full path to the file. */
    public get path() {
        return this.localBreakpoint.source!.path;
    }

    public get line() {
        return this.localBreakpoint.line;
    }

    public hasSnapshot(): boolean {
        return this.serverBreakpoint.stackFrames !== undefined;
    }

    public hasError(): boolean {
        return this.serverBreakpoint.status?.isError ?? false;
    }

    public isActive(): boolean {
        return this.serverBreakpoint.isFinal;
    }

    public toLocalBreakpoint(): DebugProtocol.Breakpoint {
        if (this.localBreakpoint) {
            return new Breakpoint(true, this.localBreakpoint.line, undefined, new Source(this.localBreakpoint.source?.name || 'unknown', this.localBreakpoint.source?.path));
        }
        if (this.serverBreakpoint) {
            const path = this.serverBreakpoint.location.path;
            return new Breakpoint(true, this.serverBreakpoint.location.line, undefined, new Source(path, addPwd(path)));
        }
        throw (new Error('Invalid breakpoint state.  Breakpoint must have local or server breakpoint data.'));
    }

    public toServerBreakpoint(): ServerBreakpoint {
        if (this.serverBreakpoint) {
            return this.serverBreakpoint;
        }
        throw (new Error('Invalid breakpoint state.  Should not be converting a local breakpoint to a server breakpoint.'));
    }

    public matches(other: CdbgBreakpoint): Boolean {
        if (this.id != kUnknown && other.id === this.id) {
            return true;
        }

        return other.path === this.path && other.line === this.line;
    }

    public static fromSnapshot(snapshot: DataSnapshot): CdbgBreakpoint {
        const serverBreakpoint = snapshot.val();
        const path = serverBreakpoint.location.path;
        const localBreakpoint = new Breakpoint(
            serverBreakpoint.isFinal,
            serverBreakpoint.location.line,
            undefined,
            new Source(path, addPwd(path))
        );
        // Note: Can set localBreakpoint.id, message, etc (though not sure how to set message...)

        return new CdbgBreakpoint(localBreakpoint, serverBreakpoint);
    }

    public static fromSourceBreakpoint(source: DebugProtocol.Source, sourceBreakpoint: DebugProtocol.SourceBreakpoint): CdbgBreakpoint {
        const bpId = kUnknown;

        const localBreakpoint = new Breakpoint(
            true,
            sourceBreakpoint.line,
            undefined,
            new Source(source.name ? source.name : kUnknown, source.path)
        );

        const serverBreakpoint = {
            id: bpId,
            action: 'CAPTURE',
            isFinal: false,
            location: {
                path: stripPwd(source.path!),
                line: sourceBreakpoint.line,
            },
            condition: sourceBreakpoint.condition
        };

        return new CdbgBreakpoint(localBreakpoint, serverBreakpoint);
    }
}
