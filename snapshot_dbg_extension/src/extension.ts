import * as vscode from 'vscode';
import { WorkspaceFolder, DebugConfiguration, DebugSession, ProviderResult, CancellationToken } from 'vscode';
import { IsActiveWhenClauseContext } from './whenClauseContextUtil';

import { CustomRequest, SnapshotDebuggerSession } from './adapter';
import { UserPreferences } from './userPreferences';

// This method is called when the extension is activated.
// The extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {
    IsActiveWhenClauseContext.create();

    const userPreferences: UserPreferences = {"isExpressionsPromptEnabled": true};
    context.subscriptions.push(vscode.commands.registerCommand('extension.snapshotdbg.getServiceAccountPath', async config => {
        const result = await vscode.window.showOpenDialog({
            "openLabel": "Select",
            "title": "Select your service account credentials file",
            "filters": { "json": ["json"] }
        });

        if (result && result[0]) {
            return result[0].fsPath;
        } else {
            // TODO: Figure out how to fail gracefully.
            return undefined;
        }
    }));

    context.subscriptions.push(vscode.commands.registerCommand('extension.snapshotdbg.viewHistoricalSnapshot', async args => {
        const activeDebugSession: DebugSession | undefined = vscode.debug.activeDebugSession;
        if (activeDebugSession) {
            activeDebugSession.customRequest(CustomRequest.RUN_HISTORICAL_SNAPSHOT_PICKER);
        } else {
            console.log("Unexpected no active SnapshotDebugger session.")
        }
    }));

    context.subscriptions.push(vscode.commands.registerCommand('extension.snapshotdbg.toggleExpressions', async args => {
        const action = userPreferences.isExpressionsPromptEnabled ? "Disabled" : "Enabled";
        const message = `${action} expresssions prompt when creating a breakpoint.`;
        const reverseAction = userPreferences.isExpressionsPromptEnabled ? "re-enable" : "disable";
        const reverseMessage = `Click again to ${reverseAction} it.`;

        userPreferences.isExpressionsPromptEnabled = !userPreferences.isExpressionsPromptEnabled;
        await vscode.window.showInformationMessage(message, {"detail": reverseMessage, "modal": true});
    }));

    const provider = new SnapshotDebuggerConfigurationProvider();
    context.subscriptions.push(vscode.debug.registerDebugConfigurationProvider('snapshotdbg', provider));

    const factory = new DebugAdapterFactory(userPreferences);
    context.subscriptions.push(vscode.debug.registerDebugAdapterDescriptorFactory('snapshotdbg', factory));
}

// This method is called when the extension is deactivated
export function deactivate() {
}


class SnapshotDebuggerConfigurationProvider implements vscode.DebugConfigurationProvider {
    resolveDebugConfiguration(folder: WorkspaceFolder | undefined, config: DebugConfiguration, token?: CancellationToken): ProviderResult<DebugConfiguration> {
        // TODO: Figure out if this is ever called.
        if (!config.serviceAccountPath) {
            return vscode.window.showInformationMessage("Cannot find service account credentials").then(_ => {
                return undefined;    // abort launch
            });
        }
        return config;
    }
}

class DebugAdapterFactory implements vscode.DebugAdapterDescriptorFactory {
    private userPreferences: UserPreferences;

    constructor(userPreferences: UserPreferences) {
        this.userPreferences = userPreferences;
    }

    createDebugAdapterDescriptor(session: vscode.DebugSession, executable: vscode.DebugAdapterExecutable | undefined): vscode.ProviderResult<vscode.DebugAdapterDescriptor> {
        return new vscode.DebugAdapterInlineImplementation(new SnapshotDebuggerSession(this.userPreferences));
    }

}
