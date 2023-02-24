import {
	Logger, logger,
	DebugSession,
	InitializedEvent, TerminatedEvent, StoppedEvent, BreakpointEvent, OutputEvent,
	ProgressStartEvent, ProgressUpdateEvent, ProgressEndEvent, InvalidatedEvent,
	Thread, StackFrame, Scope, Source, Handles, Breakpoint, MemoryEvent
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

export class SnapshotDebuggerSession extends DebugSession {
    private app: App | undefined = undefined;
    private db: Database | undefined = undefined;
    private debuggeeId: string = '';

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

        response.body.supportsHitConditionalBreakpoints = true;
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
                // TODO: Merge with breakpoints that are held by the IDE.
                console.log(`new breakpoint received from server: ${snapshot.key}`);
                // TODO: Figure out how to report back the added breakpoint.
                const serverBreakpoint = snapshot.val();
                serverBreakpoint.id = snapshot.key;
                let source = new Source(serverBreakpoint.location.file, serverBreakpoint.location.file);
                let breakpoint = new Breakpoint(
                    false, // verified
                    serverBreakpoint.location.line,
                    undefined,
                    source
                );
                this.sendEvent(new BreakpointEvent('new', breakpoint));
            });
        activeBreakpointRef.on(
            'child_removed',
            (snapshot: DataSnapshot) => {
                const bpId = snapshot.key;
                // TODO: Remove the breakpoint.
                // TODO: This might be where we notice that breakpoints have triggered.  Figure this out too.
            });

        this.sendResponse(response);
	}

    protected async setBreakPointsRequest(response: DebugProtocol.SetBreakpointsResponse, args: DebugProtocol.SetBreakpointsArguments): Promise<void> {
        console.log('setBreakPointsRequest');
        console.log(args);
        // TODO: Be smarter about this; dedupe, etc.
        // TODO: Handle removal of breakpoints here too!
        if (args.breakpoints) {
            for (const breakpoint of args.breakpoints) {
                const breakpointId = `b-${Math.floor(Date.now() / 1000)}`;
                // TODO: Handle logpoints.
                const serverBreakpoint = {
                    action: 'CAPTURE',
                    id: breakpointId,
                    location: {
                        file: args.source.path, // TODO: Handle case where sourceReference is specified (and figure out what that means)
                        line: breakpoint.line,
                    },
                    // eslint-disable-next-line @typescript-eslint/naming-convention
                    createTimeUnixMsec: {'.sv': 'timestamp'}
                };
                this.db?.ref(`cdbg/breakpoints/${this.debuggeeId}/active/${breakpointId}`).set(serverBreakpoint);
            }
        }
    }

    protected breakpointLocationsRequest(response: DebugProtocol.BreakpointLocationsResponse, args: DebugProtocol.BreakpointLocationsArguments, request?: DebugProtocol.Request): void {
        console.log('breakpointLocationsRequest');
    }

    protected stackTraceRequest(response: DebugProtocol.StackTraceResponse, args: DebugProtocol.StackTraceArguments): void {
        console.log('stackTraceRequest');
    }

    protected async variablesRequest(response: DebugProtocol.VariablesResponse, args: DebugProtocol.VariablesArguments, request?: DebugProtocol.Request): Promise<void> {
        console.log('variablesRequest');
    }

    protected completionsRequest(response: DebugProtocol.CompletionsResponse, args: DebugProtocol.CompletionsArguments): void {
        console.log('completionsRequest');
    }
}