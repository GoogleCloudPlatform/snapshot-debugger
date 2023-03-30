import { exec } from 'child_process';
import { Credential, GoogleOAuthAccessToken } from 'firebase-admin/app';

export class GcloudCredential implements Credential {
    async getAccessToken(): Promise<GoogleOAuthAccessToken> {
        return new Promise((resolve, reject) => {
            exec('gcloud auth print-access-token', (err, stdout, stderr) => {
                if (stderr) {
                    console.log(stderr);
                }
                if (err) {
                    reject(err);
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
                    console.log(stderr);
                }
                if (err) {
                    reject(err);
                }
                resolve(stdout.trim());
            });
        });
    }

    async getAccount(): Promise<string> {
        return new Promise((resolve, reject) => {
            exec('gcloud config get-value account', (err, stdout, stderr) => {
                if (stderr) {
                    console.log(stderr);
                }
                if (err) {
                    reject(err);
                }
                resolve(stdout.trim());
            });
        });
    }
}