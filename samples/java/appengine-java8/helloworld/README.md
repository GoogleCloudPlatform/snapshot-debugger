# Using the Java Agent on a Hello World Servlet on GAE Standard with Java 11

> **Note**
> This example was copied from
[appengine-java8/helloworld](https://github.com/GoogleCloudPlatform/java-docs-samples/blob/main/appengine-java8/helloworld) and modified for Snapshot Debugger Java agent use.

This example will use the App Engine Plugin to first build and stage the
application. It will make some custom changes to the staging directory to add
files before deploying it.

## Setup

See [Prerequisites](../README.md#Prerequisites).

Ensure your current working directory is
`samples/java/appengine-java8/helloworld`, as all following instructions
assumes this.

## Package your app:

First use the maven App Engine Plugin to build and stage the application.

```
mvn clean package appengine:stage
```

## Add the Snapshot Debugger Java Agent

Per [App Engine Staging
Directory](../README.md#app-engine-staging-directory-and-the-snapshot-debugger-java-agent)
we add in the Snapshot Debugger Java Agent.

```
mkdir target/appengine-staging/cdbg
wget -qO- https://github.com/GoogleCloudPlatform/cloud-debug-java/releases/latest/download/cdbg_java_agent_gae_java8.tar.gz | tar xvz -C target/appengine-staging/cdbg
```

## Deploy the application

Examine the `appengine-web.xml` contents, which provides the
`GAE_AGENTPATH_OPTS` environment variable. This is a space separated list of
`agentpath` config entries of agents to load. Each entry begins with the
relative path in the user's deployment to the agent .so file.

TODO: Add permalink

This will deploy the contents of `target/appengine-staging`, with the contents
of the added cdbg directory unchanged:

```
gcloud app deploy target/appengine-staging/app.yaml
```

Make note of the following output entries, which should resemble the following:

```
[...snip]
target service:              [default]
target version:              [20221122t182924]
target url:                  [https://<custom for your project>.appspot.com]
[...snip]
```

The service and version will be used to identify your debuggee ID.

## Navigate To Your App

This will ensure the app is run and is required as your app will not be
debuggable until after the first request has been received. The base URL should
be provided in the `target url` output of the previous step.

Visit: https://custom-for-your-project.appspot.com/hello

## Determine the Debuggee ID

Based on the service and version you'll be able to identify your debuggee ID
based on the output from the `list_debuggees` command.

```
snapshot-dbg-cli list_debuggees
```

The output will resemble the following. The first column will contain an entry
`<service> - <version>`, which in this case is `default - 20221122t182924`.

```
Name                       ID          Description                                       Last Active           Status
-------------------------  ----------  ------------------------------------------------  --------------------  ------
default - 20221122t182924  d-7f891f30  my-project-id-20221122t182924-448056845967981019  2022-11-22T18:30:00Z  ACTIVE
```

The debuggee ID in this case is  `d-7f891f30`. Using this ID you may now run
through an [Example workflow](../../../../README.md#example-workflow).

E.g.
*    Use the `set_snapshot` CLI command to set a snapshot at
     `HelloAppEngine.java:37`. Note the returned breakpoint ID.
*    Navigate to your application at `<target url>/hello` using the `target url`
     shown in the `gcloud app deploy` output. This will trigger the breakpoint
     and collect the snapshot.
*    Use the `get_snapshot` CLI command to retrieve the snapshot using the
     breakpoint ID created with the `set_snapshot` command.
