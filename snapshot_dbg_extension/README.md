# Snapshot Debugger Extension

The Snapshot Debugger extension allows you to use the Snapshot Debugger from within VSCode.

See the [Snapshot Debugger README][snapshot-debugger-readme]
for more information about the Snapshot Debugger product.

## Features

The Snapshot Debugger allows you to set a special sort of breakpoint on your running applications
that will capture snapshots of memory, or to emit logs when certain lines of code are run.
This extension allows you to do this from within VSCode.

1.  Attach to a debuggee that has registered itself with the Snapshot Debugger.

1.  Set a breakpoint within your code.  This will let the Snapshot Debugger know that you would like to capture a snapshot from your application when program execution next reaches that location.

1.  When the breakpoint is triggered, you can view the stacktrace and captured variables.

You can also:

*  Create conditional breakpoints
*  Set expressions to be evaluated when a snapshot is taken.
*  Create logpoints.  These will produce additional logs in your running applications; the logs will not show up in VSCode.
*  View snapshots from previous debugging sessions.

## Requirements

The Snapshot Debugger will only work if your application is already configured to work with it, is running, and has successfully registered itself.  See [this documentation][setting-up-in-application] for more details.

You will need `gcloud` to be installed, and to be logged in with an account that has "Firebase Database Admin" permissions or higher on your project.

## Configuration

The full set of configuration parameters can be found under the [configurationAttributes][configuration_attributes] node of the extension's [package.json][extension_package_json] file. Here we list a few of the more common ones that may need to be used:

* databaseUrl - URL to the Firebase Realtime Database to use.
* debuggeeId - ID of the debuggee to debug.

[configuration_attributes]: https://github.com/search?q=repo%3AGoogleCloudPlatform%2Fsnapshot-debugger+path%3Asnapshot_dbg_extension%2Fpackage.json+%22configurationAttributes%22&type=code
[extension_package_json]: https://github.com/GoogleCloudPlatform/snapshot-debugger/blob/main/snapshot_dbg_extension/package.json

## Quirks / Potential Improvements

* Attaching
  * `gcloud` is used to fetch user credentials and so must be installed and the user must be logged in.  Error messages are not precise if there are issues.
  * A debuggee id is required.  It can be provided in launch.json or selected at launch time.

* Breakpoint management.
  * The system attempts to synchronize breakpoints on the IDE and the server.
    * This is only done at attach time, when the IDE connects to the adapter.
      Any breakpoints added externally afterwards, (eg via the Snapshot Debugger
      CLI) will not be reflected in the IDE.
    * Breakpoints set in the UI prior to attaching will attempt to match against
      active breakpoints on the server. If there isn't a match, a new
      breakpoint will be created.
    * Active breakpoints on the server that did not get matched to a breakpoint
      in the IDE will get synced to the IDE.
    * Active breakpoints on the server that don't find a match already present
      in the IDE at sync time:
      * If it is a logpoint, it will not be synced. This is because the spec
        does not provide a way for the debug adapter to notify the IDE of a
        logpoint (that only works in the direction IDE -> Debug Adaper).
      * Breakpoints with a condition that get synced to the IDE will appear to
        not have a condition when viewed through the IDE. On the server the
        condition does exist and the agents will make use of it.  This is
        because the spec does not provide a way for the debug adapter to notify
        the IDE of a condition (that only works in the direction IDE -> Debug
        Adaper).
      * Only one breakpoint per line will be synced. In general the IDE (and
        hence the extension) only supports one breakpoint per line. When there
        are multiple active breakpoints on the server for the same line, the
        extension will choose one to be synced to the IDE.
        * The Snapshot Debugger extension does not support Inline Breakpoints (aka
          columns).

* Virtual threads.  The concept of snapshots is not present in vscode and the debug protocol, so threads
  are reported for each active breakpoint.
  * Threads for breakpoints with errors - it would be nice if the breakpoint was highlighted (eg. stack trace that includes path & line for problematic breakpoint)
  * Clicking on a breakpoint in the breakpoint list should result in the relevant "thread" being selected.
  * Note: if only one thread is reported, the thread name is not shown in the UI

* Files
  * Breakpoints that are created outside of vscode (eg. the CLI) may fail to display the correct source file in the UI when they are loaded.
    * To ensure they line up, when specifying the breakpoint via the cli, the
      relative path from the root of the vscode workspace to the file should be
      used. E.g. for file `/usr/local/src/project/com/app/App.java`, if the vscode
      workspace is rooted at `/usr/local/src/project`, then the CLI would need
      to create the breakpoint at `com/app/App.java`.
  * There is no current way to hint to users that the version of the file they are viewing is not the version of the file that they are debugging.
  * Stacktraces that include files in dependencies are reported as existing in the local workspace.  They are not, so result in error messages being displayed.

* Expressions
  * Requests for expressions by default when attaching and having breakpoints already set is a bit jarring.
  * Expressions can't be used for breakpoint matching because the SourceBreakpoint does not include expressions.

* Expected debugger functionality.  The Snapshot Debugger is not a typical debugger so does not support things like resuming, stepping through code, watch expressions, etc.
  * When a user attempts to use step-through functionality, an error is displayed to notify them that it is unsupported.
  * When a user attempts to resume a thread, it will remove the associated breakpoint from the UI.
  * Proposed improvement: Disable/hide/repurpose the watch expressions

## Known Issues

* Virtual threads
  * Deleting a breakpoint should result in its thread being removed.

* Inline breakpoints (specifying a column).
  * Columns are not supported, though at the moment the extension does not
    handle this gracefully.
  * Attempting to set multiple inline breakpoints on the same line will lead to
    confusion in the extension/IDE, since the extension only supports one
    breakpoint per line.


[snapshot-debugger-readme]: https://github.com/GoogleCloudPlatform/snapshot-debugger#readme
[setting-up-in-application]: https://github.com/GoogleCloudPlatform/snapshot-debugger#set-up-snapshot-debugger-in-your-google-cloud-project
