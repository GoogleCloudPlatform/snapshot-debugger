import {
    DebugSession,
    InitializedEvent, StoppedEvent, BreakpointEvent,
    Thread, StackFrame, Scope, Source
} from '@vscode/debugadapter';
import { CdbgBreakpoint } from './breakpoint';
import { initializeApp, cert, App, deleteApp } from 'firebase-admin/app';
import { DataSnapshot, getDatabase } from 'firebase-admin/database';

import { DebugProtocol } from '@vscode/debugprotocol';
import { Database } from 'firebase-admin/lib/database/database';
import { addPwd, sleep, stripPwd } from './util';
import { pickDebuggeeId } from './debuggeePicker';

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

    private currentBreakpoint: CdbgBreakpoint | undefined = undefined;
    private currentFrameId: number = 0;

    private breakpoints: Map<string, CdbgBreakpoint> = new Map();

    public constructor() {
        super();
    }

    /**
     * The 'initialize' request is the first request called by the frontend
     * to interrogate the features the debug adapter provides.
     */
    protected initializeRequest(response: DebugProtocol.InitializeResponse, args: DebugProtocol.InitializeRequestArguments): void {

        response.body = response.body || {};

        response.body.supportsSteppingGranularity = false;
        response.body.supportsConditionalBreakpoints = true;
        response.body.supportsLogPoints = true;

        this.sendResponse(response);
        console.log('Initialized');
    }

    protected async attachRequest(response: DebugProtocol.AttachResponse, args: IAttachRequestArguments) {
        const serviceAccount = require(args.serviceAccountPath);
        const projectId = serviceAccount['project_id'];
        let databaseUrl = args.databaseUrl;
        if (!databaseUrl) {
            databaseUrl = `https://${projectId}-cdbg.firebaseio.com`;
        }

        this.app = initializeApp({
            credential: cert(serviceAccount),
            databaseURL: databaseUrl
        },
            FIREBASE_APP_NAME
        );

        this.db = getDatabase(this.app);

        const debuggeeId = args.debuggeeId || await pickDebuggeeId(this.db);
        if (!debuggeeId) {
            response.success = false;
            this.sendErrorResponse(response, 1, 'No Debuggee selected');
            return;
        }
        this.debuggeeId = debuggeeId;

        const activeBreakpointRef = this.db.ref(`cdbg/breakpoints/${this.debuggeeId}/active`);

        // Start with a direct read to avoid race conditions with local breakpoints.
        const snapshot: DataSnapshot = await activeBreakpointRef.get();
        snapshot.forEach((breakpoint) => this.addServerBreakpoint(CdbgBreakpoint.fromSnapshot(breakpoint)));
        console.log('Breakpoints loaded from server');

        // Set up the subscription to get server-side updates.
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
                // Case 1: Breakpoint removed from UI.  We should have already handled this in setBreakPointsRequest.
                // Case 2: Breakpoint finalized server-side.  Find out what to do next by loading /final on the breakpoint.

                await this.loadSnapshotDetails(bpId);

                // Let the UI know that there was a snapshot.
                const stoppedEvent = new StoppedEvent('Snapshot taken', parseInt(bpId!.substring(2)));
                this.sendEvent(stoppedEvent);
            });

        console.log('Attached');
        this.sendResponse(response);
        // At this point we're considered sufficiently initialized to take requests from the IDE.
        this.sendEvent(new InitializedEvent());
}

    private async loadSnapshotDetails(bpId: string): Promise<void> {
        // TODO: Be more clever about this.  There's a race condition.
        await (sleep(250));
        // Just try loading it from the /snapshot table.
        const snapshotRef = this.db!.ref(`cdbg/breakpoints/${this.debuggeeId}/snapshot/${bpId}`);
        const dataSnapshot: DataSnapshot = await snapshotRef.get();
        console.log(`Getting the snapshot details`);
        console.log(dataSnapshot.val());
        if (dataSnapshot.val()) {
            const breakpoint = CdbgBreakpoint.fromSnapshot(dataSnapshot);
            this.breakpoints.get(bpId)!.serverBreakpoint = breakpoint.serverBreakpoint;
            console.log(`Just loaded snapshot details for ${bpId}`);
            console.log(breakpoint);
        } else {
            // TODO: Something went wrong.
        }

    }

    private addServerBreakpoint(breakpoint: CdbgBreakpoint): void {
        const bpId = breakpoint.id!;  // Will be provided unless things went wrong elsewhere.
        if (bpId in this.breakpoints) {
            // TODO: ???
        } else {
            this.breakpoints.set(bpId, breakpoint);
            this.sendEvent(new BreakpointEvent('new', breakpoint.toLocalBreakpoint()));
        }
    }

    protected async setBreakPointsRequest(response: DebugProtocol.SetBreakpointsResponse, args: DebugProtocol.SetBreakpointsArguments): Promise<void> {
        console.log('setBreakPointsRequest');
        console.log(args);

        const bpIds = new Set<string>();  // Keep track of which breakpoints we've seen.
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

                // If not, persist it.  Server breakpoints should have already been loaded.
                if (!found) {
                    this.saveBreakpointToServer(cdbgBreakpoint);
                }

                bpIds.add(cdbgBreakpoint.id!);
            }
        }

        const breakpointsToRemove = new Set(this.breakpoints.keys());
        bpIds.forEach((id) => breakpointsToRemove.delete(id));

        breakpointsToRemove.forEach((id) => {
            this.deleteBreakpointFromServer(id);
        })
    }

    private saveBreakpointToServer(breakpoint: CdbgBreakpoint): void {
        const bpId = `b-${Math.floor(Date.now() / 1000)}`;
        console.log(`creating new breakpoint in firebase: ${bpId}`);
        const serverBreakpoint = {
            action: 'CAPTURE',
            id: bpId,
            location: {
                path: stripPwd(breakpoint.localBreakpoint!.source!.path!), // TODO: Handle case where sourceReference is specified (and figure out what that means)
                line: breakpoint.localBreakpoint!.line!,
            },
            // eslint-disable-next-line @typescript-eslint/naming-convention
            createTimeUnixMsec: { '.sv': 'timestamp' }
        };
        this.db?.ref(`cdbg/breakpoints/${this.debuggeeId}/active/${bpId}`).set(serverBreakpoint);

        breakpoint.serverBreakpoint = serverBreakpoint;
        this.breakpoints.set(bpId, breakpoint);
    }

    private deleteBreakpointFromServer(bpId: string): void {
        this.db?.ref(`cdbg/breakpoints/${this.debuggeeId}/active/${bpId}`).set(null);
        this.breakpoints.delete(bpId);
    }

    protected async stackTraceRequest(response: DebugProtocol.StackTraceResponse, args: DebugProtocol.StackTraceArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        response.body = response.body || {};

        const bpId = `b-${args.threadId}`;
        const breakpoint = this.breakpoints.get(bpId);
        if (!breakpoint) {
            console.log(`Unexpected request for unknown breakpoint ${bpId}`);
            this.sendResponse(response);
            return;
        }

        // We'll get more requests for details on the breakpoint but won't get the breakpoint ID.
        // Stash the breakpoint so that we don't lose this context.
        this.currentBreakpoint = breakpoint;

        if (breakpoint.serverBreakpoint?.status?.isError) {
            response.body.stackFrames = [
                // TODO: Something tidier.
                new StackFrame(0, breakpoint.serverBreakpoint.status.description.format),
            ];
            this.sendResponse(response);
            return;
        }

        if (breakpoint.serverBreakpoint?.stackFrames) {
            const stackFrames = [];
            const serverFrames = breakpoint.serverBreakpoint!.stackFrames!;
            for (let i = 0; i < serverFrames.length; i++) {
                const path = serverFrames[i].location.path;
                stackFrames.push(new StackFrame(i, serverFrames[i].function, new Source(path, addPwd(path)), serverFrames[i].location.line));
            }
            response.body.stackFrames = stackFrames;
            this.sendResponse(response);
        } else {
            console.log(`Not sure what's going on with this one:`);
            console.log(breakpoint);
        }
    }


    protected async scopesRequest(response: DebugProtocol.ScopesResponse, args: DebugProtocol.ScopesArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        this.currentFrameId = args.frameId;

        response.body = response.body || {};

        const scopes: DebugProtocol.Scope[] = [];

        const stackFrame = this.currentBreakpoint!.serverBreakpoint!.stackFrames![this.currentFrameId];
        if (stackFrame.locals) {
            scopes.push(new Scope('locals', 1));
        } else {
            scopes.push(new Scope('No local variables', 0));
        }

        //scopes.push(new Scope('expressions', 2));  // TODO: Put this here if it's available.
        // TODO: Only put this here if it's available.

        response.body.scopes = scopes;
        this.sendResponse(response);
    }

    protected async variablesRequest(response: DebugProtocol.VariablesResponse, args: DebugProtocol.VariablesArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        console.log('variablesRequest');
        console.log(args);

        response.body = response.body || {};

        const variables: DebugProtocol.Variable[] = [];

        if (args.variablesReference === 0) {
            // No local variables.  No content.
        }
        if (args.variablesReference === 1) {
            if (this.currentBreakpoint!.serverBreakpoint!.stackFrames) {
                const locals = this.currentBreakpoint!.serverBreakpoint!.stackFrames[this.currentFrameId].locals!;

                for (let i = 0; i < locals.length; i++) {
                    variables.push({
                        name: locals[i].name,
                        value: locals[i].value || '...',
                        variablesReference: locals[i].varTableIndex ? locals[i].varTableIndex! + 100 : 0
                        // TODO: type, and indicate supportsVariableType
                        // TODO: presentationHint with type
                        // TODO: namedVariables for maps
                        // TODO: indexedVariables for lists
                    });
                }
            } else {
                console.log('cannot do a thing');
            }
        } else {
            const vartable = this.currentBreakpoint!.serverBreakpoint!.variableTable!;
            const variable = vartable[args.variablesReference - 100];
            for (let i = 0; i < variable.members!.length; i++) {
                const member = variable.members![i];
                variables.push({
                    name: member.name,
                    value: member.value || '...',
                    variablesReference: member.varTableIndex ? member.varTableIndex + 100 : 0
                    // TODO: type, and indicate supportsVariableType
                    // TODO: presentationHint with type
                    // TODO: namedVariables for maps
                    // TODO: indexedVariables for lists
                });
            }
        }
        response.body.variables = variables;
        this.sendResponse(response);
    }

    protected async threadsRequest(response: DebugProtocol.ThreadsResponse, request?: DebugProtocol.Request | undefined): Promise<void> {
        response.body = response.body || {};

        const threads: Thread[] = [];
        for (const bpId of this.breakpoints.keys()) {
            threads.push(new Thread(parseInt(bpId.substring(2)), bpId));
        }

        response.body.threads = threads;
        this.sendResponse(response);
    }
}