# Required Project Configuration for Snapshot Debugger

The project level configuration described here is to enable the Snapshot
Debugger agent to communicate with the Firebase RTDB backend.

## Access Scopes

The following access scopes are required and need to be manually configured if
you are running in **GCE or GKE** (in environments such as App Engine they will
already be present):
*   https://www.googleapis.com/auth/userinfo.email grants your cluster access to your email address.
*   https://www.googleapis.com/auth/firebase.database grants your cluster access to the Firebase database.

See the [Firebase information on scopes for Realtime Database and
Authentication][firebase-scopes] page for more information on access scopes.

As a special note, when using the Cloud Console to create a GCE instance, the
`userinfo.email` scope is not included when specifying `full access to google
apis`, and will need to be added afterwards. When using the `gcloud cli`, it's
possible to specify the scopes at creation time, see [here][scopes-example] for
an example.


## Service Account Permissions

The service account responsible for running your application needs to have the
the `roles/firebasedatabase.admin`

### Determine your service account's email address

By default the following holds:

* GCE, and any Google Cloud service that uses GCE (such as GKE) will use the
  `Compute Engine default service account`
* App Engine, and any Google Cloud service that uses App Engine will use the
  `App Engine default service account`

It's also possible to manually configure a different service account for your
service.  If that is the case for you, use that service account.

#### If you have not yet created your service

Run

```
gcloud iam service-accounts list
```

From the output select the email address of the service account you intend to
use. If you plan on using the default service account, use the appropriate
default service account.

#### If your service already exists

As a starting point you can run:

```
gcloud iam service-accounts list
```

This will provide the list of service accounts. However it's possible to go a
step further and determine which service account is actually in use.

* **App Engine**

    1. Substitute the appropriate values into the link and visit
    https://pantheon.corp.google.com/appengine/versions?serviceId=[SERVICE_NAME]&project=[PROJECT_ID].

    2. Look at the `Service Account` column.

* **GCE**

    Run:

    ```
    gcloud compute instances describe [INSTANCE_NAME] --format="value(serviceAccounts.email)"
    ```

* **GKE**

    Run:

    ```
    gcloud container clusters describe cluster-1 --zone us-central1-c  --flatten="nodePools[].config.serviceAccount"
    ```

    If the value is `default`, this means the `Compute Engine default service
    account`. Its email address can be determined by running and finding the
    email address in the row with name `Default compute service account`.

    ```
    gcloud iam service-accounts list
    ```

### Set the permission

Run

```
gcloud projects add-iam-policy-binding [PROJECT_ID] \
    --member=serviceAccount:[SERVICE_ACCOUNT_EMAIL] \
    --role=roles/firebasedatabase.admin
```

### List permissions

To list the permissions a given service account has, run the following:

```
gcloud projects get-iam-policy [PROJECT_ID] \
    --flatten="bindings[].members" \
    --filter="bindings.members:[SERVICE_ACCOUNT_EMAIL]" \
    --format="value(bindings.role)"
```

[firebase-scopes]: https://firebase.google.com/docs/admin/setup#set-scopes-for-realtime-database-auth
[scopes-example]: https://github.com/GoogleCloudPlatform/snapshot-debugger/tree/main/samples/java/gce#create-and-configure-a-compute-engine-instance
