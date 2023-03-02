# Snapshot Debugger Extension

The Snapshot Debugger extension allows you to use the Snapshot Debugger from within VSCode.

See the [Snapshot Debugger README][snapshot-debugger-readme]
for more information about the Snapshot Debugger product.

## Features

The Snapshot Debugger allows you to set a special sort of breakpoint on your running applications
that will capture snapshots of memory.  This extension allows you to do this from within VSCode.

1.  Attach to a debuggee that has registered itself with the Snapshot Debugger.

    TODO: Screenshot

1.  Set a breakpoint within your code.  This will let the Snapshot Debugger know that you would like to capture a snapshot from your application when program execution next reaches that location.

    TODO: Screenshot

1.  When the breakpoint is triggered, you can view the stacktrace and captured variables.

    TODO: Screenshot

You can also:

*  TODO: Delete breakpoints
*  TODO: Create conditional breakpoints
*  TODO: Create logpoints.  These will produce additional logs in your running applications; the logs will not show up in VSCode.
*  TODO: View snapshots from previous debugging sessions.

## Requirements

The Snapshot Debugger will only work if your application is already configured to work with it, is running, and has successfully registered itself.  See [this documentation][setting-up-in-application] for more details.

You will need a service account with the proper credentials to access the Snapshot Debugger.
*  TODO: See if this can be avoided.

## Extension Settings

* None

## Known Issues

* Attaching
  * A service account file is required.  It would be better if we could use user credentials instead.
  * No testing/fallback logic is present for database urls.
  * A debuggee id is required.  It can be provided in launch.json or selected at launch time.

* Breakpoint management. The system attempts to synchronize breakpoints on the IDE and the backend.
  * Breakpoints remain "active" locally when a snapshot is taken.  This results in inconsistent state and the breakpoints may be set on the backend again.
  * Finalized breakpoints on the backend are ignored.  Highly related to the previous point.
  * Matching local and backend breakpoints is done through path and line number.  This needs to be improved.  There may be a way to link breakpoints by id.  Explore this possibility.
  * There should be a way to view "final" breakpoints, either for management or for viewing snapshots.
  * The extension may grab the snapshot from the database before the agent finished persisting it.  The current fix is a sleep; there should be a retry loop instead.

* Virtual threads.  The concept of snapshots is not present in vscode and the debug protocol, so threads
  are reported for each active breakpoint.
  * Threads should only be reported for "final" breakpoints
  * Thread names should be understandable -- they are currently breakpoint ids
  * Clicking on a breakpoint in the breakpoint list should result in the relevant "thread" being selected.
  * Deleting a breakpoint should result in its thread being removed.
  * Note: if only one thread is reported, the thread name is not shown in the UI

* Snapshots
  * Only basic functionality of the debug protocol 'variable' type is being used
  * Errors do not use substitution in the error messages, resulting in messages like "no code on line $0"
  * Some agents specify `null` values by pointing to an empty entry in the variable table.  This needs to be handled still.

* Files
  * There is no current way to hint to users that the version of the file they are viewing is not the version of the file that they are debugging.
  * Stacktraces that include files in dependencies are reported as existing in the local workspace.  They are not, so result in ugly error messages being displayed.

* Expressions
  * There is no known clean way to create expressions for breakpoints.  This is a bit of a problem because it's the standard way to manage truncated snapshots (eg. long strings, arrays, etc)

* Updating breakpoint locations
  * TODO: Check this -- The Java agent will move breakpoints to the nearest line of code that can have a breakpoint.  This is not handled in this extension and will result in undefined/undesireable behaviour.

* Expected debugger functionality.  The Snapshot Debugger is not a typical debugger so does not support things like resuming, stepping through code, watch expressions, etc.
  * Disable/remove/no-op the step-through functionality
  * Disable/hide/repurpose the watch expressions

* Detaching
  * This is just currently not supported.  The button claims that you've detached, but the resources are still in place.  They need to be cleaned up.

## Release Notes

### 1.0.0

Initial release (Soon?)


[snapshot-debugger-readme]: https://github.com/GoogleCloudPlatform/snapshot-debugger#readme
[setting-up-in-application]: https://github.com/GoogleCloudPlatform/snapshot-debugger#set-up-snapshot-debugger-in-your-google-cloud-project