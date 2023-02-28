import * as vscode from 'vscode';
import { WorkspaceFolder, DebugConfiguration, ProviderResult, CancellationToken } from 'vscode';

import { initializeApp, cert, App, deleteApp } from 'firebase-admin/app';
import { getDatabase } from 'firebase-admin/database';
import { SnapshotDebuggerSession } from './adapter';

const FIREBASE_APP_NAME = 'snapshotdbgext';

const withTimeout = (ms: number, promise: Promise<any>) => {
	const timeout = new Promise((_, reject) =>
	  setTimeout(() => reject(`Timed out after ${ms} ms.`), ms)
	);
	return Promise.race([promise, timeout]);
  };


let app: App;


/*
General notes:
* VSCode supports "attach" configuration for debuggers.  Snapshot debugger is "attach" instead of "launch"
* Breakpoint, Conditional breakpoint, and Logpoint are ALL supported!!
* HitCount also exists; could be a fun feature to add into the agents if we wanted to...

*/

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {

	// The command has been defined in the package.json file
	// Now provide the implementation of the command with registerCommand
	// The commandId parameter must match the command field in package.json
	let disposable = vscode.commands.registerCommand('snapshotdbg.helloWorld', async () => {
		// TODO: Change this into something that the user provides dynamically.
		// TODO: Make the database URL configurable.
		const serviceAccount = require('C:\\Users\\jwmct\\Downloads\\mctavish-test-project-firebase-adminsdk-dwaw7-2f7da9748f.json');
		const projectId = serviceAccount['project_id'];

		app = initializeApp(
			{
				credential: cert(serviceAccount),
				databaseURL: `https://${projectId}-cdbg.firebaseio.com`
				// TODO: Implement fallback logic.
				//databaseURL: `https://${projectId}-default-rtdb.firebaseio.com`
			},
			FIREBASE_APP_NAME
		);
	
		let db = getDatabase(app);

		vscode.window.showInformationMessage('About to grab version');

		const versionSnapshot = await withTimeout(1000, db.ref('cdbg/schema_version').get());
		
		vscode.window.showInformationMessage(`Version snapshot: ${versionSnapshot.val()}`);
	});

	context.subscriptions.push(disposable,
		// FIXME: This isn't going to work.
		vscode.commands.registerCommand('extension.snapshotdbg.debugEditorContents', (resource: vscode.Uri) => {
			let targetResource = resource;
			if (!targetResource && vscode.window.activeTextEditor) {
				targetResource = vscode.window.activeTextEditor.document.uri;
			}
			if (targetResource) {
				vscode.debug.startDebugging(undefined, {
					type: 'snapshotdbg',
					name: 'Attach',
					request: 'attach'
				});
			}
		})
	);

	
	context.subscriptions.push(vscode.commands.registerCommand('extension.snapshotdbg.getServiceAccountPath', async config => {
		const result = await vscode.window.showOpenDialog({
			"openLabel": "Select",
			"title": "Select your service account credentials file",
			"filters": {"json": ["json"]}
		});

		if (result && result[0]) {
			console.log(result[0].path);
			console.log(result[0].fsPath);
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

// This method is called when your extension is deactivated
export function deactivate() {
	deleteApp(app);
}


class SnapshotDebuggerConfigurationProvider implements vscode.DebugConfigurationProvider {
	resolveDebugConfiguration(folder: WorkspaceFolder | undefined, config: DebugConfiguration, token?: CancellationToken): ProviderResult<DebugConfiguration> {
		if (!config.serviceAccountPath) {
			// TODO: Figure out if this is ever called.
			return vscode.window.showInformationMessage("Cannot find service account tcredentials").then(_ => {
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