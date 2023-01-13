# Snapshot Debugger Examples for Python in the App Engine standard environment

NOTE: This sample application was copied from
[python-docs-samples/appengine/hello-world/standard][sample-source]
and modified for the Snapshot Debugger samples here.


This is the hello-world application for the
[Google App Engine Python standard environment](https://cloud.google.com/appengine/docs/standard/python3).
More complete documentation about getting started in App Engine can be found in
[this tutorial](https://cloud.google.com/appengine/docs/standard/python3/building-app).

* [Setup](#setup)
* [Deploying to App Engine](#deploying-to-app-engine)

## Setup

Before you can run or deploy the sample, you need to do the following:

1.  Perform all [Prerequisite Steps](../../app_engine_standard_prerequisties.md)
1.  Refer to the [getting started documentation][create-cloud-project]
    for instructions on setting up your Cloud project.

## Deploying to App Engine

The following code changes have been made to enable the Snapshot Debugger:

https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/33f8756c5adb7684650adbe0d81ebbc6f5051c4c/samples/python/appengine-standard/requirements.txt#L2

https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/33f8756c5adb7684650adbe0d81ebbc6f5051c4c/samples/python/appengine-standard/main.py#L17-L21

Then deploy to App Engine as usual:

    gcloud app deploy


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
`<service> - <version>`, which in this case is `default - 20221122t161333`.

```
Name                       ID          Description                    Last Active           Status
-------------------------  ----------  -----------------------------  --------------------  ------
default - 20221122t161333  d-ad4829f7  my-project-id-20221122t161333  2022-11-22T16:15:00Z  ACTIVE
```

The debuggee ID in this case is  `d-ad4829f7`. Using this ID you may now run
through an [Example workflow](../../../README.md#example-workflow).

E.g.
*    Use the `set_snapshot` CLI command to set a snapshot at `main.py:32`.
     Note the returned breakpoint ID.
*    Navigate to your application using the `target url` shown in the
     `gcloud app deploy` output. This will trigger the breakpoint and
     collect the snapshot.
*    Use the `get_snapshot` CLI command to retrieve the snapshot using the
     breakpoint ID created with the `set_snapshot` command.

[sample-source]: https://github.com/GoogleCloudPlatform/python-docs-samples/tree/main/appengine/standard_python3/hello_world
[create-cloud-project]: https://cloud.google.com/appengine/docs/standard/python3/building-app/creating-gcp-project
