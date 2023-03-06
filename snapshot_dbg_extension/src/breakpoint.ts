import {
    Source, Breakpoint
} from '@vscode/debugadapter';
import { DebugProtocol } from '@vscode/debugprotocol';
import { DataSnapshot } from 'firebase-admin/database';
import { addPwd } from './util';


export interface Variable {
    name?: string;
    value?: string;
    type?: string;
    members?: Variable[];
    varTableIndex?: number;
}

interface ServerLocation {
    path: string;
    line: number;
}

interface ServerBreakpoint {
    id: string;
    action: string;
    location: ServerLocation;
    status?: {
        description: {
            format: string;
        };
        isError: boolean;
    };
    stackFrames?: {
        function: string;
        locals?: Variable[];
        location: ServerLocation;
    }[];
    variableTable?: Variable[];
}

export class CdbgBreakpoint {
    localBreakpoint: DebugProtocol.Breakpoint | undefined;
    serverBreakpoint: ServerBreakpoint | undefined;

    // Not all Variables have their own entry in the breakpoints variable table.
    // For the purposes of handing a `variablesReference` back to the UI, an
    // entry for these variables gets added to this array. Any variable table
    // indexes that equal or exceed the size of the main variable table, can be
    // found found in this table. The index to use for this table can be
    // obtained by subtracting the size of the main variable table from the
    // index.
    extendedVariableTable: Variable[] = new Array();

    public get id() {
        if (this.serverBreakpoint) {
            return this.serverBreakpoint.id;
        }
        return undefined;
    }

    /** Returns the full path to the file. */
    public get path() {
        if (this.localBreakpoint) {
            return this.localBreakpoint.source!.path;
        } else {
            return addPwd(this.serverBreakpoint!.location.path);
        }
    }

    public get line() {
        if (this.localBreakpoint) {
            return this.localBreakpoint.line!;
        } else {
            return this.serverBreakpoint!.location.line;
        }
    }

    public toLocalBreakpoint(): Breakpoint {
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
        if (other.id === this.id) {
            return true;
        }

        return other.path === this.path && other.line === this.line;
    }

    public static fromSnapshot(snapshot: DataSnapshot): CdbgBreakpoint {
        const breakpoint = new CdbgBreakpoint();
        breakpoint.serverBreakpoint = snapshot.val();
        return breakpoint;
    }

    public static fromSourceBreakpoint(source: DebugProtocol.Source, sourceBreakpoint: DebugProtocol.SourceBreakpoint): CdbgBreakpoint {
        const breakpoint = new CdbgBreakpoint();
        breakpoint.localBreakpoint = new Breakpoint(
            true,
            sourceBreakpoint.line,
            undefined,
            new Source(source.name ? source.name : 'unknown', source.path)
        );
        return breakpoint;
    }
}
