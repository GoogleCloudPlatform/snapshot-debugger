# Spring Boot based Hello World app

> **Note**
> This example was copied from
> [flexible/helloworld-springboot](https://github.com/GoogleCloudPlatform/java-docs-samples/tree/main/flexible/helloworld-springboot)
> and modified for Snapshot Debugger Java agent use.


## Setup

See [Prerequisites](../README.md#Prerequisites).

Ensure your current working directory is
`samples/java/appengine-flexible/helloworld-springboot`, as all following instructions
assumes this.

## Examine the `app.yaml` and `Dockerfile` files

This example customizes the Java 8 / Jetty 9 runtime by explicitly providing a
Dockerfile. The purpose of the Dockerfile is to add the Snapshot Debugger Java
agent to the runtime. The app.yaml file provides configuration information to
specify a custom runtime is being used and to configure the loading of the
agent.

app.yaml:

https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/ed767fe00d5b1006ff60ac9c4bf57668b774962f/samples/java/appengine-flexible/helloworld-springboot/src/main/appengine/app.yaml#L15-L34

Dockerfile:

https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/ed767fe00d5b1006ff60ac9c4bf57668b774962f/samples/java/appengine-flexible/helloworld-springboot/src/main/docker/Dockerfile#L1-L15

## Deploy to App Engine Flexible

Deploy the app with the following:

```
mvn clean package appengine:deploy
```

Early on in the output, log lines resembling the following will be emitted, make
note of them:

```
[INFO] GCLOUD: target service:              [default]
[INFO] GCLOUD: target version:              [20221125t224954]
[INFO] GCLOUD: target url:                  [https://PROJECT_ID.REGION_ID.r.appspot.com]
```

The service and version will be used to identify your debuggee ID.

## Navigate To Your App

This will ensure the app is running correctly. The URL should be provided in the
`target url` output of the previous step.

## Determine the Debuggee ID

Based on the service and version you'll be able to identify your debuggee ID
based on the output from the `list_debuggees` command.

```
snapshot-dbg-cli list_debuggees
```

The output will resemble the following. The first column will contain an entry
`<service> - <version>`, which in this case is `default - 20221125t224954`.

```
Name                       ID         Description                                       Last Active                  Status
-------------------------  ---------- ------------------------------------------------  ---------------------------  ------
default - 20221125t224954  d-62259477 my-project-id-20221125t224954-448130606220701265  2022-11-25T22:50:00.812000Z  ACTIVE
```

The debuggee ID in this case is  `d-62259477`. Using this ID you may now run
through an [Example workflow](../../../../README.md#example-workflow).

E.g.
*    Use the `set_snapshot` CLI command to set a snapshot at
     `HelloController.java:26`. Note the returned breakpoint ID.
*    Navigate to your application using the `target url` shown in the `mvn clean
     package appengine:deploy` output. This will trigger the breakpoint and
     collect the snapshot.
*    Use the `get_snapshot` CLI command to retrieve the snapshot using the
     breakpoint ID created with the `set_snapshot` command.
