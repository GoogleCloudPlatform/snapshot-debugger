# Snapshot Debugger Example for Node.js on Google Compute Engine

NOTE: This sample application was copied from
[nodejs-getting-started/gce][sample-source]
and modified for the Snapshot Debugger samples here.

This folder contains the sample code for the [Deploying to Google Compute
Engine][tutorial-gce]
tutorial. Please refer to the tutorial for instructions on configuring,
running, and deploying this sample.

## Enabling Snapshot Debugger

The following customizations have been made to enable the Snapshot Debugger:

Extra scopes are require, see [Create and configure a Compute Engine instance](https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/samples-java-gce/samples/java/gce/README.md#create-and-configure-a-compute-engine-instance)
https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/a6ab2b094c4e3b522aea2c61f3c4abbe87f2e211/samples/java/gce/README.md?plain=1#L30

The webapp is extracted to `${jetty.base}/webapps/root`:
https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/a6ab2b094c4e3b522aea2c61f3c4abbe87f2e211/samples/java/gce/startup-script.sh#L52-L72

Install and configure the Snapshot Debugger Java Agent:
https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/a6ab2b094c4e3b522aea2c61f3c4abbe87f2e211/samples/java/gce/startup-script.sh#L88-L90
https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/a6ab2b094c4e3b522aea2c61f3c4abbe87f2e211/samples/java/gce/startup-script.sh#L84

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

It will take some time for your instance to become available.  You can check
the progress of the instance creation:

```
gcloud compute instances get-serial-port-output my-app-instance --zone us-central1-a
```

NOTE: The application code is being downloaded to the GCE instance from the main
branch of the snapshot-debugger Github repository.  If you make local changes to
the application, they will not be present in the GCE instance unless you also
alter `startup-script.sh` to download your version of the code.

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
     `gcloud compute instances list` output on port 8080. Alternatively,
     ssh to the instance and `curl localhost:8080`. Either approach will trigger
     the breakpoint and collect the snapshot.
     *   Note: You may need to set up a firewall to be able to access the
         webserver through the external ip address.  Follow the
         [getting started on gce][tutorial-gce] instructions to learn how to
         set it up.
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
