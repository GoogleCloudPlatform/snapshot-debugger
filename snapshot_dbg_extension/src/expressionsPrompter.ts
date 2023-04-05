import * as vscode from 'vscode';

export async function promptUserForExpressions(): Promise<string[]|undefined> {
    let expressions: string[] = [];

    while (true) {
        const title = (expressions.length == 0) ?
            "Add an Expression to the Breakpoint" : "Add Another Expression to the Breakpoint";

        const prompt = (expressions.length == 0) ?
            "Press 'Escape' or enter an empty line if you do not wish to add an expression." :
            "Press 'Escape' or enter an empty line if you do not wish to add any more expressions.";

        let expression = await vscode.window.showInputBox({title, prompt});

        expression = expression?.trim();

        if (!expression) {
            break;
        }

        expressions.push(expression);
    };

    return expressions.length ? expressions : undefined;
}
