import {
    DebugSession,
    InitializedEvent, StoppedEvent, BreakpointEvent,
    Thread, StackFrame, Scope, Source, Variable, ThreadEvent
} from '@vscode/debugadapter';
import * as vscode from 'vscode';
import { CdbgBreakpoint, Variable as CdbgVariable} from './breakpoint';
import { StatusMessage } from './statusMessage';
import { UserPreferences } from './userPreferences';
import { initializeApp, cert, App, deleteApp } from 'firebase-admin/app';
import { DataSnapshot, getDatabase } from 'firebase-admin/database';

import { DebugProtocol } from '@vscode/debugprotocol';
import { Database } from 'firebase-admin/lib/database/database';
import { addPwd, sleep, stripPwd } from './util';
import { pickDebuggeeId } from './debuggeePicker';

const FIREBASE_APP_NAME = 'snapshotdbg';
const INITIALIZE_TIME_ALLOWANCE_MS = 2 * 1000; // 2 seconds

/**
 * This interface describes the snapshot-debugger specific attach attributes
 * (which are not part of the Debug Adapter Protocol).  The schema for these
 * attributes lives in the package.json of the snapshot-debugger extension.  The
 * interface should always match this schema.
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
    private initializedPaths: Map<string, boolean> = new Map();
    private previousSetBreakpointRequests: Map<string, DebugProtocol.SourceBreakpoint[]> = new Map();

    private setVariableType: boolean = false;
    private userPreferences: UserPreferences;
    private attachTime: number = Date.now();

    public constructor(userPreferences: UserPreferences) {
        super();
        this.userPreferences = userPreferences;
    }

    /**
     * The 'initialize' request is the first request called by the frontend to
     * interrogate the features the debug adapter provides.
     * https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Initialize
     *
     * Capabilityes for the response.body:
     * https://microsoft.github.io/debug-adapter-protocol/specification#Types_Capabilities
     */
    protected initializeRequest(response: DebugProtocol.InitializeResponse, args: DebugProtocol.InitializeRequestArguments): void {
        this.setVariableType = args.supportsVariableType ?? false;

        response.body = response.body || {};

        response.body.supportsSteppingGranularity = false;
        response.body.supportsConditionalBreakpoints = true;
        response.body.supportsLogPoints = true;
        response.body.supportsValueFormattingOptions = false;
        response.body.supportsConditionalBreakpoints = true;

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
        // Note that this will result in a double-read of these breakpoints.
        const activeSnapshot: DataSnapshot = await activeBreakpointRef.get();
        activeSnapshot.forEach((breakpoint) => this.addInitServerBreakpoint(CdbgBreakpoint.fromSnapshot(breakpoint)));
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

                if (this.breakpoints.has(bpId)) {
                    // Breakpoint finalized server-side.  Find out what to do next by loading /snapshot on the breakpoint.
                    await this.loadSnapshotDetails(bpId);
                    this.reportCompletedBreakpointToIDE(bpId);
                } else {
                    // Breakpoint removed from UI.  We should have already handled this in setBreakPointsRequest.
                    this.breakpoints.delete(bpId);
                }
            });

        console.log('Attached');
        this.sendResponse(response);
        // At this point we're considered sufficiently initialized to take requests from the IDE.
        this.sendEvent(new InitializedEvent());
    }

    protected async disconnectRequest(response: DebugProtocol.DisconnectResponse, args: DebugProtocol.DisconnectArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        // A new instance of this class is created for each debugging session.
        // Treat this function as a desctructor to clean up any resources that require cleanup.

        if (this.app) {
            deleteApp(this.app);
            this.app = undefined;
        }

        this.sendResponse(response);
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
            this.sendEvent(new BreakpointEvent('new', breakpoint.localBreakpoint));
        }
    }

    private sourceBreakpointToString(bp: DebugProtocol.SourceBreakpoint): string {
        return `${bp.line}\0${bp.condition}\0${bp.logMessage}`;
    }

    private stringToSourceBreakpoint(bp: string): DebugProtocol.SourceBreakpoint {
        const parts = bp.split('\0');
        return {
            line: parseInt(parts[0]),
            ...(parts[1] !== 'undefined' && {condition: parts[1]}),
            ...(parts[2] !== 'undefined' && {logMessage: parts[2]})
        };
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

    protected async setBreakPointsRequest(response: DebugProtocol.SetBreakpointsResponse, args: DebugProtocol.SetBreakpointsArguments): Promise<void> {
        console.log('setBreakPointsRequest');
        console.log(args);

        response.body = response.body || {breakpoints: []};

        const path = args.source.path!;

        const initialized: boolean = this.initializedPaths.get(path) ?? (Date.now() - this.attachTime > INITIALIZE_TIME_ALLOWANCE_MS);
        // Simple hack: set initialized to `true` if enough time has passed since the attach request.

        if (initialized) {
            console.log(`Already initialized for this path.  Looking for user input (create or delete breakpoints)`);
            const prevBPs: DebugProtocol.SourceBreakpoint[] = this.previousSetBreakpointRequests.get(path) ?? [];
            const currBPs: DebugProtocol.SourceBreakpoint[] = args.breakpoints ?? [];

            const prevBPSet = new Set(prevBPs.map(bp => this.sourceBreakpointToString(bp)));
            const currBPSet = new Set(currBPs.map(bp => this.sourceBreakpointToString(bp)));

            const newBPs = [...currBPSet].filter(bp => !prevBPSet.has(bp));
            for (const bp of newBPs) {
                const cdbgBp = CdbgBreakpoint.fromSourceBreakpoint(args.source, this.stringToSourceBreakpoint(bp));
                await this.setExpressions(cdbgBp);
                this.saveBreakpointToServer(cdbgBp);
            }
            const delBPs = [...prevBPSet].filter(bp => !currBPSet.has(bp));
            for (const bp of delBPs) {
                const sourceBp = CdbgBreakpoint.fromSourceBreakpoint(args.source, this.stringToSourceBreakpoint(bp));
                for (const cdbgBp of this.breakpoints.values()) {
                    if (cdbgBp.matches(sourceBp)) {
                        this.deleteBreakpointFromServer(cdbgBp.id);
                    }
                }
            }

            this.previousSetBreakpointRequests.set(path, args.breakpoints ?? []);

            this.sendResponse(response);
            return;
        }

        console.log('Not initialized for this path yet.  Will attempt to synchronize between IDE and server');
        // TODO: Tidy this part of the code.
        const bpIds = new Set<string>();  // Keep track of which breakpoints we've seen.
        for (const breakpoint of args.breakpoints ?? []) {
            const cdbgBreakpoint = CdbgBreakpoint.fromSourceBreakpoint(args.source, breakpoint);

            let found = false;
            for (const bp of this.breakpoints.values()) {
                if (bp.matches(cdbgBreakpoint)) {
                    found = true;
                    // TODO: This should be a state update instead.
                    // bp.localBreakpoint = cdbgBreakpoint.localBreakpoint;

                    bpIds.add(bp.id);  // Say that we've seen this breakpoint even if there's more than one match.
                }
            }

            if (!found) {
                // Server breakpoints should have already been loaded.
                console.log('did not find a matching breakpoint on server; creating a new one.');
                this.saveBreakpointToServer(cdbgBreakpoint);
            }

            response.body.breakpoints.push(cdbgBreakpoint.localBreakpoint);
        }

        const extraServerBreakpoints = new Set(this.breakpoints.keys());
        bpIds.forEach((id) => extraServerBreakpoints.delete(id));

        // TODO: Probably only report active breakpoints.
        extraServerBreakpoints.forEach((id) => { this.reportNewBreakpointToIDE(id); });

        this.previousSetBreakpointRequests.set(path, args.breakpoints ?? []);
        this.initializedPaths.set(path, true);

        this.sendResponse(response);

        // TODO: This doesn't seem to be working properly?
        for (const breakpoint of response.body.breakpoints) {
            if (!breakpoint.verified) {
                this.reportCompletedBreakpointToIDE(`b-${breakpoint.id}`);
            }
        }
    }

    private reportCompletedBreakpointToIDE(bpId: string) {
        const breakpoint = this.breakpoints.get(bpId)!;
        const threadId = parseInt(bpId!.substring(2));

        const threadEvent = new ThreadEvent('started', threadId);
        this.sendEvent(threadEvent);

        const stoppedEvent = new StoppedEvent(breakpoint.hasError() ? 'Error' : 'Snapshot', threadId);
        this.sendEvent(stoppedEvent);

        // TODO: Tidy this up; this state change shouldn't be in this method.
        const localBreakpoint = breakpoint.localBreakpoint;
        localBreakpoint.verified = false;
        localBreakpoint.message = breakpoint.hasError() ? new StatusMessage(breakpoint.serverBreakpoint).message : 'Snapshot captured';
        console.log(`reporting breakpoint ${localBreakpoint.id} as unverified`);
        console.log(localBreakpoint);
        const breakpointEvent = new BreakpointEvent('changed', localBreakpoint);
        this.sendEvent(breakpointEvent);
    }

    private reportNewBreakpointToIDE(bpId: string) {
        const breakpoint = this.breakpoints.get(bpId);
        if (!breakpoint) {
            console.log(`attempting to report breakpoint to IDE but it is missing: ${bpId}`);
            return;
        }
        const breakpointEvent = new BreakpointEvent('new', breakpoint.localBreakpoint);
        this.sendEvent(breakpointEvent);
    }

    private saveBreakpointToServer(breakpoint: CdbgBreakpoint): void {
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

    private deleteBreakpointFromServer(bpId: string): void {
        console.log(`deleting breakpoint from server: ${bpId}`);
        this.breakpoints.delete(bpId);
        this.db?.ref(`cdbg/breakpoints/${this.debuggeeId}/active/${bpId}`).set(null);
    }

    /**
     * Provides the stack frames for a given "thread".
     * 
     * In this implementation, the thread represents a snapshot.  This should only be called
     * with a threadId that maps to a breakpointId where the breakpoint has a snapshot or error.
     * 
     * @param response 
     * @param args 
     * @param request 
     * @returns 
     */
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
                // TODO: Might want to have a stack frame that matches the breakpoint's location first.  That way the breakpoint will be selected.
                new StackFrame(0, new StatusMessage(breakpoint.serverBreakpoint).message ?? ""),
            ];
            this.sendResponse(response);
            return;
        }

        if (breakpoint.serverBreakpoint?.stackFrames) {
            const stackFrames = [];
            const serverFrames = breakpoint.serverBreakpoint!.stackFrames!;
            for (let i = 0; i < serverFrames.length; i++) {
                const path = serverFrames[i].location?.path ?? "Unknown path";
                stackFrames.push(new StackFrame(i, serverFrames[i].function ?? "Unknown function", new Source(path, addPwd(path)), serverFrames[i].location?.line ?? 0));
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

        console.log(`scopes request for breakpoint - stack frame: ${this.currentFrameId}`);
        console.log(this.currentBreakpoint);

        if (this.currentBreakpoint?.hasSnapshot()) {

            const stackFrame = this.currentBreakpoint!.serverBreakpoint!.stackFrames![this.currentFrameId];
            if (stackFrame.arguments) {
                scopes.push(new Scope('arguments', 1));
            } else {
                scopes.push(new Scope('No function arguments', 0));
            }

            if (stackFrame.locals) {
                scopes.push(new Scope('locals', 2));
            } else {
                scopes.push(new Scope('No local variables', 0));
            }

            if (this.currentFrameId === 0 && this.currentBreakpoint?.serverBreakpoint?.evaluatedExpressions) {
                scopes.push(new Scope('expressions', 3));
            }
        }

        response.body.scopes = scopes;
        this.sendResponse(response);
    }

    /**
     * https://microsoft.github.io/debug-adapter-protocol/specification#Requests_Variables
     */
    protected async variablesRequest(response: DebugProtocol.VariablesResponse, args: DebugProtocol.VariablesArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        console.log('variablesRequest');
        console.log(args);

        response.body = response.body || {};

        let variables: DebugProtocol.Variable[] = [];

        if (args.variablesReference === 0) {
            // No local variables.  No content.
        } else if (args.variablesReference === 1 || args.variablesReference === 2) {
            const stackFrames = this.currentBreakpoint?.serverBreakpoint?.stackFrames ?? [];
            if (this.currentFrameId < stackFrames.length) {
                const stackFrame = stackFrames[this.currentFrameId];
                const cdbgVars: CdbgVariable[] | undefined = args.variablesReference === 1 ?  stackFrame.arguments : stackFrame.locals;
                variables = (cdbgVars ?? []).map(v => this.cdbgVarToDap(v));
            } else {
                console.log('cannot do a thing');
            }
        } else if (args.variablesReference === 3) {
            const expressions = this.currentBreakpoint?.serverBreakpoint?.evaluatedExpressions ?? [];
            variables = expressions.map(v => this.cdbgVarToDap(v));
        } else {
            let vartable: CdbgVariable[] = this.currentBreakpoint!.serverBreakpoint!.variableTable ?? [];
            let varTableIndex = args.variablesReference - 100;

            if (varTableIndex >= vartable.length) {
                varTableIndex -= vartable.length;
                vartable = this.currentBreakpoint!.extendedVariableTable;
            }

            variables = (vartable[varTableIndex].members ?? []).map(v => this.cdbgVarToDap(v));
        }

        response.body.variables = variables;
        console.log(response);
        this.sendResponse(response);
    }

    private cdbgVarToDap(unresolvedCdbgVar: CdbgVariable): DebugProtocol.Variable {
        const cdbgVar: CdbgVariable = this.resolveCdbgVariable(unresolvedCdbgVar);

        // Reference documentation for DAP Variable:
        // https://microsoft.github.io/debug-adapter-protocol/specification#Types_Variable
        //
        // To note, we are expressly not populating the 'namedVariables' or
        // 'indexedVariables' fields. These are meant to be set if there are a
        // large number of children, the information could then be used in a
        // paged UI which would fetch the data in chunks. Given the Snapshot
        // Debugger agents all place limits on the amount of data that is
        // captured, this is not a concern here, we just always return all data.
        //
        // In addition, the 'presentationHint' field is also not populated. The
        // Snapshot Debugger agents do not capture any data that could be used
        // provide any of the infiormation covered in:
        // https://microsoft.github.io/debug-adapter-protocol/specification#Types_VariablePresentationHint

        let variablesReference = cdbgVar.varTableIndex ? cdbgVar.varTableIndex! + 100 : 0;
        const isNewExtendedVarTableEntryRequired = (variablesReference == 0) && ((cdbgVar.members ?? []).length > 0);
        if (isNewExtendedVarTableEntryRequired) {
            const vartable: CdbgVariable[] = this.currentBreakpoint!.serverBreakpoint!.variableTable ?? [];
            const extendedVartable = this.currentBreakpoint!.extendedVariableTable;
            variablesReference = 100 + vartable.length + extendedVartable.length;
            extendedVartable.push(unresolvedCdbgVar);
        }

        // Special case check for the situation where the agent communicates a
        // status message such as 'Empty container'.  If the Variable has one
        // member, and that member only has the status message populated, we set
        // variablesReference to 0 so the UI won't allow expansion of the
        // Variable. The status message will already be shown in the variable
        // summary.
        const members = cdbgVar.members ?? []
        if (members.length == 1 && members[0].value === undefined && members[0].status !== undefined) {
            variablesReference = 0;
        }

        let dapVar: DebugProtocol.Variable = {
            name: cdbgVar.name ?? '',
            value: this.getVariableValue(cdbgVar),
            variablesReference,
        };

        if (this.setVariableType && cdbgVar.type !== undefined) {
            dapVar.type = cdbgVar.type;
        }

        return dapVar;
    }

    private getVariableValue(variable: CdbgVariable): string {
        const message: string|undefined = new StatusMessage(variable).message;
        let members = variable.members ?? []

        if (variable.value !== undefined) {
            return message ? `${variable.value} (DBG_MSG  ${message})` : variable.value;
        } else if (members.length == 0 && message) {
            return message;
        }

        const type = variable.type ?? "";
        const membersSummary = members.map(m => {
            m = this.resolveCdbgVariable(m);
            const message: string|undefined = new StatusMessage(m).message;

            // Special case where we can make the UI output look nicer by only including them message.
            if (!m.name && !m.value && message) {
                return message;
            }

            const name =  m.name ?? "";

            let value = ""
            if (m.value !== undefined) {
                value = m.value;
            } else if (message !== undefined) {
                value = `DBG_MSG : ${message}`;
            } else {
                // Unicode 2026 is the 'Horizontal Ellipsis' character, 3 tightly packed periods
                value = "{\u2026}";
            }

            return `${name}: ${value}`;
        });

        return `${type} {${membersSummary.join(", ")}}`
    }

    private resolveCdbgVariable(variable: CdbgVariable,  predecessors = new Set<number>()): CdbgVariable {
        let vartable = this.currentBreakpoint!.serverBreakpoint!.variableTable ?? [];

        // In this case there's nothing to resolve, already done.
        if (variable.varTableIndex === undefined) {
            return variable;
        }

        let index = variable.varTableIndex;
        if (index >= vartable.length) {
            index -= vartable.length;
            vartable = this.currentBreakpoint!.extendedVariableTable;
        }

        // This would be unexpected, something would be wrong with the snapshot itself.
        if (index < 0 || index >= vartable.length) {
            return variable;
        }

        // Guard against a loop as this function calls itself recursively. This is a safeguard,
        // in practice it's not expected to happen.
        if (predecessors.has(index)) {
            return variable;
        }

        predecessors.add(index)
        const resolvedVariable = this.resolveCdbgVariable(vartable[index], predecessors);

        // It's not expected there would be conflicts in fields present, but just in case we
        // prioritize the resolved variable by placing it first
        return {...resolvedVariable, ...variable}
    }


    private async setExpressions(cdbgBp: CdbgBreakpoint): Promise<void> {
        if (!this.userPreferences.isExpressionsPromptEnabled) {
            return;
        }

        const expressions = await this.promptUserForExpressions();

        if (expressions) {
            cdbgBp.serverBreakpoint.expressions = expressions;
        }
    }

    private async promptUserForExpressions(): Promise<string[]|undefined> {
        let expressions = string[];

        const expressionsString = await vscode.window.showInputBox({
            "title": "Expressions",
            "prompt": "Separator **"
        });

        return expressionsString?.split("**").map(e => e.trim()).filter(e => e.length > 0);
    }

    /**
     * Provides the IDE the list of threads to display.
     * 
     * The threads to display will be the set of snapshots that have been captured or breakpoints with errors.
     * @param response 
     * @param request 
     */
    protected async threadsRequest(response: DebugProtocol.ThreadsResponse, request?: DebugProtocol.Request | undefined): Promise<void> {
        response.body = response.body || {};

        const threads: DebugProtocol.Thread[] = [];
        for (const bpId of this.breakpoints.keys()) {
            const bp = this.breakpoints.get(bpId)!;
            if (bp.hasSnapshot() || bp.hasError()) {
                const thread: DebugProtocol.Thread = {
                    id: parseInt(bpId.substring(2)),
                    name: `${bp.shortPath}:${bp.line} - ${bp.id}`
                };
                
                threads.push(thread);
            }
        }

        response.body.threads = threads;
        console.log(`reporting threads`);
        this.sendResponse(response);

        // and suspend all the threads.  This doesn't work right now because sending a thread-related event causes threads to be fetched again.
/*        for (const thread of threads) {
            const bp = this.breakpoints.get(`b-${thread.id}`)!;
            const event = new StoppedEvent(bp.hasError() ? 'error' : 'snapshot', thread.id);
            this.sendEvent(event);
        }*/
    }
}
