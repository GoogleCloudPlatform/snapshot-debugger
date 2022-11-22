# Using the Java Agent on a Simple One File Server App in Google App Engine Standard Java 11

NOTE: This example was copied from
[appengine-java11/custom-entrypoint](https://github.com/GoogleCloudPlatform/java-docs-samples/blob/main/appengine-java11/custom-entrypoint)
and modified for Snapshot Debugger Java agent use.


## Setup
See [Prerequisites](../README.md#Prerequisites).

Ensure your current working directory is
`samples/java/appengine-java11/simple-server`, as all following instructions
assumes this.

## Compile the Source With Full Debug Information Enabled

The `-g` option here is what enables full debug information. Without it
information on method arguments and local variables would not be available. The
`-source` and `-target` options are to ensure it will run with the Java 11
runtime.

```
javac -source 11 -target 11 -g Main.java
```

## Install the Snapshot Debugger Java Agent

```
mkdir cdbg
wget -qO- https://github.com/GoogleCloudPlatform/cloud-debug-java/releases/latest/download/cdbg_java_agent_gce.tar.gz | tar xvz -C cdbg
```

## Deploy to App Engine Standard

Examine the app.yaml contents, which provides a custom entry point that
specifies the `-agentpath` java option to load the agent:

https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/ac5c05af60eb739330ca970f183ce52002df3c10/samples/java/appengine-java11/simple-server/app.yaml#L15-L17

Deploy the app with the following:

```
gcloud app deploy
```

Make note of the following output entries, which should resemble the following:

```
[...snip]
target service:              [sample-java11-simple-server]
target version:              [20221122t161333]
target url:                  [https://<your-project-id>.appspot.com]
[...snip]
```

The service and version will be used to identify your debuggee ID.

## Navigate To Your App

This will ensure the app is run and is required as your app will not be
debuggable until after the first request has been received.  The URL should be
provided in the `target url` output of the previous step.

## Determine the Debuggee ID

Based on the service and version you'll be able to identify your debuggee ID
based on the output from the `list_debuggees` command.

```
snapshot-dbg-cli list_debuggees
```

The output will resemble the following. The first column will contain an entry
`<service> - <version>`, which in this case is `default - 20221117t213436`.

```
Name                                           ID                                Description
---------------------------------------------  --------------------------------  ----------------------------------------------------------------------------------
sample-java11-simple-server - 20221122t161333  d-ad4829f7                        jcb-test-firebase-1-sample-java11-simple-server-20221122t161333-448054658875855015
```

The debuggee ID in this case is  `d-de80f15f`. Using this ID you may now run
through an [Example workflow](../../../../README.md#example-workflow).

E.g.
*    Use the `set_snapshot` CLI command to set a snapshot at `Main.java:33`. Note
     the returned breakpoint ID.
*    Navigate to your application using the `target url` shown in the `gcloud
     app deploy` output. This will trigger the breakpoint and collect the snapshot.
*    Use the `get_snapshot` CLI command to retrieve the snapshot using the
     breakpoint ID created with the `set_snapshot` command.
