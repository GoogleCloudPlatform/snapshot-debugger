import {
    DebugSession,
    InitializedEvent, StoppedEvent, BreakpointEvent,
    Thread, StackFrame, Scope, Source, Variable, ThreadEvent, ContinuedEvent
} from '@vscode/debugadapter';
import * as vscode from 'vscode';
import { CdbgBreakpoint, SourceBreakpointExtraParams, Variable as CdbgVariable } from './breakpoint';
import { promptUserForExpressions } from './expressionsPrompter';
import { IdeBreakpoints } from './ideBreakpoints';
import { pickLogLevel } from './logLevelPicker';
import { pickSnapshot } from './snapshotPicker';
import { StatusMessage } from './statusMessage';
import { UserPreferences } from './userPreferences';
import { IsActiveWhenClauseContext } from './whenClauseContextUtil';
import { initializeApp, cert, App, deleteApp, Credential } from 'firebase-admin/app';
import { DataSnapshot, getDatabase } from 'firebase-admin/database';

import { DebugProtocol } from '@vscode/debugprotocol';
import { Database } from 'firebase-admin/lib/database/database';
import { addPwd, sleep, sourceBreakpointToString, stringToSourceBreakpoint, stripPwd } from './util';
import { pickDebuggeeId } from './debuggeePicker';
import { BreakpointManager } from './breakpointManager';
import { credential, GoogleOAuthAccessToken } from 'firebase-admin';
import { GcloudCredential } from './gcloudCredential';

const FIREBASE_APP_NAME = 'snapshotdbg';
const INITIALIZE_TIME_ALLOWANCE_MS = 2 * 1000; // 2 seconds

export enum CustomRequest {
    RUN_HISTORICAL_SNAPSHOT_PICKER = 'runHistoricalSnapshotPicker',
}

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

    private initializedPaths: Set<string> = new Set();
    private ideBreakpoints: IdeBreakpoints = new IdeBreakpoints();

    private setVariableType: boolean = false;
    private userPreferences: UserPreferences;
    private isDeferredInitializationDone = false;

    private breakpointManager?: BreakpointManager;

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
        response.body.supportsStepInTargetsRequest = false;
        response.body.supportsConditionalBreakpoints = true;
        response.body.supportsLogPoints = true;
        response.body.supportsValueFormattingOptions = false;
        response.body.supportsConditionalBreakpoints = true;
        response.body.supportsSingleThreadExecutionRequests = true;

        this.sendResponse(response);
        console.log('Initialized');
    }

    protected customRequest(command: string, response: DebugProtocol.Response, args: any, request?: DebugProtocol.Request | undefined): void {
        console.log(`Received custom request: ${command}`);
        switch (command) {
            case CustomRequest.RUN_HISTORICAL_SNAPSHOT_PICKER:
                this.runPickSnapshot();
                break;

            default:
                console.log(`Unknown custom request: ${command}`);
        }
    }

    protected async attachRequest(response: DebugProtocol.AttachResponse, args: IAttachRequestArguments) {
        console.log("Attach Request");
        console.log(args);

        const credential = new GcloudCredential();
        const projectId = await credential.getProjectId();
        console.log(`Using account: ${await credential.getAccount()}`);

        /*
        const serviceAccount = require(args.serviceAccountPath);
        const projectId = serviceAccount['project_id'];
        */
        let databaseUrl = args.databaseUrl;
        if (!databaseUrl) {
            databaseUrl = `https://${projectId}-cdbg.firebaseio.com`;
        }

        this.app = initializeApp({
//            credential: cert(serviceAccount),
            credential: credential,
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
        console.log("Using debuggee id: ", debuggeeId);

        // Set up breakpoint manager.
        this.breakpointManager = new BreakpointManager(debuggeeId, this.db);
        this.breakpointManager.onNewBreakpoint = (bp) => this.reportNewBreakpointToIDE(bp);
        this.breakpointManager.onCompletedBreakpoint = (bp) => this.reportCompletedBreakpointToIDE(bp);

        // Load all breakpoints before setting up listeners to avoid race conditions.
        // Breakpoints will be loaded twice.
        await this.breakpointManager.loadServerBreakpoints();
        this.breakpointManager.setUpServerListeners();

        IsActiveWhenClauseContext.enable();
        console.log('Attached');
        this.sendResponse(response);

        this.isDeferredInitializationDone = false;
        setTimeout(() => { this.runDeferredInitialization() }, INITIALIZE_TIME_ALLOWANCE_MS);

        // At this point we're considered sufficiently initialized to take requests from the IDE.
        this.sendEvent(new InitializedEvent());
    }

    protected async disconnectRequest(response: DebugProtocol.DisconnectResponse, args: DebugProtocol.DisconnectArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        // A new instance of this class is created for each debugging session.
        // Treat this function as a desctructor to clean up any resources that require cleanup.
        console.log("Received Disconnect request: ", args);

        IsActiveWhenClauseContext.disable();

        if (this.app) {
            deleteApp(this.app);
            this.app = undefined;
        }

        this.sendResponse(response);
    }

    protected continueRequest(response: DebugProtocol.ContinueResponse, args: DebugProtocol.ContinueArguments, request?: DebugProtocol.Request | undefined): void {
        console.log("Received continue request: ", args);
        const bp = this.breakpointManager?.getBreakpoint(`b-${args.threadId}`);
        if (bp) {
            this.removeBreakpoint(bp);
        }

        response.body = { allThreadsContinued: false };
        this.sendResponse(response);
    }

    protected async pauseRequest(response: DebugProtocol.PauseResponse, args: DebugProtocol.PauseArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        // This handler maps to the lllljj'Pause' debugger toolbar button. As a
        // threadID is required, this handler will only ever run once we've
        // notified the UI of a thread (IE provided it with a breakpoint ID
        // which acts as a thread ID).
        console.log("Received Pause request: ", args);
        await vscode.window.showInformationMessage("This operation is not supported by the Snapshot Debugger", { "modal": true });
        this.sendResponse(response);
        this.sendEvent(new ContinuedEvent(args.threadId));
    }

    protected async nextRequest(response: DebugProtocol.NextResponse, args: DebugProtocol.NextArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        // This handler maps to the 'Step Over' debugger toolbar button.
        console.log("Received Next request: ", args);
        await this.handleUnsupportedStepRequest(args.threadId);
        this.sendResponse(response);
    }

    protected async stepInRequest(response: DebugProtocol.StepInResponse, args: DebugProtocol.StepInArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        // This handler maps to the 'Step Into' debugger toolbar button.
        console.log("Received StepIn request: ", args);
        await this.handleUnsupportedStepRequest(args.threadId);
        this.sendResponse(response);
    }

    protected async stepOutRequest(response: DebugProtocol.StepOutResponse, args: DebugProtocol.StepOutArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        // This handler maps to the 'Step Out' debugger toolbar button.
        console.log("Received StepOut request: ", args);
        await this.handleUnsupportedStepRequest(args.threadId);
        this.sendResponse(response);
    }

    protected async setBreakPointsRequest(response: DebugProtocol.SetBreakpointsResponse, args: DebugProtocol.SetBreakpointsArguments): Promise<void> {
        console.log('setBreakPointsRequest');
        console.log(args);

        response.body = response.body || { breakpoints: [] };

        const path = args.source.path!;

        const initialized: boolean = this.initializedPaths.has(path) || this.isDeferredInitializationDone;

        if (initialized) {
            console.log(`Already initialized for this path.  Looking for user input (create or delete breakpoints)`);
            const bpDiff = this.ideBreakpoints.applyNewIdeSnapshot(path, args.breakpoints ?? []);

            for (const bp of bpDiff.added) {
                const extraParams: SourceBreakpointExtraParams = {};
                if (bp.logMessage) {
                    extraParams.logLevel = await pickLogLevel();
                } else {
                    extraParams.expressions = await this.runExpressionsPrompt();
                }

                const cdbgBp = CdbgBreakpoint.fromSourceBreakpoint(args.source, bp, extraParams);
                this.breakpointManager!.saveBreakpointToServer(cdbgBp);
            }

            for (const bp of bpDiff.deleted) {
                const sourceBp = CdbgBreakpoint.fromSourceBreakpoint(args.source, bp);
                for (const cdbgBp of this.breakpointManager!.getBreakpoints()) {
                    if (cdbgBp.matches(sourceBp)) {
                        this.breakpointManager!.deleteBreakpointFromServer(cdbgBp.id);
                    }
                }
            }
        } else {
            console.log('Not initialized for this path yet.  Will attempt to synchronize between IDE and server');

            const sourceBreakpoints = args.breakpoints ?? [];

            // Ordering here matters. We need to do the applyNewIdeSnapshot
            // before the call to initializeWithLocalBreakpoints as that second
            // call will cause breakpoints to be added to this.ideBreakpoints,
            // and applyNewIdeSnapshot clobbers all pre-existing data.
            this.ideBreakpoints.applyNewIdeSnapshot(path, sourceBreakpoints);

            const localBreakpoints = sourceBreakpoints.map((bp) => CdbgBreakpoint.fromSourceBreakpoint(args.source, bp));
            this.breakpointManager!.initializeWithLocalBreakpoints(path, localBreakpoints);

            this.initializedPaths.add(path);
        }

        // The breakpoints in the response must have a 1:1 mapping in the same order as found in the request.
        response.body.breakpoints = [];
        for (const bp of (args.breakpoints ?? [])) {
            const cdbg = this.breakpointManager?.getBreakpointBySourceBreakpoint(bp);
            if (cdbg) {
                response.body.breakpoints.push(cdbg.localBreakpoint);
            } else {
              console.log("Unexpected breakpoint not found!");
            }
        }

        console.log('setBreakpointsResponse:');
        console.log(response.body);
        this.sendResponse(response);
    }

    private runDeferredInitialization(): void {
        console.log("Syncing active breakpoints from backend.");

        // We sync over all breakpoints that have not yet had their paths
        // synced.  After the attach request call, the IDE will immediately call
        // setBreakpointRequest for all paths (files) it already has breakpoints
        // for. Any path that had this happen will be marked in
        // this.initializedPaths.
        this.breakpointManager?.syncInitialActiveBreakpointsToIDE(this.initializedPaths);

        this.isDeferredInitializationDone = true;
    }

    private reportCompletedBreakpointToIDE(bp: CdbgBreakpoint) {
        const threadId = bp.numericId;

        const threadEvent = new ThreadEvent('started', threadId);
        this.sendEvent(threadEvent);

        const stoppedEvent = new StoppedEvent(bp.hasError() ? 'Error' : 'Snapshot', threadId);
        this.sendEvent(stoppedEvent);

        // TODO: Tidy this up; this state change shouldn't be in this method.
        // It should probably be in CdbgBreakpoint.fromSnapshot
        bp.localBreakpoint.verified = false;
        bp.localBreakpoint.message = bp.hasError() ? new StatusMessage(bp.serverBreakpoint).message : 'Snapshot captured';
        console.log(`reporting breakpoint ${bp.id} as unverified`);
        this.sendEvent(new BreakpointEvent('changed', bp.localBreakpoint));
    }

    private reportNewBreakpointToIDE(bp: CdbgBreakpoint): void {
        console.log(`Notifying IDE of BP: ${bp.id} - ${bp.shortPath}:${bp.line}`);
        this.ideBreakpoints.add(bp.path, bp.ideBreakpoint);
        this.sendEvent(new BreakpointEvent('new', bp.localBreakpoint));
    }

    private removeBreakpoint(bp: CdbgBreakpoint) {
        this.breakpointManager?.deleteBreakpointLocally(bp.id);
        this.removeBreakpointFromIDE(bp);
    }

    private removeBreakpointFromIDE(bp: CdbgBreakpoint) {
        this.ideBreakpoints.remove(bp.path, bp.ideBreakpoint);
        const threadId = bp.numericId;
        this.sendEvent(new ThreadEvent('exited', threadId));
        this.sendEvent(new BreakpointEvent('removed', bp.localBreakpoint));
    }

    private async handleUnsupportedStepRequest(threadId: number): Promise<void> {
        await vscode.window.showInformationMessage("This operation is not supported by the Snapshot Debugger", { "modal": true });
        const bp = this.breakpointManager?.getBreakpoint(`b-${threadId}`);
        if (bp) {
            this.removeBreakpoint(bp);
            this.breakpointManager?.loadCompleteSnapshot(bp);
        }
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
        const breakpoint = this.breakpointManager!.getBreakpoint(bpId);
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
        response.body = response.body || {};

        let variables: DebugProtocol.Variable[] = [];

        if (args.variablesReference === 0) {
            // No local variables.  No content.
        } else if (args.variablesReference === 1 || args.variablesReference === 2) {
            const stackFrames = this.currentBreakpoint?.serverBreakpoint?.stackFrames ?? [];
            if (this.currentFrameId < stackFrames.length) {
                const stackFrame = stackFrames[this.currentFrameId];
                const cdbgVars: CdbgVariable[] | undefined = args.variablesReference === 1 ? stackFrame.arguments : stackFrame.locals;
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
        const message: string | undefined = new StatusMessage(variable).message;
        let members = variable.members ?? []

        if (variable.value !== undefined) {
            return message ? `${variable.value} (DBG_MSG  ${message})` : variable.value;
        } else if (members.length == 0 && message) {
            return message;
        }

        const type = variable.type ?? "";
        const membersSummary = members.map(m => {
            m = this.resolveCdbgVariable(m);
            const message: string | undefined = new StatusMessage(m).message;

            // Special case where we can make the UI output look nicer by only including them message.
            if (!m.name && !m.value && message) {
                return message;
            }

            const name = m.name ?? "";

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

    private resolveCdbgVariable(variable: CdbgVariable, predecessors = new Set<number>()): CdbgVariable {
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
        return { ...resolvedVariable, ...variable }
    }


    private async runExpressionsPrompt(): Promise<string[] | undefined> {
        if (!this.userPreferences.isExpressionsPromptEnabled) {
            return undefined;
        }

        return await promptUserForExpressions();
    }

    public async runPickSnapshot() {
        if (this.db && this.debuggeeId) {
            const snapshot = await pickSnapshot(this.db, this.debuggeeId);
            if (snapshot) {
                await this.breakpointManager?.addHistoricalSnapshot(snapshot);
            }
        }
    }

    /**
     * Provides the IDE the list of threads to display.
     *
     * TODO: The pattern of calling this function, particularly with suspended threads, needs to be understood.
     *
     * The threads to display will be the set of snapshots that have been captured or breakpoints with errors.
     * @param response
     * @param request
     */
    protected async threadsRequest(response: DebugProtocol.ThreadsResponse, request?: DebugProtocol.Request | undefined): Promise<void> {
        response.body = response.body || {};

        const threads: DebugProtocol.Thread[] = [];
        for (const bp of this.breakpointManager!.getBreakpoints()) {
            const bpId = bp.id;
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
