import * as vscode from 'vscode';

/**
 * We use a custom when clause context for tracking when the Snapshot Debugger
 * extension is actually active. The adapter will enable it when it receives an
 * attach request, and then disable it when it receives a disonnect request.
 * This is then available for use in when clauses in the package.json file. One
 * use is for controlling when the icons are displayed in the debug toolbar.
 * Without this the Snapshot Debugger icons would be visible in the debug
 * toolbar for any debugger in use. With this we can ensure it is only visible
 * when the Snapshot Debugger extension is actively being used.
 *
 * https://code.visualstudio.com/api/references/when-clause-contexts#add-a-custom-when-clause-context
 */
export class IsActiveWhenClauseContext {
  public static CONTEXT_NAME: string = 'extension.snapshotdbg.isActive';

  private static setContext(value: boolean): void {
    vscode.commands.executeCommand('setContext', IsActiveWhenClauseContext.CONTEXT_NAME, value);
  }

  public static create(): void {
    IsActiveWhenClauseContext.setContext(false);
  }

  public static enable(): void {
    IsActiveWhenClauseContext.setContext(true);
  }

  public static disable(): void {
    IsActiveWhenClauseContext.setContext(false);
  }
}
