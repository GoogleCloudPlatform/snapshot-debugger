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

## Quirks / Potential Improvements

* Attaching
  * A service account file is required.  It would be better if we could use user credentials instead.
  * A debuggee id is required.  It can be provided in launch.json or selected at launch time.

* Breakpoint management. The system attempts to synchronize breakpoints on the IDE and the backend.
  * Breakpoints set in the UI prior to attaching will attempt to match against active breakpoints on the server.  If there isn't a match, a new breakpoint will be created.
  * There should be a way to view "final" breakpoints, either for management or for viewing snapshots.
  * All active breakpoints are read twice; once before completing attachment and once immediately after (concurrently).

* Virtual threads.  The concept of snapshots is not present in vscode and the debug protocol, so threads
  are reported for each active breakpoint.
  * Threads for breakpoints with errors - it would be nice if the breakpoint was highlighted (eg. stack trace that includes path & line for problematic breakpoint)
  * Clicking on a breakpoint in the breakpoint list should result in the relevant "thread" being selected.
  * Note: if only one thread is reported, the thread name is not shown in the UI

* Logpoints
  * Not yet supported

* Files
  * There is no current way to hint to users that the version of the file they are viewing is not the version of the file that they are debugging.
  * Stacktraces that include files in dependencies are reported as existing in the local workspace.  They are not, so result in ugly error messages being displayed.

* Expressions
  * Requests for expressions by default when attaching and having breakpoints already set is a bit jarring.
  * Expressions can't be used for breakpoint matching because the SourceBreakpoint does not include expressions.

* Expected debugger functionality.  The Snapshot Debugger is not a typical debugger so does not support things like resuming, stepping through code, watch expressions, etc.
  * Disable/remove/no-op the step-through functionality
  * Disable/hide/repurpose the watch expressions

## Known Issues

* Attaching
  * No testing/fallback logic is present for database urls.

* Breakpoint management
  * SetBreakpoints response breakpoints need to be in the same order as they are in the request.  This is currently not the case and results in the UI merging breakpoints incorrectly.
  * Matching local and backend breakpoints is done through path and line number.  This should be improved:
    * Include conditions
    * Handle multiple matches in a reasonable way (TBD)

* Virtual threads
  * The resume button completely messes up the state; it sets the threads to be "running" and there's no way to bring back the stack traces.
  * Deleting a breakpoint should result in its thread being removed.  At the very least, there should be a way to delete them.

* Updating breakpoint locations
  * TODO: Check this -- The Java agent will move breakpoints to the nearest line of code that can have a breakpoint.  This is not handled in this extension and will result in undefined/undesireable behaviour.

## Release Notes

### 1.0.0

Initial release (Soon?)


[snapshot-debugger-readme]: https://github.com/GoogleCloudPlatform/snapshot-debugger#readme
[setting-up-in-application]: https://github.com/GoogleCloudPlatform/snapshot-debugger#set-up-snapshot-debugger-in-your-google-cloud-project