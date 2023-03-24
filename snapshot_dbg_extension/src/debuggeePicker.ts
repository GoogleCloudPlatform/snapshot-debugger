import { Database } from 'firebase-admin/database';
import * as vscode from 'vscode';

class DebuggeeItem implements vscode.QuickPickItem {
    label: string;
    kind?: vscode.QuickPickItemKind | undefined;

    constructor(public debuggeeId: string, public detail: string) {
        this.label = debuggeeId;
    }
}

async function fetchDebuggees(db: Database): Promise<DebuggeeItem[]> {
    const debuggees: DebuggeeItem[] = [];

    const snapshot = await db.ref('/cdbg/debuggees').get();
    const savedDebuggees = snapshot.val();
    if (savedDebuggees) {
        for (const debuggeeId in savedDebuggees) {
            const timestamp = new Date(savedDebuggees[debuggeeId].lastUpdateTimeUnixMsec);
            debuggees.push(
                new DebuggeeItem(
                    debuggeeId,
                     `${savedDebuggees[debuggeeId].description} - ${timestamp.toISOString()}`));
        }
    } else {
        const noDebuggees = new DebuggeeItem("No debuggees found", "Please check your configuration");
        noDebuggees.debuggeeId = "";
        debuggees.push();
    }
    return debuggees;
}

export async function pickDebuggeeId(db: Database): Promise<string | undefined> {
    const selection = await vscode.window.showQuickPick(fetchDebuggees(db), {'title': 'Select Debuggee'});
    if (selection) {
        console.log(`Selected Debuggee: ${selection.debuggeeId}`);
        return selection.debuggeeId;
    } else {
        return undefined;
    }
}
