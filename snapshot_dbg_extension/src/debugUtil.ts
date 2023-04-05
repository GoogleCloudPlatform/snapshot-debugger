
let debugLogEnabled = true;
export function setDebugLogEnabled(enabled: boolean): void {
    debugLogEnabled = enabled;
}

export function debugLog(message?: any, ...optionalParams: any[]): void {
    if (debugLogEnabled) {
        console.log(message, ...optionalParams);
    }
}
