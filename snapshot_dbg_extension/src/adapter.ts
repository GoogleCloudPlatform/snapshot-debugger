import {
	Logger, logger,
	DebugSession,
	InitializedEvent, TerminatedEvent, StoppedEvent, BreakpointEvent, OutputEvent,
	ProgressStartEvent, ProgressUpdateEvent, ProgressEndEvent, InvalidatedEvent,
	Thread, StackFrame, Scope, Source, Handles, Breakpoint, MemoryEvent, ThreadEvent
} from '@vscode/debugadapter';
import { initializeApp, cert, App, deleteApp } from 'firebase-admin/app';
import { DataSnapshot, getDatabase } from 'firebase-admin/database';

import { DebugProtocol } from '@vscode/debugprotocol';
import { Database } from 'firebase-admin/lib/database/database';

const FIREBASE_APP_NAME = 'snapshotdbg';

/**
 * This interface describes the snapshot-debugger specific attach attributes
 * (which are not part of the Debug Adapter Protocol).
 * The schema for these attributes lives in the package.json of the snapshot-debugger extension.
 * The interface should always match this schema.
 */
interface IAttachRequestArguments extends DebugProtocol.AttachRequestArguments {
	/** An absolute path to the service account credentials file. */
	serviceAccountPath: string;

    /** URL to the Firebase RTDB database. */
    databaseUrl: string | undefined;

    /** Debuggee Id of an already registered debuggee. */
    debuggeeId: string;
}

interface ServerBreakpoint {
    id: string;
    action: string;
    location: {
        file: string;
        line: number;
    }
}

class CdbgBreakpoint {
    localBreakpoint: DebugProtocol.Breakpoint | undefined;
    serverBreakpoint: ServerBreakpoint | undefined;

    public get id() {
        if (this.serverBreakpoint) {
            return this.serverBreakpoint.id;
        }
        return undefined;
    }

    public toLocalBreakpoint(): Breakpoint {
        if (this.localBreakpoint) {
            return new Breakpoint(true, this.localBreakpoint.line, undefined, new Source(this.localBreakpoint.source?.name || 'unknown', this.localBreakpoint.source?.path));
        }
        if (this.serverBreakpoint) {
            return new Breakpoint(true, this.serverBreakpoint.location.line, undefined, new Source(this.serverBreakpoint.location.file, this.serverBreakpoint.location.file));
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
        // TODO: Collapse all of this into accessors for the file and line.
        if (other.localBreakpoint && this.localBreakpoint) {
            return other.localBreakpoint.source?.path === this.localBreakpoint?.source?.path && other.localBreakpoint.line === this.localBreakpoint?.line;
        }
        if (other.localBreakpoint) {
            return other.localBreakpoint.source?.path === this.serverBreakpoint?.location.file && other.localBreakpoint.line === this.serverBreakpoint?.location.line;
        }
        return other.serverBreakpoint?.location.file === this.localBreakpoint?.source?.path && other.serverBreakpoint?.location.line === this.localBreakpoint?.line;
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


export class SnapshotDebuggerSession extends DebugSession {
    private app: App | undefined = undefined;
    private db: Database | undefined = undefined;
    private debuggeeId: string = '';

    private breakpoints: Map<string, CdbgBreakpoint> = new Map();

    public constructor() {
        super();

        console.log('SnapshotDebuggerSession constructor');
    }

	/**
	 * The 'initialize' request is the first request called by the frontend
	 * to interrogate the features the debug adapter provides.
	 */
    protected initializeRequest(response: DebugProtocol.InitializeResponse, args: DebugProtocol.InitializeRequestArguments): void {
        console.log('initializeRequest');

        console.log(args);

        response.body = response.body || {};

        response.body.supportsConditionalBreakpoints = true;
        response.body.supportsLogPoints = true;

        this.sendResponse(response);
        // We're all good to go!
        this.sendEvent(new InitializedEvent());
    }

    protected async attachRequest(response: DebugProtocol.AttachResponse, args: IAttachRequestArguments) {
        console.log('attachRequest');

        this.debuggeeId = args.debuggeeId;

		const serviceAccount = require(args.serviceAccountPath);
		const projectId = serviceAccount['project_id'];
        let databaseUrl = args.databaseUrl;
        if (!databaseUrl) {
            databaseUrl = `https://${projectId}-default-rtdb.firebaseio.com`;
        }

		this.app = initializeApp({
				credential: cert(serviceAccount),
				databaseURL: databaseUrl
			},
			FIREBASE_APP_NAME
		);
	
		this.db = getDatabase(this.app);

        const activeBreakpointRef = this.db.ref(`cdbg/breakpoints/${this.debuggeeId}/active`);
        activeBreakpointRef.on(
            'child_added',
            (snapshot: DataSnapshot) => {
                console.log(`new breakpoint received from server: ${snapshot.key}`);
                // Added is either new (remote) or persisted (local).
                const bpId = snapshot.key!;
                if (bpId in this.breakpoints) {
                    // TODO: ???
                } else {
                    const breakpoint = CdbgBreakpoint.fromSnapshot(snapshot);
                    this.breakpoints.set(bpId, breakpoint);
                    this.sendEvent(new BreakpointEvent('new', breakpoint.toLocalBreakpoint()));
                }
            });
        activeBreakpointRef.on(
            'child_removed',
            (snapshot: DataSnapshot) => {
                const bpId = snapshot.key;
                // Case 1: Breakpoint removed from UI.  We should have already handled this in setBreakPointsRequest.
                // Case 2: Breakpoint finalized server-side.  Find out what to do next by loading /final on the breakpoint.

                // Let the UI know that there was a snapshot.
                const stoppedEvent = new StoppedEvent('Snapshot taken', parseInt(bpId!.substring(2)));
                this.sendEvent(stoppedEvent);
            });

        this.sendResponse(response);
	}

    protected async setBreakPointsRequest(response: DebugProtocol.SetBreakpointsResponse, args: DebugProtocol.SetBreakpointsArguments): Promise<void> {
        console.log('setBreakPointsRequest');
        console.log(args);
        // TODO: Remove missing breakpoints.
        if (args.breakpoints) {
            for (const breakpoint of args.breakpoints) {
                const cdbgBreakpoint = CdbgBreakpoint.fromSourceBreakpoint(args.source, breakpoint);

                let found = false;
                for (const bp of this.breakpoints.values()) {
                    if (bp.matches(cdbgBreakpoint)) {
                        found = true;
                        bp.localBreakpoint = cdbgBreakpoint.localBreakpoint;
                    }
                }

                // If not, persist it.
                if (!found) {
                    const bpId = `b-${Math.floor(Date.now() / 1000)}`;
                    const serverBreakpoint = {
                        action: 'CAPTURE',
                        id: bpId,
                        location: {
                            file: args.source.path!, // TODO: Handle case where sourceReference is specified (and figure out what that means)
                            line: breakpoint.line,
                        },
                        // eslint-disable-next-line @typescript-eslint/naming-convention
                        createTimeUnixMsec: {'.sv': 'timestamp'}
                    };                
                    this.db?.ref(`cdbg/breakpoints/${this.debuggeeId}/active/${bpId}`).set(serverBreakpoint);

                    cdbgBreakpoint.serverBreakpoint = serverBreakpoint;
                    this.breakpoints.set(bpId, cdbgBreakpoint);
                }
            }
        }
    }

    protected async stackTraceRequest(response: DebugProtocol.StackTraceResponse, args: DebugProtocol.StackTraceArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        console.log('stackTraceRequest');
        console.log(request);

        response.body = response.body || {};

        response.body.stackFrames = [
            new StackFrame(0, 'something'),
            new StackFrame(1, 'something else')
        ];
        this.sendResponse(response);
    }

    protected async scopesRequest(response: DebugProtocol.ScopesResponse, args: DebugProtocol.ScopesArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        console.log('scopesRequest');
    }

    protected async variablesRequest(response: DebugProtocol.VariablesResponse, args: DebugProtocol.VariablesArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        console.log('variablesRequest');
    }

    protected async threadsRequest(response: DebugProtocol.ThreadsResponse, request?: DebugProtocol.Request | undefined): Promise<void> {
        console.log('threadsRequest');
        console.log(request);

        response.body = response.body || {};

        const threads: Thread[] = [];
        for (const bpId of this.breakpoints.keys()) {
            threads.push(new Thread(parseInt(bpId.substring(2)), bpId));
        }

        response.body.threads = threads;
        this.sendResponse(response);
    }
}