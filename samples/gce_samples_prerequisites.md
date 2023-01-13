# Prerequisite Steps For The GCE Samples

## Project Setup

Follow all steps in [Project Prerequites](common_samples_prerequisites.md)

## Enable Compute Engine API

The Compute Engine API (compute.googleapis.com) must be enabled.

1. Check if it's already enabled.

    ```
    gcloud  services list --enabled | grep compute.googleapis.com
    ```

    If the entry was found, it is enabled. If not, proceed to step 2 to enable
    it.

2. Enable the API if it is not already renabled.

    ```
    gcloud  services enable compute.googleapis.com
    ```

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
    gcloud projects add-iam-policy-binding jcb-gce-fresh-test \
        --member=serviceAccount:[SERVICE ACCOUNT EMAIL ADDRESS] \
        --role=roles/firebasedatabase.admin
    ```
