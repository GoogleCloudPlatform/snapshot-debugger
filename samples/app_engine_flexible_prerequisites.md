# Prerequisite Steps For The App Engine Flexible Samples

## Project Setup

Follow the instructions
[here](https://cloud.google.com/appengine/docs/flexible/managing-projects-apps-billing)
to create/confgure your App Engine enabled project.

## Install the Snapshot Debugger CLI and enable Firebase

Follow the instructions beginning at [Before you
begin](../README.md#before-you-begin) through to and including [Enable
Firebase for your Google Cloud
Project](../README.md#enable-firebase-for-your-google-cloud-project) to
get the Snapshot Debugger CLI installed and your project configured to use
Firebase.

## Configure Service Account Roles

The application running on App Engine will need to read/write from the Firebase
RTDB instance. For it to do that, the service account running the application
will need the `roles/firebasedatabase.admin` role. In addition, service accounts
running applications in the App Engine Flexible environment require the
`roles/storage.objectViewer` and `roles/appengineflex.serviceAgent` roles.

* **Determine the Service Account Email Address**

    Here it is assumed the default App Engine service account will be used. If
    you have provided special configuration to use a different service account,
    use the email address of that service account.

    ```
    gcloud iam service-accounts list
    ```

    Identify the email of the entry with a display name resembling `App Engine
    default service account`.

* **Add the roles**

    ```
    gcloud projects add-iam-policy-binding [YOUR PROJECT ID] \
        --member=serviceAccount:[SERVICE ACCOUNT EMAIL ADDRESS] \
        --role=roles/firebasedatabase.admin

    gcloud projects add-iam-policy-binding [YOUR PROJECT ID] \
        --member=serviceAccount:[SERVICE ACCOUNT EMAIL ADDRESS] \
        --role=roles/storage.objectViewer

    gcloud projects add-iam-policy-binding [YOUR PROJECT ID] \
        --member=serviceAccount:[SERVICE ACCOUNT EMAIL ADDRESS] \
        --role=roles/appengineflex.serviceAgent
    ```
