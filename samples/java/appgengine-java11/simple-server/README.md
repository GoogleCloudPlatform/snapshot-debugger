# Using the Java Agent on a Simple One File Server App in Google App Engine Standard Java 11

NOTE: This example was copied from
[appengine-java11/custom-entrypoint](https://github.com/GoogleCloudPlatform/java-docs-samples/blob/main/appengine-java11/custom-entrypoint)
and modified for Snapshot Debugger Java agent use.


## Setup
See [Prerequisites](../README.md#Prerequisites).

## Compile the Source With Full Debug Information Enabled

```
javac -g Main.java
```

## Install the Snapshot Debugger Java Agent

```
mkdir cdbg
wget -qO- https://github.com/GoogleCloudPlatform/cloud-debug-java/releases/latest/download/cdbg_java_agent_gce.tar.gz | tar xvz -C cdbg
```

## Deploy to App Engine Standard

Examine the app.yaml file, which specifies the -agentpath java option to load
the agent. Deploy the app with the following:

```
gcloud app deploy
```

Make note of the following output entries, which should resemble the following:

```
[...snip]
target service:              [default]
target version:              [20221117t213436]
target url:                  [https://<your-project-id>.appspot.com]
[...snip]
```

The service and version will be used to identify your debuggee ID.

## Navigate To Your App

This will ensure the app is run, which will allow the agent to register itself with the Firebase backend.

## Determine the Debuggee ID

Based on the service and version you'll be able to identify your debuggee ID
based on the output from the `list_debuggees` command.

```
snapshot-dbg-cli list_debuggees
```

The output will resemble the following. The first column will contain an entry
`<service> - <version>`, which in this case is `default - 20221117t213436`.

```
Name                         ID             Description
---------------------------  -------------  ---------------------------------------------
default - 20221117t213436    d-de80f15f     my-project-20221117t213436-447943866161740510
```

The debuggee ID in this case is  `d-de80f15f`. Using this ID you may now run
through an [Example workflow](../../../../README.md#example-workflow).
