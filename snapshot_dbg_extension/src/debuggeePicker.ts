import { Database } from 'firebase-admin/database';
import * as vscode from 'vscode';

class DebuggeeItem implements vscode.QuickPickItem {
    label: string;
    detail: string;
    kind?: vscode.QuickPickItemKind | undefined;

    constructor(public debuggeeId: string, description: string, timestamp?: Date) {
        this.label = description;
        if (timestamp) {
            this.detail = `${debuggeeId} | ${timestamp.toISOString()}`;
        } else {
            this.detail = debuggeeId;
        }
    }
}

async function fetchDebuggees(db: Database): Promise<DebuggeeItem[]> {
    const debuggees: DebuggeeItem[] = [];

    const snapshot = await db.ref('/cdbg/debuggees').get();
    const savedDebuggees = snapshot.val();
    if (savedDebuggees) {
        for (const debuggeeId in savedDebuggees) {
            const timestamp = new Date(savedDebuggees[debuggeeId].lastUpdateTimeUnixMsec);
            const labels = savedDebuggees[debuggeeId].labels;
            debuggees.push(
                new DebuggeeItem(
                    debuggeeId,
                    `${labels.module || 'default'} - ${labels.version}`,
                    timestamp));
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
