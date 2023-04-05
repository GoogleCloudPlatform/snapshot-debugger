import { Database, DataSnapshot } from 'firebase-admin/database';
import { CdbgBreakpoint } from './breakpoint';
import * as vscode from 'vscode';
import { debugLog } from './debugUtil';

class SnapshotItem implements vscode.QuickPickItem {
    label: string;
    description: string | undefined;
    kind?: vscode.QuickPickItemKind | undefined;

    constructor(public cdbgBreakpoint: CdbgBreakpoint | undefined) {
        if (cdbgBreakpoint) {
            this.label = cdbgBreakpoint.id;
            this.description = ` ${cdbgBreakpoint.shortPath}:${cdbgBreakpoint.line}   ${cdbgBreakpoint.finalTime}`
        } else {
            this.label = "No snapshots found";
        }
    }
}

async function fetchSnapshots(db: Database, debuggeeId: string): Promise<SnapshotItem[]> {
    const snapshotItems: SnapshotItem[] = [];

    const snapshots: DataSnapshot= await db.ref(`cdbg/breakpoints/${debuggeeId}/final`).get();
    snapshots.forEach((breakpoint): void => {
        const cdbgBreakpoint: CdbgBreakpoint = CdbgBreakpoint.fromSnapshot(breakpoint);
        if (cdbgBreakpoint.isSnapshot()) {
            snapshotItems.push(new SnapshotItem(cdbgBreakpoint));
        }
    });
    return snapshotItems;
}

export async function pickSnapshot(db: Database, debuggeeId: string): Promise<CdbgBreakpoint | undefined> {
    const selection = await vscode.window.showQuickPick(fetchSnapshots(db, debuggeeId), {'title': 'Select Previously Captured Snapshot'});
    if (selection?.cdbgBreakpoint) {
        debugLog(`Selected Snapshot: ${selection.cdbgBreakpoint.id}`);
        return selection.cdbgBreakpoint;
    } else {
        return undefined;
    }
}
