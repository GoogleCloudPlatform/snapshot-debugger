# Appengine Helloworld sample for Google App Engine Flexible

> **Note**
> This example was copied from
> [flexible/helloworld](https://github.com/GoogleCloudPlatform/java-docs-samples/tree/main/flexible/helloworld)
> and modified for Snapshot Debugger Java agent use.

## Setup

See [Prerequisites](../README.md#Prerequisites).

Ensure your current working directory is
`samples/java/appengine-flexible/helloworld`, as all following instructions
assumes this.

## Examine app.yaml and Dockerfile

This example customizes the Java 8 / Jetty 9 runtime by explicitly providing a
Dockerfile. The purpose of the Dockerfile is to add the Snapshot Debugger Java
agent to the runtime.

src/main/appengine/app.yaml:

https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/ef597d47dadff1921dbf5a00a459d72acf1886c3/samples/java/appengine-flexible/helloworld/src/main/appengine/app.yaml#L15-L40

src/main/docker/Dockerfile:

https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/0868fe074c9504c9c226c93baa4fa9249afc8c68/samples/java/appengine-flexible/helloworld/src/main/docker/Dockerfile#L1-L15

## Deploy to App Engine Flexible

Deploy the app with the following:

```
mvn clean package appengine:deploy
```

Early on in the output, log lines resembling the following will be emitted, make
note of them:

```
[INFO] GCLOUD: target service:              [default]
[INFO] GCLOUD: target version:              [20221125t154414]
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
`<service> - <version>`, which in this case is `default - 20221125t154414`.

```
Name                       ID          Description
-------------------------- ----------  ------------------------------------------------
default - 20221125t154414  d-85ad2c65  my-project-id-20221125t154414-448123750866017122
```

The debuggee ID in this case is  `d-85ad2c65`. Using this ID you may now run
through an [Example workflow](../../../../README.md#example-workflow).

E.g.
*    Use the `set_snapshot` CLI command to set a snapshot at
     `HelloServlet.java:34`. Note the returned breakpoint ID.
*    Navigate to your application using the `target url` shown in the `mvn clean
     package appengine:deploy` output. This will trigger the breakpoint and
     collect the snapshot.
*    Use the `get_snapshot` CLI command to retrieve the snapshot using the
     breakpoint ID created with the `set_snapshot` command.
