import {
    DebugSession,
    InitializedEvent, StoppedEvent, BreakpointEvent,
    StackFrame, Scope, Source, ThreadEvent, ContinuedEvent
} from '@vscode/debugadapter';
import * as vscode from 'vscode';
import { CdbgBreakpoint, SourceBreakpointExtraParams, Variable as CdbgVariable } from './breakpoint';
import { promptUserForExpressions } from './expressionsPrompter';
import { IdeBreakpoints } from './ideBreakpoints';
import { pickLogLevelNewlyCreated } from './logLevelPicker';
import { pickSnapshot } from './snapshotPicker';
import { StatusMessage } from './statusMessage';
import { UserPreferences } from './userPreferences';
import { IsActiveWhenClauseContext } from './whenClauseContextUtil';
import { initializeApp, App, deleteApp } from 'firebase-admin/app';
import { getDatabase } from 'firebase-admin/database';

import { DebugProtocol } from '@vscode/debugprotocol';
import { Database } from 'firebase-admin/lib/database/database';
import { addPwd, sourceBreakpointToString, withTimeout } from './util';
import { debugLog, setDebugLogEnabled } from './debugUtil';
import { pickDebuggeeId } from './debuggeePicker';
import { BreakpointManager } from './breakpointManager';
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
    /** URL to the Firebase RTDB database. */
    databaseUrl: string | undefined;

    /** Debuggee Id of an already registered debuggee. */
    debuggeeId: string;

    /** Whether to output debug messages to console. */
    debugOutput: boolean;
}


export class SnapshotDebuggerSession extends DebugSession {
    private app: App | undefined = undefined;
    private db: Database | undefined = undefined;
    private debuggeeId: string = '';
    private projectId: string = '';
    private account: string = '';

    private currentBreakpoint: CdbgBreakpoint | undefined = undefined;
    private currentFrameId: number = 0;

    private initializedPaths: Set<string> = new Set();
    private ideBreakpoints: IdeBreakpoints = new IdeBreakpoints();

    private setVariableType: boolean = false;
    private userPreferences: UserPreferences;
    private isDeferredInitializationDone = false;

    // At initialization time, immediately after the attach, any files that have
    // breakpoints/logpoints set in the IDE will be passed to the adapter via
    // setBreakPointsRequests, one call per file. In addition, these calls are
    // not serialized, there can be multiple outstanding. If there are logpoints
    // that need to be synced to the backend as part of this, we prompt the user
    // for the log level for each logpoint. This can cause delays in this
    // initial processing since it's gated on user input and will delay the
    // completion of the setBreakPointsRequest calls. While this phase is
    // still active we need to delay the work runDeferredInitialization does.
    // This variable tracks how many such active calls we have and is used for
    // the purpose of delaying runDeferredInitialization, once this value is 0,
    // it can proceed.
    private activeInitializePathCount = 0;

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
    }

    protected customRequest(command: string, response: DebugProtocol.Response, args: any, request?: DebugProtocol.Request | undefined): void {
        debugLog(`Received custom request: ${command}`);
        switch (command) {
            case CustomRequest.RUN_HISTORICAL_SNAPSHOT_PICKER:
                this.runPickSnapshot();
                break;

            default:
                debugLog(`Unknown custom request: ${command}`);
        }
    }

    private async connectToFirebase(credential: GcloudCredential, progress: vscode.Progress<{ message: string, increment: number }>, configuredDatabaseUrl?: string): Promise<Database> {
        // Build the database URL.
        const databaseUrls = [];
        if (configuredDatabaseUrl) {
            databaseUrls.push(configuredDatabaseUrl);
        } else {
            databaseUrls.push(`https://${this.projectId}-cdbg.firebaseio.com`);
            databaseUrls.push(`https://${this.projectId}-default-rtdb.firebaseio.com`);
        }

        for (const databaseUrl of databaseUrls) {
            progress.report({ message: `Connecting to ${databaseUrl}`, increment: 20 });
            this.app = initializeApp({
                credential: credential,
                databaseURL: databaseUrl
            }, FIREBASE_APP_NAME);

            const db = getDatabase(this.app);

            // Test the connection by reading the schema version.
            try {
                const version_snapshot = await withTimeout(
                    2000,
                    db.ref('cdbg/schema_version').get());
                if (version_snapshot) {
                    const version = version_snapshot.val();
                    debugLog(
                        `Firebase app initialized.  Connected to ${databaseUrl}` +
                        ` with schema version ${version}`
                    );

                    return db;
                } else {
                    throw new Error('failed to fetch schema version from database');
                }
            } catch (e) {
                debugLog(`failed to connect to database ${databaseUrl}: ` + e);
                deleteApp(this.app);
                this.app = undefined;
            }
        }

        throw new Error(`Failed to initialize FirebaseApp, attempted URLs: ${databaseUrls}`);
    }

    protected async attachRequest(response: DebugProtocol.AttachResponse, args: IAttachRequestArguments) {
        setDebugLogEnabled(args.debugOutput);

        const options = {
            title: 'Attaching to Snapshot Debugger',
            location: vscode.ProgressLocation.Notification
        };

        await vscode.window.withProgress(options, async (progress) => {
            debugLog("Attach Request");
            debugLog(args);

            progress.report({ message: 'Fetching user account', increment: 10 });
            const credential = new GcloudCredential();
            try {
                this.account = await credential.getAccount();
            } catch (err) {
                this.sendErrorResponse(response, 4, 'Cannot determine user account.\n\nIs `gcloud` installed and have you logged in?');
                throw err;
            }

            // We only need the project ID if a database URL was not specified.
            if (!args.databaseUrl) {
                progress.report({ message: 'Fetching project ID', increment: 20 });
                try {
                    this.projectId = await credential.getProjectId();
                } catch (err) {
                    this.sendErrorResponse(response, 3, 'Cannot determine project Id.\n\nIs `gcloud` installed and have you logged in?');
                    throw err;
                }
            }

            try {
                this.db = await this.connectToFirebase(credential, progress, args.databaseUrl);
            } catch (err) {
                this.sendErrorResponse(response, 2,
                    'Cannot connect to Firebase.\n\n' +
                    '* Are you logged into `gcloud`?\n' +
                    '* Have you set up the Snapshot Debugger on this project?\n' +
                    '* Do you have Firebase Database Admin permissions or higher?\n' +
                    '* Is the correct database URL specified in your launch.json?');
                throw err;
            }

            credential.initialized = true;
        });

        const debuggeeId = args.debuggeeId || await pickDebuggeeId(this.db!);
        if (!debuggeeId) {
            response.success = false;
            this.sendErrorResponse(response, 1, 'No Debuggee selected');
            return;
        }
        this.debuggeeId = debuggeeId;
        debugLog("Using debuggee id: ", debuggeeId);

        // Set up breakpoint manager.
        this.breakpointManager = new BreakpointManager(debuggeeId, this.db!);
        this.breakpointManager.onNewBreakpoint = (bp) => this.reportNewBreakpointToIDE(bp);
        this.breakpointManager.onChangedBreakpoint = (bp, originalLine) => this.reportChangedBreakpointToIDE(bp, originalLine);
        this.breakpointManager.onCompletedBreakpoint = (bp) => this.reportCompletedBreakpointToIDE(bp);

        // Load all breakpoints before setting up listeners to avoid race conditions.
        // Breakpoints will be loaded twice.
        await this.breakpointManager.loadServerBreakpoints();
        this.breakpointManager.setUpServerListeners();

        IsActiveWhenClauseContext.enable();
        debugLog('Attached');
        this.sendResponse(response);

        this.isDeferredInitializationDone = false;
        setTimeout(() => { this.runDeferredInitialization() }, INITIALIZE_TIME_ALLOWANCE_MS);

        // At this point we're considered sufficiently initialized to take requests from the IDE.
        this.sendEvent(new InitializedEvent());
    }

    protected async disconnectRequest(response: DebugProtocol.DisconnectResponse, args: DebugProtocol.DisconnectArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        // A new instance of this class is created for each debugging session.
        // Treat this function as a desctructor to clean up any resources that require cleanup.
        debugLog("Received Disconnect request: ", args);

        IsActiveWhenClauseContext.disable();

        if (this.app) {
            deleteApp(this.app);
            this.app = undefined;
        }

        this.sendResponse(response);
    }

    protected continueRequest(response: DebugProtocol.ContinueResponse, args: DebugProtocol.ContinueArguments, request?: DebugProtocol.Request | undefined): void {
        debugLog("Received continue request: ", args);
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
        debugLog("Received Pause request: ", args);
        await vscode.window.showInformationMessage("This operation is not supported by the Snapshot Debugger", { "modal": true });
        this.sendResponse(response);
        this.sendEvent(new ContinuedEvent(args.threadId));
    }

    protected async nextRequest(response: DebugProtocol.NextResponse, args: DebugProtocol.NextArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        // This handler maps to the 'Step Over' debugger toolbar button.
        debugLog("Received Next request: ", args);
        await this.handleUnsupportedStepRequest(args.threadId);
        this.sendResponse(response);
    }

    protected async stepInRequest(response: DebugProtocol.StepInResponse, args: DebugProtocol.StepInArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        // This handler maps to the 'Step Into' debugger toolbar button.
        debugLog("Received StepIn request: ", args);
        await this.handleUnsupportedStepRequest(args.threadId);
        this.sendResponse(response);
    }

    protected async stepOutRequest(response: DebugProtocol.StepOutResponse, args: DebugProtocol.StepOutArguments, request?: DebugProtocol.Request | undefined): Promise<void> {
        // This handler maps to the 'Step Out' debugger toolbar button.
        debugLog("Received StepOut request: ", args);
        await this.handleUnsupportedStepRequest(args.threadId);
        this.sendResponse(response);
    }

    protected async setBreakPointsRequest(response: DebugProtocol.SetBreakpointsResponse, args: DebugProtocol.SetBreakpointsArguments): Promise<void> {
        debugLog('setBreakPointsRequest');
        debugLog(args);

        response.body = response.body || { breakpoints: [] };
        const path = args.source.path!;
        const initialized: boolean = this.initializedPaths.has(path) || this.isDeferredInitializationDone;
        const sourceBreakpoints = [];
        const linesPresent: Set<number> = new Set();
        let finalizeInitializePath: (() => void) | undefined = undefined;

        for (const bp of (args.breakpoints ?? [])) {
            linesPresent.add(bp.line);
            sourceBreakpoints.push({...bp})
        }

        for (const bp of sourceBreakpoints) {
            const lineMapping = this.breakpointManager?.getLineMapping(path, bp.line);
            if (lineMapping !== undefined && !linesPresent.has(lineMapping)) {
                linesPresent.add(lineMapping);
                bp.line = lineMapping;
            }
        }

        if (initialized) {
            debugLog(`Already initialized for this path.  Looking for user input (create or delete breakpoints)`);
            const bpDiff = this.ideBreakpoints.applyNewIdeSnapshot(path, sourceBreakpoints);

            for (const bp of bpDiff.added) {
                const extraParams: SourceBreakpointExtraParams = {};
                if (bp.logMessage) {
                    extraParams.logLevel = await pickLogLevelNewlyCreated();
                } else {
                    extraParams.expressions = await this.runExpressionsPrompt();
                }

                const cdbgBp = CdbgBreakpoint.fromSourceBreakpoint(args.source, bp, this.account, extraParams);
                this.breakpointManager!.saveBreakpointToServer(cdbgBp);
            }

            for (const bp of bpDiff.deleted) {
                // TODO: Change this to use getBreakpointBySourceBreakpoint() on
                // breakpointmanager.
                const sourceBp = CdbgBreakpoint.fromSourceBreakpoint(args.source, bp, this.account);
                for (const cdbgBp of this.breakpointManager!.getBreakpoints()) {
                    if (cdbgBp.matches(sourceBp)) {
                        this.breakpointManager!.deleteBreakpointFromServer(cdbgBp.id);
                    }
                }
            }
        } else {
            debugLog('Not initialized for this path yet.  Will attempt to synchronize between IDE and server');
            this.activeInitializePathCount++;

            this.ideBreakpoints.applyNewIdeSnapshot(path, sourceBreakpoints);

            const localBreakpoints = sourceBreakpoints.map((bp) => CdbgBreakpoint.fromSourceBreakpoint(args.source, bp, this.account));
            const flushServerBreakpointsToIDE = await this.breakpointManager!.initializeWithLocalBreakpoints(path, localBreakpoints);

            // See below, but we need to defer this work until after the
            // sendReponse occurs.
            finalizeInitializePath = () => {
                flushServerBreakpointsToIDE();
                this.activeInitializePathCount--;
            }

            this.initializedPaths.add(path);
        }

        // The breakpoints in the response must have a 1:1 mapping in the same order as found in the request.
        response.body.breakpoints = [];
        for (const bp of (sourceBreakpoints)) {
            const cdbg = this.breakpointManager?.getBreakpointBySourceBreakpoint(bp);
            if (cdbg) {
                response.body.breakpoints.push({...cdbg.localBreakpoint});
            } else {
                debugLog("Unexpected breakpoint not found!: "), sourceBreakpointToString(bp);
            }
        }

        debugLog('setBreakpointsResponse:');
        debugLog(response.body);
        this.sendResponse(response);

        // Some work needs to be delayed to the very end of this function, after
        // the sendResponse has occurred. One example is the syncing of any
        // breakpoints that exist on the server to the IDE. We ensure these
        // notification as sent after the sendResponse so that the IDE does not
        // receive them while the setBreakPointsRequest is still active.
        if (finalizeInitializePath) {
            finalizeInitializePath();
        }
    }

    private runDeferredInitialization(): void {
        if (this.activeInitializePathCount > 0) {
            setTimeout(() => { this.runDeferredInitialization() }, 250);
            return;
        }

        debugLog("Syncing active breakpoints from backend.");

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
        debugLog(`reporting breakpoint ${bp.id} as unverified`);
        this.sendEvent(new BreakpointEvent('changed', bp.localBreakpoint));
    }

    private reportNewBreakpointToIDE(bp: CdbgBreakpoint): void {
        debugLog(`Notifying IDE of BP: ${bp.id} - ${bp.shortPath}:${bp.line}`);
        debugLog(bp.localBreakpoint);
        this.ideBreakpoints.add(bp.path, bp.ideBreakpoint);
        this.sendEvent(new BreakpointEvent('new', bp.localBreakpoint));
    }

    private reportChangedBreakpointToIDE(bp: CdbgBreakpoint, originalLine: number): void {
        debugLog(`Notifying IDE of Changed BP: ${bp.id} - ${bp.shortPath}:${bp.line}`);
        debugLog(bp.localBreakpoint);
        this.ideBreakpoints.updateLine(bp.path, originalLine, bp.line);
        this.sendEvent(new BreakpointEvent('changed', bp.localBreakpoint));
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
            debugLog(`Unexpected request for unknown breakpoint ${bpId}`);
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
            debugLog(`Not sure what's going on with this one:`);
            debugLog(breakpoint);
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
                debugLog('cannot do a thing');
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
        debugLog(response);
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
        debugLog(`reporting threads`);
        this.sendResponse(response);
    }
}
