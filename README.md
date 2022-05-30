# Snapshot Debugger

The Snapshot Debugger  lets you inspect the state of a running cloud
application, at any code location, without stopping or slowing it down. It’s not
your traditional process debugger but rather an always on, whole app debugger
taking snapshots from any instance of the app.

You can use the Snapshot Debugger with any deployment of your application,
including test, development, and production. The debugger typically adds less
than 10ms to the request latency only when the application state is captured. In
most cases, this isn’t noticeable by users.


## Preview Limitations

During the preview phase, only [GCE](https://cloud.google.com/compute), and
local debugging are supported. Snapshot Debugger only works with the
[Node.js](https://github.com/googleapis/cloud-debug-nodejs) agent for preview.


### Upcoming Features

* Java agent support
* Python 3 agent support
* App Engine support for Java, Python 3, and Node.js

Note:

*  All upcoming features will be implemented before the
   [Cloud Debugger shutdown](https://cloud.google.com/debugger/docs/deprecations)
*  Python 2.7 will not be supported


## Support Period

Snapshot Debugger and associated agents will be supported until Aug 31, 2023,
after which they will be archived and frozen. No bug fixes or security patches
will be made after the freeze date. The repository can be forked by users if
they wish to maintain it going forward.

## CLI Command Reference

See
[COMMAND_REFERENCE.md](https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/main/cli/src/COMMAND_REFERENCE.md).

## Download the Snapshot Debugger CLI

Clone the debugger to your local environment, or to your Cloud Shell
$HOME directory. See [Using Cloud
Shell](https://cloud.google.com/shell/docs/using-cloud-shell) for information on
using Cloud Shell.

Note: When using the Snapshot Debugger in Cloud Shell you will be asked to
Authorize using your account credentials.

1. Clone the Snapshot Debugger CLI
```
git clone https://github.com/GoogleCloudPlatform/snapshot-debugger.git
```

## Before you begin

### Ensure you have the proper permissions

To complete the setup you’ll need to have the following permissions in your
Google Cloud project. If you are an `Owner` or `Editor` of the Google Cloud
project, then you have these permissions.

*   firebase.projects.create
*   firebase.projects.update,
*   firebasedatabase.instances.create
*   firebasedatabase.instances.get
*   resourcemanager.projects.get
*   serviceusage.services.enable
*   serviceusage.services.get

For more information on permissions and roles in Google projects, read
[Understanding
roles](https://cloud.google.com/iam/docs/understanding-roles#firebase-roles)


### Using Snapshot Debugger in Cloud Shell

Snapshot Debugger requires Python 3.6 or above and the `gcloud` CLI. If you are
working in Cloud Shell, you already have Python and `gcloud` installed.

In addition, the environment should already configured correctly by default. You
can verify this by running the following commands:

1. `gcloud config get-value project`
2. `gcloud config get-value account`

> **NOTE**: When running the cli, you may encounter a popup warning you that
`gcloud is requesting your credentials to make a GCP API call`. You'll  need to
click `AUTHORIZE` to proceed.


### Using Snapshot Debugger outside of Cloud Shell

#### Ensure you have Python 3.6 or above installed

The Snapshot Debugger CLI requires [Python](https://www.python.org/downloads/)
3.6 or newer.

#### Install Google Cloud `gcloud` CLI

The Snapshot Debugger CLI depends on the `gcloud` CLI. To install the `gcloud`
CLI, follow these [instructions](https://cloud.google.com/sdk/docs/install). If
you already have the `gcloud` CLI installed, run `gcloud components update` to
update all of your installed components to the latest version.

#### Set up the environment

1. Run `gcloud auth login`, be sure to use the account that has permissions on
   the Google Cloud project you are working on.
2. Run `gcloud config set project PROJECT_ID`. Where PROJECT_ID is the project
   you want to use. The Snapshot Debugger CLI always acts on the current
   `gcloud` configured project.

## Enable Firebase for your Google Cloud Project

The Snapshot Debugger CLI and agents use a Firebase Realtime Database (RTDB) to
communicate.

If you already use Firebase in your project, skip to the [Set up the Firebase
RTDB](#set-up-the-firebase-rtdb) section.

1. Add Firebase to your project:

   https://console.firebase.google.com/?dlAction=MigrateCloudProject&cloudProjectNumber=PROJECT_ID

   Where PROJECT_ID is your project ID

2. Select your
   [Project ID](https://cloud.google.com/resource-manager/docs/creating-managing-projects#identifying_projects)
    and click **Continue**. If you have billing enabled in your project, the
    pay-as-you-go Blaze plan is selected, otherwise the free Spark plan is
    selected. If you have billing enabled and want to use the free Spark plan,
    set up a new project without billing enabled.

   Note: The Snapshot Debugger uses the Firebase RTDB service. Most users' usage
   will be low enough to remain under the [free usage
   limits](https://firebase.google.com/pricing?).

3. If you are using the pay-as-you-go Blaze plan, click **Confirm plan**. You
   are not prompted to confirm if you are on the free Spark plan.

4. Read the information under **A Few things to remember when adding Firebase to
   a Google Cloud project** then click **Continue**.

5. Toggle the **enable analytics** option to enable or disable Google Analytics
   for Firebase. Google Analytics isn't required for Debugger use.

6. Click **Continue**.

7. Click **Get Started**.

8. Click on your project.

### Set up the Firebase RTDB

The instructions are slightly different depending on whether you are on the
Spark or Blaze billing plan. Follow the steps in the following section for the
plan you have.

You can check what billing plan is in effect for your project on the Firebase Usage & Billing page:

https://console.firebase.google.com/project/PROJECT_ID/usage/details

Where PROJECT_ID is your project ID

#### Blaze plan RTDB setup

This will instruct the debugger CLI to create and use a database with the name
`PROJECT_ID-cdbg`

1. Run `python3 cli/src/cli.py init` in the cloned `snapshot-debugger`
   directory.
2. The output resembles the following:

```
Project 'test-proj' is successfully configured with the Firebase Realtime
Database for use by Snapshot Debugger.

The full database information is below. If you have specified a custom database
ID the url below is the one you'll need to specify when using the other cli
commands.

  name:         projects/23498723497/locations/us-central1/instances/test-proj-cdbg
  project:      projects/23498723497
  database url: https://test-proj-cdbg.firebaseio.com
  type:         USER_DATABASE
  state:        ACTIVE
```

Note: The information printed by the `init` command can be accessed from within
your Firebase project. It’s safe to run the `python3 cli/src/cli.py init`
command multiple times to view this information.

#### Spark plan RTDB setup

This will instruct the CLI to create and use a database with the name
`PROJECT_ID-default-rtdb`. It will only be created if it does not currently
exist.

1. Run `python3 cli/src/cli.py init --use-default-rtdb`
2. The output resembles the following:

```
Project 'test-proj' is successfully configured with the Firebase Realtime
Database for use by Snapshot Debugger.

The full database information is below. If you have specified a custom database
ID the url below is the one you'll need to specify when using the other cli
commands.

  name:         projects/23498723497/locations/us-central1/instances/default
  project:      projects/23498723497
  database url: https://test-proj-default-rtdb.firebaseio.com
  type:         USER_DATABASE
  state:        ACTIVE
```

Note: The information printed by the `init` command can be accessed from within
your Firebase project. It’s safe to run the `python3 cli/src/cli.py init
--use-default-rtdb` command multiple times to view this information.

## Set up Snapshot Debugger in your Google Cloud project

To use the preview Snapshot Debugger, it’s necessary to set a flag to use the
Firebase backend.

If you don’t have a project yet and want to try out Snapshot Debugger, follow
the steps in [Getting started with Node.js on Compute Engine | Google
Cloud](https://cloud.google.com/nodejs/getting-started/getting-started-on-compute-engine)
to create one.

### Set up Google Compute Engine

1. Create your Compute Engine instance with the following access scopes:
    *   https://www.googleapis.com/auth/userinfo.email grants your cluster access to your email address.
    *   https://www.googleapis.com/auth/firebase.database grants your cluster access to the Firebase database.

    See the [Firebase information on scopes for Realtime Database and
    Authentication](https://firebase.google.com/docs/admin/setup#set-scopes-for-realtime-database-auth)
    page for more information on access scopes. To note, the `userinfo.email`
    scope is not included when specifying `full access to google apis` when
    creating a GCE instance, and will need to be added.

2. Use [npm](https://www.npmjs.com/) to install the package:

    ```
    npm install --save @google-cloud/debug-agent
    ```

3. Enable the agent at the top of your app's main script or entry point (but
   after `@google/cloud-trace` if you are also using it):

    ```
    require('@google-cloud/debug-agent').start({
      useFirebase: true,
      serviceContext: {
        service: 'SERVICE',
        version: 'VERSION',
      }
    });
    ```

    Where:
    *    `SERVICE` is a name for your app, such as MyApp, Backend, or Frontend.
    *    `VERSION` is a version, such as v1.0, build_147, or v20170714.

    We recommend setting these from environment variables so you don’t need to
    change the source code with each deployment.

The debugger is now ready for use with your app.

### Local and elsewhere

1. Use [npm](https://www.npmjs.com/) to install the package:

    ```
    npm install --save @google-cloud/debug-agent
    ```

2. Download service account credentials from Firebase.
    1. Navigate to your project in the Firebase console service account page.
       Replace `PROJECT_ID` with your project’s ID.

    ```
    https://console.firebase.google.com/project/PROJECT_ID/settings/serviceaccounts/adminsdk
    ```

    2. Click **Generate new private key** and save the key locally.

3. Configure and enable the agent at the top of your app's main script or entry
   point (but after @google/cloud-trace if you are also using it).

    ```
    require('@google-cloud/debug-agent').start({
      useFirebase: true,
      firebaseKeyPath: 'PATH-TO-KEY-FILE',
      // Specify this if you are the Spark billing plan and are using the
      // default RTDB instance.
      // firebaseDbUrl: 'https://RTDB-NAME-default-rtdb.firebaseio.com',
      serviceContext: {
        service: 'SERVICE',
        version: 'VERSION',
      }
    });
    ```

    Where:
    *   `PATH-TO-KEY-FILE` is the path to your Firebase private key.
    *   `RTDB-NAME` is the name of your Firebase database.
    *   `SERVICE` is a name for your app, such as `MyApp`, `Backend`, or `Frontend`.
    *   `VERSION` is a version, such as `v1.0`, `build_147`, or `v20170714`.

## Example workflow

You create a breakpoint (snapshot or logpoint) on debuggees. Debuggees represent
instances of the running application. In general all instances of the same
version of the application will have the same debuggee ID, and breakpoints set
on a debuggee will be installed on all running instances of it.

The following workflow commands are run in the cloned `snapshot-debugger`
directory unless otherwise specified.

### List Debuggees

1. Navigate to the cloned `snapshot-debugger` directory
2. Run the following command

```
python3 cli/src/cli.py list_debuggees
```

The output resembles the following:

```
Name           ID                                Description
-------------  --------------------------------  ----------------------------------------
test-app - v1  4a1d08461c8e10cc010b606353389d3e  node index.js module:test-app version:v1
test-app - v2  2054916c4b46c04e04fffa32781bbd2f  node index.js module:test-app version:v2
```

### Set Snapshots

Snapshots capture local variables and the call stack at a specific line location
in your app's source code. You can specify certain conditions and locations to
return a snapshot of your app's data, and view it in detail to debug your app.

1. Navigate to the cloned `snapshot-debugger` directory
2. Set snapshots with the following command:

```
python3 cli/src/cli.py set_snapshot index.js:21 --debuggee-id 2054916c4b46c04e04fffa32781bbd2f
```

Where:
*   `index.js:21` is the `file:line` for the snapshot
*   2054916c4b46c04e04fffa32781bbd2f is the debuggee ID


#### Snapshot conditions (optional)

A snapshot condition is a simple expression in the app's language that must
evaluate to true for the snapshot to be taken. Snapshot conditions are evaluated
each time the line is executed, by any instance, until the condition evaluates
to true or the snapshot times out.

Use of snapshot conditions is optional.

The condition is a full boolean expression that can include logical operators.
Conditions are specified using the `--condition` flag of the `set_snapshots`
command.

Example:
```
python3 cli/src/cli.py set_snapshot index.js:26 --debuggee-id 2054916c4b46c04e04fffa32781bbd2f --condition="ultimateAnswer <= 42 && foo==bar"
```

You can use the following language features to express conditions:

##### Node.js

Most Javascript expressions are supported, with the following caveat:

Expressions that may have static side effects are disallowed. The debug agent
ensures all conditions and watchpoints you add are read-only and have no side
effects, however, it doesn’t catch expressions that have dynamic side-effects.

For example, `o.f` looks like a property access, but dynamically, it may end up
calling a getter function. The debugger presently doesn't detect such
dynamic-side effects.


#### Snapshot expressions (optional)

Snapshot Debugger's Expressions feature allows you to evaluate complex
expressions or traverse object hierarchies when a snapshot is taken. Expressions
support the same language features as snapshot conditions.

Use of expressions is optional.

Typical uses for expressions are:

* To view static or global variables that are not part of the local variable
  set.
* To easily view deeply nested member variables.
* To avoid repetitive mathematical calculations. For example, calculating a
  duration in seconds with `(endTimeMillis - startTimeMillis) / 1000.0`.

Expressions are specified using the --expression flag of the set_snapshots
command.

Example:
```
python3 cli/src/cli.py set_snapshot index.js:26 --debuggee-id 2054916c4b46c04e04fffa32781bbd2f --expression="histogram.length"
```


### List snapshots

1. Navigate to the cloned `snapshot-debugger` directory
2. List snapshots with the following command:

```
python3 cli/src/cli.py list_snapshots --debuggee-id 2054916c4b46c04e04fffa32781bbd2f --include-inactive
```

Where:
*   2054916c4b46c04e04fffa32781bbd2f is the debuggee ID

The output resembles the following:

```
Status     Location     Condition    CompletedTime                ID
---------  -----------  -----------  ---------------------------  ------------
ACTIVE     index.js:21                                            b-1648008775
ACTIVE     index.js:21                                            b-1648044994
ACTIVE     index.js:21                                            b-1648045010
COMPLETED  index.js:21               2022-03-23T02:52:23.558000Z  b-1648003845
```

### Get snapshot

1. Navigate to the cloned `snapshot-debugger` directory
2. Get a snapshot with the following command:

```
python3 cli/src/cli.py get_snapshot b-1649947203 --debuggee-id 2054916c4b46c04e04fffa32781bbd2f
```

Where:
*   `b-1649947203` is the snapshot ID
*   2054916c4b46c04e04fffa32781bbd2f is the debuggee ID

The output resembles the following:

```
--------------------------------------------------------------------------------
| Summary
--------------------------------------------------------------------------------

Location:    index.js:30
Condition:   No condition set.
Expressions: No expressions set.
Status:      Complete
Create Time: 2022-05-13T14:14:01.444000Z
Final Time:  2022-05-13T14:14:02.516000Z

-------------------------------------------------------------------------------
| Evaluated Expressions
--------------------------------------------------------------------------------

There were no expressions specified.

--------------------------------------------------------------------------------
| Local Variables For Stack Frame Index 0:
--------------------------------------------------------------------------------

[
  {
    "req (IncomingMessage) ": {
      "_readableState (ReadableState) ": {
        "objectMode": "false",
        "highWaterMark": "16384",
        "buffer (BufferList) ": {
          "head": null,
          "tail": null,
          "length": "0"
        },
[... snip]

--------------------------------------------------------------------------------
| CallStack:
--------------------------------------------------------------------------------

Function              Location
--------------------  -----------
(anonymous function)  index.js:30
```

### Delete snapshots

1. Navigate to the cloned `snapshot-debugger` directory
2. Delete snapshots with the following command:

```
python3 cli/src/cli.py delete_snapshots --debuggee-id 2054916c4b46c04e04fffa32781bbd2f --include-inactive
```

Where:
*   2054916c4b46c04e04fffa32781bbd2f is the debuggee ID

The output resembles the following:

```
This command will delete the following snapshots:

Status     Location     Condition    ID
---------  -----------  -----------  ------------
ACTIVE     index.js:28               b-1649959801
ACTIVE     index.js:27               b-1649959807
COMPLETED  index.js:19               b-1649702213
COMPLETED  index.js:22               b-1649702753


Do you want to continue (Y/n)? Y
Deleted 4 snapshots.
```

## Troubleshooting

If you run into problems with Snapshot Debugger, file an
[issue](https://github.com/GoogleCloudPlatform/snapshot-debugger/issues).

### Your project doesn’t show up when enabling Firebase

#### Symptom

Your project id is not auto populated and is not present in the project dropdown
when you try to [Enable Firebase for your GCP
Project](#enable-firebase-for-your-google-cloud-project).

#### Resolution

Check if the Firebase Management API is already enabled, as if it is, that
interferes with the process. Try using the following link to disable the
Firebase Management API, then go back and follow the steps in the [Enable
Firebase for your GCP Project](#enable-firebase-for-your-google-cloud-project).

```
https://console.developers.google.com/apis/api/firebase.googleapis.com?project=PROJECT_ID
```

Where PROJECT_ID is your project ID.

### Your database in not displayed in the Firebase Console

#### Symptom

A blank screen is shown when attempting to view database contents in Firebase
Console's Realtime Database section. The project is using the Blaze pricing
plan.

#### Resolution

Rerun the init command to find the database's url. Use that url to view the
database's contents. See [Blaze plan RTDB setup](#blaze-plan-rtdb-setup) for
details, as noted there, it is safe to run the `init` command multiple times to
view your database's information.

The database's url should resemble `https://DATABASE_NAME.firebaseio.com`,
which should redirect to
`https://console.firebase.google.com/project/PROJECT_ID/database/DATABASE_NAME/data`
for the Firebase Console view.
