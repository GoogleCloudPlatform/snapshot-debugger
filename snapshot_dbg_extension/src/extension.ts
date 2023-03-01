import * as vscode from 'vscode';
import { WorkspaceFolder, DebugConfiguration, ProviderResult, CancellationToken } from 'vscode';

import { SnapshotDebuggerSession } from './adapter';

// This method is called when the extension is activated.
// The extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {
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

	const provider = new SnapshotDebuggerConfigurationProvider();
	context.subscriptions.push(vscode.debug.registerDebugConfigurationProvider('snapshotdbg', provider));

	const factory = new DebugAdapterFactory();
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
				return undefined;	// abort launch
			});
		}
		return config;
	}
}

class DebugAdapterFactory implements vscode.DebugAdapterDescriptorFactory {
	createDebugAdapterDescriptor(session: vscode.DebugSession, executable: vscode.DebugAdapterExecutable | undefined): vscode.ProviderResult<vscode.DebugAdapterDescriptor> {
		return new vscode.DebugAdapterInlineImplementation(new SnapshotDebuggerSession());
	}

}