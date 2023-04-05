import * as vscode from 'vscode';

export async function pickLogLevel(): Promise<string | undefined> {
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

    const selection = await vscode.window.showQuickPick(items, {'title': 'Select Log Level'});
    return selection?.label.split(' ')[0].trim();
}
