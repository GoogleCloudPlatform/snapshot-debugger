# Snapshot Debugger Example for Python on Google Compute Engine

NOTE: This sample application was copied from
[getting-started-python/gce][sample-source]
and modified for the Snapshot Debugger samples here.

This folder contains the sample code for the [Getting started with Python on
Compute Engine][tutorial-gce]
tutorial. Please refer to the tutorial for instructions on configuring,
running, and deploying this sample.

## Enabling Snapshot Debugger

The following code changes have been made to enable the Snapshot Debugger:

https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/8d8d03a5e1c90ba7817eddadb09ab5f247d45e0f/samples/python/gce/main.py#L18-25

https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/8d8d03a5e1c90ba7817eddadb09ab5f247d45e0f/samples/python/gce/requirements.txt#L4

## Setup

Run through the steps listed in
[GCE Prerequisites](../../gce_samples_prerequisites.md).

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
`gce-python-sample - v1`, which was set in main.py.

```
Name                   ID         Description
---------------------- ---------- ----------------------------------
gce-python-sample - v1 d-ad4829f7 my-project-id-gce-python-sample-v1
```

The debuggee ID in this case is  `d-ad4829f7`. Using this ID you may now run
through an [Example workflow](../../../README.md#example-workflow).

E.g.
*    Use the `set_snapshot` CLI command to set a snapshot at `main.py:30`.
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

[tutorial-gce]: https://cloud.google.com/python/docs/getting-started/getting-started-on-compute-engine
[sample-source]: https://github.com/GoogleCloudPlatform/getting-started-python/tree/main/gce
