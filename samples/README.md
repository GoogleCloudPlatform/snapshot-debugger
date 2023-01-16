# Snapshot Debugger Samples

This directory contains working examples of using the Snapshot Debugger with
Java, Python and Node.js applications across different Google Cloud
environments.

The accompanying README files in the subdirectories contain the relevant
information for each sample. For more information on the Snapshot Debugger and
the agents see the following:

* [Snapshot Debugger](https://github.com/GoogleCloudPlatform/snapshot-debugger)
* [Java Agent](https://github.com/GoogleCloudPlatform/cloud-debug-java)
* [NodeJS Agent](https://github.com/googleapis/cloud-debug-nodejs)
* [Python Agent](https://github.com/GoogleCloudPlatform/cloud-debug-python)


## Notes on running locally

It's also possible to run things outside of a Google Cloud environment, such
as locally. Here are some notes for doing so, which involves generating a
service account key so the agents are able to read/write from the Firebase RTDB
backend.

**Download service account credentials from Firebase.**

1. Navigate to your project in the Firebase console service account page.
   Replace `PROJECT_ID` with your project’s ID.

    ```
    https://console.firebase.google.com/project/PROJECT_ID/settings/serviceaccounts/adminsdk
    ```

2. Click **Generate new private key** and save the key locally.

**Language specific instructions:**

### Java

1. Download the pre-built agent package:

    ```
    # Create a directory for the Debugger. Add and unzip the agent in the directory.
    sudo sh -c "mkdir /opt/cdbg && wget -qO- https://github.com/GoogleCloudPlatform/cloud-debug-java/releases/latest/download/cdbg_java_agent_gce.tar.gz | tar xvz -C /opt/cdbg"
    ```

2. Add the agent to your Java invocation:

    _(If you are using Tomcat or Jetty, see the [Application
    Servers](https://github.com/GoogleCloudPlatform/cloud-debug-java#application-servers)
    section of the agent documentation for extra information.)_

    ```
    # Start the agent when the app is deployed.
    java -agentpath:/opt/cdbg/cdbg_java_agent.so \
        -Dcom.google.cdbg.module=MODULE \
        -Dcom.google.cdbg.version=VERSION \
        -Dcom.google.cdbg.agent.use_firebase=True \
        -Dcom.google.cdbg.auth.serviceaccount.jsonfile=PATH-TO-KEY-FILE
        -jar PATH_TO_JAR_FILE
    ```

    Where:
    *    `MODULE` is a name for your app, such as MyApp, Backend, or Frontend.
    *    `VERSION` is a version, such as v1.0, build_147, or v20170714.
    *    `PATH-TO-KEY-FILE` is the path to your Firebase private key.
    *    `PATH_TO_JAR_FILE` is the relative path to the app's JAR file. e.g.,: ~/myapp.jar.

### Python

1. Download the Debugger agent.

    The easiest way to install the Python Debugger is with
    [pip](https://pypi.org/project/pip/)

    ```
    pip install google-python-cloud-debugger
    ```

2. Add the following lines as early as possible in your initialization code, such as in your main function, or in manage.py when using the Django web framework.

    ```
    try:
      import googleclouddebugger
      googleclouddebugger.enable(
        use_firebase=True,
        module='[MODULE]',
        version='[VERSION]',
        service_account_json_file='[PATH-TO-KEY-FILE]'
      )
    except ImportError:
      pass
    ```

    Where:
    *    `MODULE` is a name for your app, such as MyApp, Backend, or Frontend.
    *    `VERSION` is a version, such as v1.0, build_147, or v20170714.
    *    `PATH-TO-KEY-FILE` is the path to your Firebase private key.



### Node.js

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

