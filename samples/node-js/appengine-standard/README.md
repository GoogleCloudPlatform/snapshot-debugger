# Snapshot Debugger Examples for Node.js in the App Engine standard environment

NOTE: This file was copied from
[nodejs-docs-samples/appengine/hello-world/standard/README.md](https://github.com/GoogleCloudPlatform/nodejs-docs-samples/blob/main/appengine/hello-world/standard/README.md)
and modified for the Snapshot Debugger samples here.


This is the sample application for the
[Quickstart for Node.js in the App Engine standard environment][tutorial]
tutorial found in the [Google App Engine Node.js standard environment][appengine]
documentation.

* [Setup](#setup)
* [Deploying to App Engine](#deploying-to-app-engine)

## Setup

Before you can run or deploy the sample, you need to do the following:

1.  Refer to the [../../README.md](snapshot debugger readme) file for instructions on
    setting up the snapshot debugger.
1.  Refer to the
    [https://github.com/GoogleCloudPlatform/nodejs-docs-samples/blob/main/appengine/README.md](appengine readme)
    file for instructions on running and deploying.
1.  Install dependencies:

        npm install

## Deploying to App Engine

The following code changes have been made to enable the Snapshot Debugger:

https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/c7cc477b9a66541f9b6804f0b6ba215547901afc/samples/node-js/appengine-standard/package.json#L18-21

https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/c7cc477b9a66541f9b6804f0b6ba215547901afc/samples/node-js/appengine-standard/app.js#L17-L20

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

TODO: Not true.  Maybe set the version?  Right now it's completely missing.

The output will resemble the following. The first column will contain an entry
`<service> - <version>`, which in this case is `default - 20221117t213436`.

```
Name                       ID         Description
-------------------------- ---------- ------------------------------------------------
default - 20221122t161333  d-ad4829f7 my-project-id-20221122t161333-448054658875855015
```

The debuggee ID in this case is  `d-ad4829f7`. Using this ID you may now run
through an [Example workflow](../../../../README.md#example-workflow).

E.g.
*    Use the `set_snapshot` CLI command to set a snapshot at `app.js:28`.
     Note the returned breakpoint ID.
*    Navigate to your application using the `target url` shown in the
     `gcloud app deploy` output. This will trigger the breakpoint and
     collect the snapshot.
*    Use the `get_snapshot` CLI command to retrieve the snapshot using the
     breakpoint ID created with the `set_snapshot` command.
