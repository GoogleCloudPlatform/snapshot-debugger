# Prerequisite Steps For The GCE Samples

## Create a Project in the Google Cloud Platform Console

If you haven't already created a project, create one now. Projects enable you to
manage all Google Cloud Platform resources for your app, including deployment,
access control, billing, and services.

1. Open the [Cloud Platform Console][cloud-console].
1. In the drop-down menu at the top, select **Create a project**.
1. Give your project a name.
1. Make a note of the project ID, which might be different from the project
   name. The project ID is used in commands and in configurations.

## Enable Compute Engine API

The Compute Engine API (compute.googleapis.com) must be enabled.

1. Check if it's already enabled.

    ```
    gcloud services list --enabled | grep compute.googleapis.com
    ```

    If the entry was found, it is enabled. If not, proceed to step 2 to enable
    it.

2. Enable the API if it is not already renabled.

    ```
    gcloud services enable compute.googleapis.com
    ```

## Install the Snapshot Debugger CLI and enable Firebase

Follow the instructions beginning at [Before you
begin](../README.md#before-you-begin) through to and including [Enable
Firebase for your Google Cloud
Project](../README.md#enable-firebase-for-your-google-cloud-project) to
get the Snapshot Debugger CLI installed and your project configured to use
Firebase.

## Configure Service Account Role

The application running on GCE will need to read/write from the Firebase RTDB
instance. For it to do that, the service account running the GCE instance will
need the `roles/firebasedatabase.admin` role.

* **Determine the Service Account Email Address**

    Here it is assumed the default GCE service account will be used when the
    instance gets created.

    ```
    gcloud iam service-accounts list
    ```

    Identify the email of the entry with a display name resembling `Compute
    Engine default service account`.

* **Add the role**

    ```
    gcloud projects add-iam-policy-binding [YOUR PROJECT ID] \
        --member=serviceAccount:[SERVICE ACCOUNT EMAIL ADDRESS] \
        --role=roles/firebasedatabase.admin
    ```
