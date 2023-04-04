import { Database } from 'firebase-admin/database';
import * as vscode from 'vscode';
import { debugLog } from './debugUtil';

const NO_DEBUGGEES = 'No debuggees found';
const NO_DEBUGGEES_DETAIL = 'Please check your configuration';

class DebuggeeItem implements vscode.QuickPickItem {
    label: string;
    detail: string;
    kind?: vscode.QuickPickItemKind | undefined;

    constructor(public debuggeeId: string, description: string, public timestamp: Date) {
        if (this.debuggeeId === NO_DEBUGGEES) {
            this.label = NO_DEBUGGEES;
            this.detail = NO_DEBUGGEES_DETAIL;
        } else {
            this.label = description;
            this.detail = `${debuggeeId} | ${duractionToLastActiveString(new Date().getTime() - timestamp.getTime())}`;
        }
    }
}

function duractionToLastActiveString(d: number) {
    const seconds = d / 1000;
    const minutes = seconds / 60;

    if (minutes < 60) {
        return 'Recently active';
    }

    return `Last seen ${durationToFriendlyString(d)} ago`;
}

function durationToFriendlyString(d: number) {
    const seconds = d / 1000;
    const minutes = seconds / 60;
    const hours = minutes / 60;
    const days = hours / 24;

    if (seconds == 1) {
        return 'a second';
    } else if (seconds < 45) {
        return `${Math.round(seconds)} seconds`;
    } else if (seconds < 90) {
        return 'a minute';
    } else if (minutes < 45) {
        return `${Math.round(minutes)} minutes`;
    } else if (minutes < 90) {
        return 'an hour';
    } else if (hours < 24) {
        return `${Math.round(hours)} hours`;
    } else if (hours < 42) {
        return 'a day';
    } else if (days < 30) {
        return `${Math.round(days)} days`;
    } else if (days < 45) {
        return 'a month';
    } else {
        return `${Math.round(days / 30)} months`;
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
        debuggees.sort((a: DebuggeeItem, b: DebuggeeItem) => b.timestamp.getTime() - a.timestamp.getTime());
    } else {
        const noDebuggees = new DebuggeeItem(NO_DEBUGGEES, "", new Date());
        noDebuggees.debuggeeId = "";
        debuggees.push();
    }
    return debuggees;
}

export async function pickDebuggeeId(db: Database): Promise<string | undefined> {
    const selection = await vscode.window.showQuickPick(fetchDebuggees(db), {'title': 'Select Debuggee'});
    if (selection) {
        debugLog(`Selected Debuggee: ${selection.debuggeeId}`);
        return selection.debuggeeId;
    } else {
        return undefined;
    }
}
