# Snapshot Debugger

The Snapshot Debugger  lets you inspect the state of a running cloud
application, at any code location, without stopping or slowing it down. It’s not
your traditional process debugger but rather an always on, whole app debugger
taking snapshots from any instance of the app.

You can use the Snapshot Debugger with any deployment of your application,
including test, development, and production. The debugger typically adds less
than 10ms to the request latency only when the application state is captured. In
most cases, this isn’t noticeable by users.


## Limitations

*  Python 2.7 will not be supported


## Support Period

Snapshot Debugger and associated agents will be supported until Aug 31, 2023,
after which they will be archived and frozen. No bug fixes or security patches
will be made after the freeze date. The repository can be forked by users if
they wish to maintain it going forward.

### What happens after Aug 31

After Aug 31, 2023, Snapshot Debugger CLI and agents remain functional. Users
can fork the repository to add features.

This OSS solution is being provided as an alternative to Cloud Debugger that
users can use beyond the end of the support period. The purpose of the support
period is to assist users with issues or questions they have around
transitioning from Cloud Debugger to Snapshot Debugger.


## CLI Command Reference

See
[COMMAND_REFERENCE.md](https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/main/snapshot_dbg_cli/COMMAND_REFERENCE.md).

## Installing the Snapshot Debugger CLI

Install the debugger CLI in your local environment, or in your Cloud Shell
$HOME directory. See [Using Cloud
Shell](https://cloud.google.com/shell/docs/using-cloud-shell) for information on
using Cloud Shell.

```
python3 -m pip install snapshot-dbg-cli
```

> **Note**: When using the Snapshot Debugger in Cloud Shell you will be asked to
Authorize using your account credentials.


## Running the Snapshot Debugger CLI

There are two options to run the CLI once the pip install has been completed.

### Option 1: Use the installed script

As part of the pip install process, a script, `snapshot-dbg-cli` will be
installed which can be used to run the CLI.

Example running the `list_debuggees` command:

```
snapshot-dbg-cli list_debuggees
```

> **NOTE**: To run the script this way from any directory, you must ensure the
script's install directory is in your PATH. Pip should emit a warning if the
install location is not in the PATH, and also provide the install location in
this case, so that you can add it to your PATH.

### Option 2: Run the package directly

Example running the `list_debuggees` command:

```
python3 -m snapshot_dbg_cli list_debuggees
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

1. Run `snapshot-dbg-cli init`.
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
your Firebase project. It’s safe to run the `snapshot-dbg-cli init` command
multiple times to view this information.

#### Spark plan RTDB setup

This will instruct the CLI to create and use a database with the name
`PROJECT_ID-default-rtdb`. It will only be created if it does not currently
exist.

1. Run `snapshot-dbg-cli init --use-default-rtdb`
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
your Firebase project. It’s safe to run the `snapshot-dbg-cli init
--use-default-rtdb` command multiple times to view this information.

#### Setting up Firebase RTDB in other regions

By default, `snapshot-dbg-cli init` will create a Firebase Realtime Database in
`us-central1`.  It is possible to create and use a database in any region
supported by Firebase Realtime Database.  See
[supported RTDB locations][rtdb_locations].

Setting up your database in a non-default region comes with some trade-offs:
*  As a positive, you get to control where your snapshot data will be stored.
   This may be important for compliance reasons.
*  As a negative, the vsCode extension and agents will be unable to
   automatically find the database.  The database URL will need to be provided
   explicitly via configuration, see the following for details:
   * [Configuring the Java Agent][java_agent_config]
   * [Configuring the Python Agent][python_agent_config]
   * [Configuring the Node.js Agent][nodejs_agent_config]

You can set up your database in a non-default location as follows:
```
snapshot-dbg-cli init --location={YOUR_LOCATION}
```

For example, you may want to set up your database in Belgium, and so would run
```snapshot-dbg-cli init --location=europe-west1```

Make note of the database URL provided in the command output; you will need to
provide this to your debug agent(s) and the vsCode plugin.

[rtdb_locations]: https://firebase.google.com/docs/projects/locations#rtdb-locations
[java_agent_config]: https://github.com/GoogleCloudPlatform/cloud-debug-java#snapshot-debugger---firebase-realtime-database-backend
[python_agent_config]: https://github.com/GoogleCloudPlatform/cloud-debug-python/blob/main/README.md#snapshot-debugger---firebase-realtime-database-backend
[nodejs_agent_config]: https://github.com/googleapis/cloud-debug-nodejs/blob/main/README.md#snapshot-debugger---firebase-realtime-database-backend


## Set up Snapshot Debugger in your Google Cloud project

### Working Samples

Working examples of using the Snapshot Debugger with Java, Python and Node.js
applications across different Google Cloud environments can be found in:

* [snapshot-debugger/samples][samples]

[samples]: https://github.com/GoogleCloudPlatform/snapshot-debugger/tree/main/samples
[notes-local]: https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/main/samples/README.md#notes-on-running-locally

### Agent Documentation

See the following for agent specific documentation:

* [Java](https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/main/docs/java.md)
* [Node.js](https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/main/docs/node-js.md)
* [Python](https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/main/docs/python.md)

## Example workflow

You create a breakpoint (snapshot or logpoint) on debuggees. Debuggees represent
instances of the running application. In general all instances of the same
version of the application will have the same debuggee ID, and breakpoints set
on a debuggee will be installed on all running instances of it.

### List Debuggees

Run the following command

```
snapshot-dbg-cli list_debuggees --include-inactive
```

The output resembles the following:

```
Name           ID          Description                              Last Active           Status
-------------  ----------  ---------------------------------------- --------------------  --------
test-app - v2  d-8dd7f149  node index.js module:test-app version:v2 2022-12-16T21:45:07Z  ACTIVE
test-app - v1  d-24abc4f1  node index.js module:test-app version:v1 2022-10-16T21:45:07Z  INACTIVE
```


### Set Snapshots

Snapshots capture local variables and the call stack at a specific line location
in your app's source code. You can specify certain conditions and locations to
return a snapshot of your app's data, and view it in detail to debug your app.

Set snapshots with the following command:

```
snapshot-dbg-cli set_snapshot index.js:21 --debuggee-id d-8dd7f149
```

Where:
*   `index.js:21` is the `file:line` for the snapshot
*   `d-8dd7f149` is the debuggee ID


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
snapshot-dbg-cli set_snapshot index.js:26 --debuggee-id d-8dd7f149 --condition="ultimateAnswer <= 42 && foo==bar"
```

You can use the following language features to express conditions:

##### Java

Most Java expressions are supported, including:

*   Local variables: `a == 8`.
*   Numerical and boolean operations: `x + y < 20`.
*   Instance and static fields: `this.counter == 20`, `this.myObj.isShutdown`,
    `myStatic`, or `com.mycompany.MyClass.staticMember`.
*   String comparisons with the equality operator: `myString == "abc"`.
*   Function calls. Only read-only functions can be used. For example,
    `StringBuilder.indexOf()` is supported, but `StringBuilder.append()` is not.
*   Type casting, with fully qualified types: `((com.myprod.ClassImpl)
    myInterface).internalField`

The following language features are *not* supported:

*   Unboxing of numeric types, such as `Integer`; use `myInteger.value` instead.


##### Python

Most Python expressions are supported, including:

*   Reading local and global variables.
*   Reading from arrays, lists, slices, dictionaries and objects.
*   Calling simple methods.

The following language features are not supported:

*   Calling functions that allocate new objects or use complex constructs.
*   Creating new objects inside the expression.

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
support the same language features as [snapshot conditions](#snapshot-conditions-optional), described above.

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
snapshot-dbg-cli set_snapshot index.js:26 --debuggee-id d-8dd7f149 --expression="histogram.length"
```


### List snapshots

List snapshots with the following command:

```
snapshot-dbg-cli list_snapshots --debuggee-id d-8dd7f149 --include-inactive
```

Where:
*   `d-8dd7f149` is the debuggee ID

The output resembles the following:

```
Status     Location     Condition    CompletedTime         ID
---------  -----------  -----------  --------------------  ------------
ACTIVE     index.js:21                                     b-1648008775
ACTIVE     index.js:21                                     b-1648044994
ACTIVE     index.js:21                                     b-1648045010
COMPLETED  index.js:21               2022-03-23T02:52:23Z  b-1648003845
```

### Get snapshot

Get a snapshot with the following command:

```
snapshot-dbg-cli get_snapshot b-1649947203 --debuggee-id d-8dd7f149
```

Where:
*   `b-1649947203` is the snapshot ID
*   `d-8dd7f149` is the debuggee ID

The output resembles the following:

```
--------------------------------------------------------------------------------
| Summary
--------------------------------------------------------------------------------

Location:    index.js:30
Condition:   No condition set.
Expressions: No expressions set.
Status:      Complete
Create Time: 2022-05-13T14:14:01Z
Final Time:  2022-05-13T14:14:02Z

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

### Set Logpoints

Adds a debug logpoint to a debug target (debuggee). Logpoints inject logging
into running services without changing your code or restarting your application.
Every time any instance executes code at the logpoint location, Snapshot
Debugger logs a message. Output is sent to the standard log for the programming
language of the target (java.logging for Java, logging for Python, etc.)

Logpoints remain active for 24 hours after creation, or until they are deleted
or the service is redeployed. If you place a logpoint on a line that receives
lots of traffic, Debugger throttles the logpoint to reduce its impact on your
application.

Set logpoints with the following command:

```
snapshot-dbg-cli set_logpoint index.js:21 "a={a} b={b}" --debuggee-id d-8dd7f149
```

Where:
*   `index.js:21` is the `file:line` for the logpoint
*   `a={a} b={b}` is the logpoint message format
*   `d-8dd7f149` is the debuggee ID

> **Note**: A common issue that users have run into is that logging at INFO
level is often suppressed by the default logger and so logpoints will appear to
be broken. See the `--log-level` option for setting a higher priority log level.

#### Logpoint message format

The format string is the message which will be logged every time the logpoint
location is executed. If the string contains curly braces ('{' and '}'), any
text within the curly braces will be interpreted as a run-time expression in the
debug target's language, which will be evaluated when the logpoint is hit. Some
valid examples are {a}, {myObj.myFunc()} or {a + b}.  The value of the
expression will then replace the {} expression in the resulting log output. For
example, if you specify the format string "a={a}, (b+1)={b+1}", and the logpoint
is hit when local variable a is 1 and b is 3, the resulting log output would be
"a=1, (b+1)=3".

For more detailed information on valid expressions see [Snapshot
expressions](#snapshot-expressions-optional) as the rules are the same for
logpoint expressions.

#### Logpoint conditions (optional)

A logpoint condition is a simple expression in the application language that
must evaluate to true for the logpoint to be logged. Logpoint conditions are
evaluated each time the line is executed, by any instance, until the logpoint
expires or is deleted.

Use of logpoint conditions is optional.

For more detailed information on valid conditions see [Snapshot
conditions](#snapshot-conditions-optional) as the rules are the same for
logpoint conditions.


### List logpoints

List logpoints with the following command:

```
snapshot-dbg-cli list_logpoints --debuggee-id d-8dd7f149 --include-inactive
```

Where:
*   `d-8dd7f149` is the debuggee ID

The output resembles the following:

```
User Email    Location        Condition  Log Level  Log Message Format   ID            Status
------------  --------------  ---------  ---------  -------------------  ------------  -------------------------------------------
foo1@bar.com  Main.java:23               INFO      a={a} b={b}           b-1660681047  EXPIRED
foo2@bar.com  Main.java:25    a == 3     WARNING   Line hit              b-1660932877  EXPIRED
foo2@bar.com  Main.java:9999             INFO      Log msg               b-1661203071  SOURCE_LOCATION: No code found at line 9999
```


### Get logpoint

Get a logpoint with the following command:

```
snapshot-dbg-cli get_logpoint b-1660681047 --debuggee-id d-8dd7f149
```

Where:
*   `b-1660681047` is the logpoint ID
*   `d-8dd7f149` is the debuggee ID

The output resembles the following:

```
Logpoint ID:        b-1660681047
Log Message Format: a == 3
Location:           Main.java:23
Condition:          No condition set
Status:             EXPIRED
Create Time:        2022-08-19T18:14:38Z
Final Time:         2022-08-20T18:14:39Z
User Email:         foo1@bar.com
```

## Cleaning up

The following commands can be used to delete debuggees and breakpoints
(snapshots and logpoints).

### Delete Debuggees

Run the following command

```
snapshot-dbg-cli delete_debuggees
```

The output resembles the following:

```
This command will delete the following debuggees:

Name                       ID          Last Active           Status
-------------------------  ----------  --------------------  ------
default - 20221125t224954  d-39f7082e  2022-12-05T03:13:42Z  STALE
default - 20221125t154414  d-dba89292  2022-12-04T03:02:48Z  STALE



Do you want to continue (Y/n)?
Deleted 2 debuggees.
```

When deleting a debuggee, all breakpoints that belong to it are also deleted.

### Delete snapshots

Delete snapshots with the following command:

```
snapshot-dbg-cli delete_snapshots --debuggee-id d-8dd7f149 --include-inactive
```

Where:
*   `d-8dd7f149` is the debuggee ID

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


### Delete logpoints

Delete logpoints with the following command:

```
snapshot-dbg-cli delete_snapshots --debuggee-id d-8dd7f149 --include-inactive
```

Where:
*   `d-8dd7f149` is the debuggee ID

The output resembles the following:

```
This command will delete the following logpoints:

Location         Condition  Log Level  Log Message Format  ID
---------------  ---------  ---------  ------------------  ------------
Main.java:25     a == 3     WARNING    Line hit            b-1660927187
Main.java:9999              INFO       Log msg             b-1660927272



Do you want to continue (Y/n)?
Deleted 4 snapshots.
```


## VSCode Extension

There is a VSCode extension for the Snapshot Debugger.  You can use this
extension to set logpoints, set breakpoints and view snapshots in the comfort
of your IDE.  See the [extension's README][extension-readme] for more details.

You can install the extension by downloading it from the
[most recent release][extension-release], and then running
`code --install-extension snapshotdbg-*.vsix`.

Note that you will still need to use the Snapshot Debugger CLI to set up your
environment and to purge old data.  Gcloud needs to be installed for credential
management.

[extension-release]: https://github.com/GoogleCloudPlatform/snapshot-debugger/releases
[extension-readme]: https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/main/snapshot_dbg_extension/README.md

## Troubleshooting

See [Snapshot Debugger Troubleshooting][troubleshooting]

[troubleshooting]: https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/main/docs/troubleshooting.md

## Firebase DB Schema

See [Snapshot Debugger Firebase DB Schema][schema]

[schema]: https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/main/docs/SCHEMA.md
