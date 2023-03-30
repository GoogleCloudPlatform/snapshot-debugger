import * as vscode from 'vscode';
import { DebugProtocol } from '@vscode/debugprotocol';

/**
 * Returns a promise that will resolve in ms milliseconds.
 * @param ms 
 * @returns 
 */
export function sleep(ms: number) {
    return new Promise((resolve) => { setTimeout(resolve, ms) });
}

/**
 * Waits ms milliseconds for the promise to resolve, or rejects with a timeout.
 * @param ms
 * @param promise
 * @returns Promise wrapped in a timeout.
 */
export function withTimeout(ms: number, promise: Promise<any>) {
    const timeout = new Promise((_, reject) =>
      setTimeout(() => reject(`Timed out after ${ms} ms.`), ms)
    );
    return Promise.race([promise, timeout]);
};

// TODO: Plumb this through from outside this file if possible.
// FIXME: Use a path library instead of this nonsense.
function pwd() {
    if (vscode.workspace.workspaceFolders !== undefined) {
        return vscode.workspace.workspaceFolders[0].uri.fsPath + '/';
    } else {
        return '';
    }
}

export function stripPwd(path: string): string {
    const prefix = pwd();
    if (path.startsWith(prefix)) {
        return path.substring(prefix.length);
    }
    return path;
}

export function addPwd(path: string): string {
    const prefix = pwd();
    return `${prefix}${path}`;
}

export function sourceBreakpointToString(bp: DebugProtocol.SourceBreakpoint): string {
    return `${bp.line}\0${bp.condition}\0${bp.logMessage}`;
}

export function stringToSourceBreakpoint(bp: string): DebugProtocol.SourceBreakpoint {
    const parts = bp.split('\0');
    return {
        line: parseInt(parts[0]),
        ...(parts[1] !== 'undefined' && {condition: parts[1]}),
        ...(parts[2] !== 'undefined' && {logMessage: parts[2]})
    };
}

