import * as vscode from 'vscode';

import { sleep } from "./util";

let gPickPending = false;

async function pickLogLevel(title: string): Promise<string | undefined> {
    /**
     * The lable field supports icons via the $(<name>)-syntax.
     * https://code.visualstudio.com/api/references/vscode-api#ThemeIcon
     *
     * A list of available icons can be found here:
     * https://code.visualstudio.com/api/references/icons-in-labels
     *
     * Here we're able to leverage the fact that icons with the names 'info',
     * 'warning' and 'error' exist and we can convert our log level to lowercase
     * to obtain a relevant icon.
     */
    const items: vscode.QuickPickItem[] =
        ['INFO', 'WARNING', 'ERROR'].map(level => (
            {'label': `${level} $(${level.toLowerCase()})`}
        ));

    // If we have one call to showQuickPick outstanding, any other calls to it
    // during this time will immediately return with a value of undefined.
    // During initialization time it's possible we'll be prompting the user
    // to select a log level for logpoints found in the IDE in multiple
    // different files. This can lead to this situation occurring, so here
    // we serialize the calls.
    while (gPickPending) {
        await (sleep(250));
    }

    gPickPending = true;
    const selection = await vscode.window.showQuickPick(items, {title});
    gPickPending = false;

    return selection?.label.split(' ')[0].trim();
}

export async function pickLogLevelNewlyCreated(): Promise<string | undefined> {
    return pickLogLevel('Select Log Level');
}

export async function pickLogLevelSyncedFromIDE(path: string, line: number): Promise<string | undefined> {
    return pickLogLevel(`Select Log Level For Logpoint: ${path}:${line}`);
}
