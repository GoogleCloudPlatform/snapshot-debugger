# Java Snapshot Debugger Agent

This section contains information for integrating and configuring the Java
Snapshot Debugger agent in different environments. Full configuration
information for the agent can be found at [Java Agent Documentation][java-agent]

## Samples

See [samples/java][java-samples] for working examples of installing and
configuring the Java agent across different Google Cloud environments.

[java-agent]: https://github.com/GoogleCloudPlatform/cloud-debug-java/blob/main/README.md
[java-samples]: https://github.com/GoogleCloudPlatform/snapshot-debugger/tree/main/samples/java

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
