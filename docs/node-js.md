# Node.js Snapshot Debugger Agent

This section contains information for integrating and configuring the Node.js
Snapshot Debugger agent in different environments. Full configuration
information for the agent can be found at [Node.js Agent
Documentation][nodejs-agent]

## Samples

See [samples/node-js][nodejs-samples] for working examples of installing and
configuring the Node.js agent across different Google Cloud environments.

[nodejs-agent]: https://github.com/googleapis/cloud-debug-nodejs/blob/main/README.md
[nodejs-samples]: https://github.com/GoogleCloudPlatform/snapshot-debugger/tree/main/samples/node-js

## Running locally

It's also possible to run things outside of a Google Cloud environment, such
as locally. Here are some notes for doing so, which involves generating a
service account key so the agents are able to read/write from the Firebase RTDB
backend.

### Download service account credentials from Firebase.

1. Navigate to your project in the Firebase console service account page.
   Replace `PROJECT_ID` with your project’s ID.

    ```
    https://console.firebase.google.com/project/PROJECT_ID/settings/serviceaccounts/adminsdk
    ```

2. Click **Generate new private key** and save the key locally.

### Install and configure the agent

1. Use [npm](https://www.npmjs.com/) to install the package:

    ```
    npm install --save @google-cloud/debug-agent
    ```

2. Configure and enable the agent at the top of your app's main script or entry
   point (but after @google/cloud-trace if you are also using it).

    ```
    require('@google-cloud/debug-agent').start({
      useFirebase: true,
      firebaseKeyPath: 'PATH-TO-KEY-FILE',
      // Specify this if you are the Spark billing plan and are using the
      // default RTDB instance.
      // firebaseDbUrl: 'https://RTDB-NAME-default-rtdb.firebaseio.com',
      serviceContext: {
        service: 'SERVICE',
        version: 'VERSION',
      }
    });
    ```

    Where:
    *   `PATH-TO-KEY-FILE` is the path to your Firebase private key.
    *   `RTDB-NAME` is the name of your Firebase database.
    *   `SERVICE` is a name for your app, such as `MyApp`, `Backend`, or `Frontend`.
    *   `VERSION` is a version, such as `v1.0`, `build_147`, or `v20170714`.

