import * as vscode from 'vscode';

import { exec } from 'child_process';
import { Credential, GoogleOAuthAccessToken } from 'firebase-admin/app';
import { debugLog } from './debugUtil';

const NO_TOKEN_MESSAGE = 'Could not fetch access token from gcloud.  Are you logged in?';

export class GcloudCredential implements Credential {
    public initialized = false;
    private showingModal = false;

    async getAccessToken(): Promise<GoogleOAuthAccessToken> {
        return new Promise((resolve, reject) => {
            exec('gcloud auth print-access-token', (err, stdout, stderr) => {
                if (stderr) {
                    debugLog(stderr);
                }
                if (err) {
                    reject(err);
                }
                if (!stdout.trim()) {
                    // Only show the dialog if we've previously been connected and are not already showing the error.
                    if (this.initialized && !this.showingModal) {
                        this.showingModal = true;
                        vscode.window.showErrorMessage(NO_TOKEN_MESSAGE, {"modal": true}).then(() => this.showingModal = false);
                    }
                    reject(new Error(NO_TOKEN_MESSAGE));
                }
                resolve({
                    access_token: stdout.trim(),
                    expires_in: 3600
                });
            });
        });
    }

    async getProjectId(): Promise<string> {
        return new Promise((resolve, reject) => {
            exec('gcloud config get-value project', (err, stdout, stderr) => {
                if (stderr) {
                    debugLog(stderr);
                }
                if (err) {
                    reject(err);
                }
                if (!stdout.trim()) {
                    reject(new Error('Unable to fetch project id'));
                }
                resolve(stdout.trim());
            });
        });
    }

    async getAccount(): Promise<string> {
        return new Promise((resolve, reject) => {
            exec('gcloud config get-value account', (err, stdout, stderr) => {
                if (stderr) {
                    debugLog(stderr);
                }
                if (err) {
                    reject(err);
                }
                if (!stdout.trim()) {
                    reject(new Error('Unable to fetch account'));
                }
                resolve(stdout.trim());
            });
        });
    }
}