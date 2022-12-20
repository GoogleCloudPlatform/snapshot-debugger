# Snapshot Debugger Example for Node.js on Google Compute Engine

NOTE: This sample application was copied from
[nodejs-getting-started/gce][sample-source]
and modified for the Snapshot Debugger samples here.

This folder contains the sample code for the [Deploying to Google Compute
Engine][tutorial-gce]
tutorial. Please refer to the tutorial for instructions on configuring,
running, and deploying this sample.

## Enabling Snapshot Debugger

The following code changes have been made to enable the Snapshot Debugger:

https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/d055bb60c04356ad64695c8853cbfdc59ebe2fdc/samples/node-js/gce/app.js#L17-L24

https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/d99f0ba821a94203440ba6213378843e172ce214/samples/node-js/gce/package.json#L18-L21

## Create and configure a Compute Engine instance

Note that the Snapshot Debugger requires the following access scopes:
* https://www.googleapis.com/auth/userinfo.email grants your cluster access to
your email address.  It is provided below in userinfo-email.
* https://www.googleapis.com/auth/firebase.database grants your cluster access to
the Firebase database.

```
gcloud compute instances create my-app-instance \
  --image-family=debian-10 \
  --image-project=debian-cloud \
  --machine-type=g1-small \
  --scopes userinfo-email,cloud-platform,https://www.googleapis.com/auth/firebase.database \
  --metadata-from-file startup-script=startup-script.sh \
  --zone us-central1-a \
  --tags http-server
```

## Determine the Debuggee ID

Based on the service and version you'll be able to identify your debuggee ID
based on the output from the `list_debuggees` command.

```
snapshot-dbg-cli list_debuggees
```

The output will resemble the following. The first column will contain an entry
`sample-service - version-1`, which was set in app.js.

```
Name                       ID         Description
-------------------------- ---------- ------------------------------------------------
sample-service - version-1 d-ad4829f7 node app.js module:sample-service version:version-1
```

The debuggee ID in this case is  `d-ad4829f7`. Using this ID you may now run
through an [Example workflow](../../../README.md#example-workflow).

E.g.
*    Use the `set_snapshot` CLI command to set a snapshot at `app.js:31`.
     Note the returned breakpoint ID.
*    Navigate to your application using the ip address shown in the
     `gcloud compute instances list` output. This will trigger the breakpoint
     and collect the snapshot.
     *   Note: You may need to set up a firewall to be able to access the
         webserver.  Follow the [getting started on gce][tutorial-gce]
         instructions to learn how to set it up.
*    Use the `get_snapshot` CLI command to retrieve the snapshot
     using the breakpoint ID created with the `set_snapshot` command.

## Clean up

```
gcloud compute instances delete my-app-instance \
  --zone=us-central1-a \
  --delete-disks=all
```

[tutorial-gce]: https://cloud.google.com/nodejs/tutorials/getting-started-on-compute-engine
[sample-source]: https://github.com/GoogleCloudPlatform/nodejs-getting-started/tree/main/gce
