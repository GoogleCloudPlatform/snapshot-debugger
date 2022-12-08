# CLI Command Reference

## init

```
snapshot-cdbg-cli init
```

Usage: `__main__.py init [-h] [--use-default-rtdb] [--debug] [--database-id
DATABASE_ID] [-l LOCATION]`

Initializes a GCP project with the required Firebase resources so Snapshot
Debugger can use Firebase as a backend. This must be done at least once per
project. This command is safe to run multiple times, as the command will
determine what, if anything, needs to be done. Some steps require the user to
perform a requested action and then rerun the command to make progress.

### Optional arguments

| Argument                    | Description |
|-----------------------------|-------------|
| `-h`, `--help`              | Show this help message and exit. |
| `--use-default-rtdb`        | Required for projects on the Spark plan. When specified, instructs the CLI to use the project's default Firebase RTDB database. |
| `--database-id DATABASE_ID` | Specify the ID of the database instance for the CLI to create as part of the initialization process. If not specified, defaults to `PROJECT_ID-cdbg`. |
| `--debug`                   | Enable CLI debug messages. |

## list_debuggees

```
snapshot-cdbg-cli list_debuggees
```


Usage: `__main__.py list_debuggees [-h] [--database-url DATABASE_URL] [--format
FORMAT] [--debug] [--include-inactive]`

Used to display a list of the debug targets (debuggees) registered with the
Snapshot Debugger. By default all active debuggees are returned. To also obtain
inactive debuggees specify the --include-inactive option.

### Optional arguments

| Argument                      | Description |
|-------------------------------|-------------|
| `-h`, `--help`                | Show this help message and exit. |
| `--include-inactive`          | Include inactive debuggees. |
| `--database-url DATABASE_URL` | Specify the database URL for the CLI to use. This should only be used as an override to make the CLI talk to a specific instance and isn't expected to be needed. It is only required if the `--database-id` argument was used with the init command.  This value may be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DATABASE_URL` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--format FORMAT`             | Set the format for printing command output resources. The default is a command-specific human-friendly output format. The supported formats are: `default`, `json` (raw) and `pretty-json` (formatted `json`). |
| `--debug`                     | Enable CLI debug messages. |


## set_snapshot

```
snapshot-cdbg-cli set_snapshot
```

Usage: `__main__.py set_snapshot [-h] [--database-url DATABASE_URL]
[--debug] [--condition CONDITION] [--expression EXPRESSION]
[--debuggee-id DEBUGGEE_ID] LOCATION`

Creates a snapshot on a debug target (Debuggee). Snapshots allow you to capture
stack traces and local variables from your running service without interfering
with normal operations. When any instance of the target executes the snapshot
location, the optional condition expression is evaluated. If the result is true
(or if there is no condition), the instance captures the current thread state
and reports it back to the Snapshot Debugger. Once any instance captures a
snapshot, the snapshot is marked as completed, and it will not be captured
again. It is also possible to inspect snapshot results with the
`get_snapshot` command.

### Positional arguments

| Argument      | Description |
|---------------|-------------|
| `LOCATION`    | Specify the location to take a snapshot. Locations are of the form `FILE:LINE`, where `FILE` is the file name, or the file name preceded by enough path components to differentiate it from other files with the same name. If the file name isn't unique in the debuggee, the behavior is unspecified. |

### Optional arguments

| Argument                      | Description |
|-------------------------------|-------------|
| `-h`, `--help`                | Show this help message and exit. |
| `--debuggee-id DEBUGGEE_ID`   | Specify the debuggee ID. It must be an ID obtained from the `list_debuggees` command. This value is required, it must be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DEBUGGEE_ID` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--database-url DATABASE_URL` | Specify the database URL for the CLI to use. This should only be used as an override to make the CLI talk to a specific instance and isn't expected to be needed. It is only required if the `--database-id` argument was used with the init command.  This value may be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DATABASE_URL` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--debug`                     | Enable CLI debug messages. |
| `--condition CONDITION`       | Specify a condition to restrict when the snapshot is taken. When the snapshot location is executed, the condition will be evaluated, and the snapshot is generated if the condition is true. |
| `--expression EXPRESSION`     | Specify an expression to evaluate when the snapshot is taken. You may specify `--expression` multiple times. |

## list_snapshots

```
snapshot-cdbg-cli list_snapshots
```


Usage: `__main__.py list_snapshots [-h] [--database-url DATABASE_URL] [--format
FORMAT] [--debug] [--all-users] [--include-inactive]
[--debuggee-id DEBUGGEE_ID]`

Used to display the debug snapshots for a debug target (debuggee). By default
all active snapshots are returned. To obtain completed snapshots specify the
`--include-inactive` option.

### Optional arguments

| Arguments                     | Description |
|-------------------------------|-------------|
| -h, --help                    | Show this help message and exit. |
| `--include-inactive`          | Include completed snapshots. |
| ` --all-users`                | If set, display snapshots from all users, rather than only the current user. |
| `--debuggee-id DEBUGGEE_ID`   | Specify the debuggee ID. It must be an ID obtained from the `list_debuggees` command. This value is required, it must be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DEBUGGEE_ID` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--database-url DATABASE_URL` | Specify the database URL for the CLI to use. This should only be used as an override to make the CLI talk to a specific instance and isn't expected to be needed. It is only required if the `--database-id` argument was used with the init command.  This value may be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DATABASE_URL` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--format FORMAT`             | Set the format for printing command output resources. The default is a command-specific human-friendly output format. The supported formats are: `default`, `json` (raw) and `pretty-json` (formatted `json`). |
| `--debug`                     | Enable CLI debug messages. |

## get_snapshot

```
snapshot-cdbg-cli get_snapshot
```

Usage: `__main__.py get_snapshot [-h] [--database-url DATABASE_URL] [--format FORMAT]
[--debug] [--frame-index FRAME_INDEX] [--max-level
MAX_LEVEL] [--debuggee-id DEBUGGEE_ID]`

Used to retrieve a debug snapshot from a debug target (debuggee). If the
snapshot has completed, the output includes details on the stack trace and local
variables. By default the expressions and local variables for the first stack
frame are displayed to 3 levels deep. To see the local variables from another
stack frame specify the `--frame-index` option. When the `json` or `pretty-json`
format outputs are selected, the entire snapshot data is emitted in a compact
form which is intended to be machine-readable rather than human-readable.

### Positional arguments

| Arguments     | Description |
|---------------|-------------|
| `ID`          | Specify the snapshot ID to retrieve. |

### Optional arguments

| Arguments                     | Description |
|-------------------------------|-------------|
| -h, --help                    | Show this help message and exit. |
| `--debuggee-id DEBUGGEE_ID`   | Specify the debuggee ID. It must be an ID obtained from the `list_debuggees` command. This value is required, it must be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DEBUGGEE_ID` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--database-url DATABASE_URL` | Specify the database URL for the CLI to use. This should only be used as an override to make the CLI talk to a specific instance and isn't expected to be needed. It is only required if the `--database-id` argument was used with the init command.  This value may be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DATABASE_URL` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--format FORMAT`             | Set the format for printing command output resources. The default is a command-specific human-friendly output format. The supported formats are: `default`, `json` (raw) and `pretty-json` (formatted `json`). |
| `--debug`                     | Enable CLI debug messages. |
| ` --frame-index FRAME_INDEX`  | Set the stack frame to display local variables from, the default is 0, which is the top of the stack. |
| `--max-level MAX_LEVEL`       | Set the maximum variable expansion to use when the `--format` option is `default`. The default value is 3. |


## delete_snapshots

```
snapshot-cdbg-cli delete_snapshots
```

Usage: `__main__.py delete_snapshots [-h] [--database-url DATABASE_URL] [--format
FORMAT] [--debug] [--all-users] [--include-inactive]
[--quiet] [--debuggee-id DEBUGGEE_ID] [ID ...]`

Used to delete snapshots from a debug target (debuggee). You are prompted for
confirmation before any snapshots are deleted. To suppress confirmation, use the
--quiet option.


### Positional arguments

| Arguments     | Description |
|---------------|-------------|
| `ID`          | Zero or more snapshot IDs. The specified snapshots will be deleted. By default, if no snapshot IDs are specified, all active snapshots created by the user are selected for deletion. |

### Optional arguments

| Arguments                     | Description |
|-------------------------------|-------------|
| -h, --help                    | Show this help message and exit. |
| `--include-inactive`          | Include completed snapshots. |
| `--debuggee-id DEBUGGEE_ID`   | Specify the debuggee ID. It must be an ID obtained from the `list_debuggees` command. This value is required, it must be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DEBUGGEE_ID` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--database-url DATABASE_URL` | Specify the database URL for the CLI to use. This should only be used as an override to make the CLI talk to a specific instance and isn't expected to be needed. It is only required if the `--database-id` argument was used with the init command.  This value may be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DATABASE_URL` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--format FORMAT`             | Set the format for printing command output resources. The default is a command-specific human-friendly output format. The supported formats are: `default`, `json` (raw) and `pretty-json` (formatted `json`). |
| `--debug`                     | Enable CLI debug messages. |
| ` --all-users`                | If set, snapshots from all users will be deleted, rather than only snapshots created by the current user. This flag is not required when specifying the exact ID of a snapshot. |
| `--include-inactive`          | If set, also delete snapshots which have been completed. By default, only pending snapshots will be deleted. This flag is not required when specifying the exact ID of an inactive snapshot. |
| `--quiet`                     | If set, suppresses user confirmation of the command. |

## set_logpoint

```
snapshot-cdbg-cli set_logpoint
```

Usage: `__main__.py set_logpoint [-h] [--database-url DATABASE_URL] [--format
FORMAT] [--debuggee-id DEBUGGEE_ID] [--debug] [--log-level LOG_LEVEL]
[--condition CONDITION] LOCATION LOG_FORMAT_STRING`

Adds a debug logpoint to a debug target (debuggee). Logpoints inject logging
into running services without changing your code or restarting your application.
Every time any instance executes code at the logpoint location, Snapshot
Debugger logs a message. Output is sent to the standard log for the programming
language of the target (java.logging for ava, logging for Python, etc.)

Logpoints remain active for 24 hours after creation, or until they are deleted
or the service is redeployed. If you place a logpoint on a line that receives
lots of traffic, Debugger throttles the logpoint to reduce its impact on your
application.


### Positional arguments

| Argument            | Description |
|---------------------|-------------|
| `LOCATION`          | Specify the location to add the logpoint. Locations are of the form `FILE:LINE`, where `FILE` is the file name, or the file name preceded by enough path components to differentiate it from other files with the same name. If the file name isn't unique in the debuggee, the behavior is unspecified. |
| `LOG_FORMAT_STRING` | Specify a format string which will be logged every time the logpoint location is executed. If the string contains curly braces ('{' and '}'), any text within the curly braces will be interpreted as a run-time expression in the debug target's language, which will be evaluated when the logpoint is hit. The value of the expression will then replace the {} expression in the resulting log output. For example, if you specify the format string "a={a}, b={b}", and the logpoint is hit when local variable a is 1 and b is 2, the resulting log output would be "a=1, b=2". |

### Optional arguments

| Argument                      | Description |
|-------------------------------|-------------|
| `-h`, `--help`                | Show this help message and exit. |
| `--debuggee-id DEBUGGEE_ID`   | Specify the debuggee ID. It must be an ID obtained from the `list_debuggees` command. This value is required, it must be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DEBUGGEE_ID` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--database-url DATABASE_URL` | Specify the database URL for the CLI to use. This should only be used as an override to make the CLI talk to a specific instance and isn't expected to be needed. It is only required if the `--database-id` argument was used with the init command.  This value may be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DATABASE_URL` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--debug`                     | Enable CLI debug messages. |
| `--log-level LOG_LEVEL`       | The logging level to use when producing the log message. `LOG_LEVEL` must be one of: [info, warning, error]. If not specified, `info` is used by default. |
| `--condition CONDITION`       | Specify a condition to restrict when the log output is generated. When the logpoint is hit, the condition will be evaluated, and the log output will be generated only if the condition is true. |

## list_logpoints

```
snapshot-cdbg-cli list_logpoints
```


Usage: `__main__.py list_snapshots [-h] [--database-url DATABASE_URL] [--format
FORMAT] [--debuggee-id DEBUGGEE_ID] [--debug] [--include-inactive] [--all-users]
[--no-all-users]`

Used to display the debug logpoints for a debug target (debuggee). By default
all active logpoints are returned. To obtain older, expired logpoints, specify
the --include-inactive option.

### Optional arguments

| Arguments                     | Description |
|-------------------------------|-------------|
| -h, --help                    | Show this help message and exit. |
| `--include-inactive`          | Include all logpoints which have completed. |
| ` --all-users`                | If false, display only logpoints created by the current user. Enabled by default, use `--no-all-users` to disable. |
| ` --no-all-users`             | Disables `--all-users`, which is enabled by default. |
| `--debuggee-id DEBUGGEE_ID`   | Specify the debuggee ID. It must be an ID obtained from the `list_debuggees` command. This value is required, it must be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DEBUGGEE_ID` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--database-url DATABASE_URL` | Specify the database URL for the CLI to use. This should only be used as an override to make the CLI talk to a specific instance and isn't expected to be needed. It is only required if the `--database-id` argument was used with the init command.  This value may be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DATABASE_URL` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--format FORMAT`             | Set the format for printing command output resources. The default is a command-specific human-friendly output format. The supported formats are: `default`, `json` (raw) and `pretty-json` (formatted `json`). |
| `--debug`                     | Enable CLI debug messages. |

## get_logpoint

```
snapshot-cdbg-cli get_logpoint
```

Usage: `__main__.py get_logpoint [-h] [--database-url DATABASE_URL] [--format
FORMAT] [--debuggee-id DEBUGGEE_ID] [--debug] ID`

Used to retrieve a debug logpoint from a debug target (debuggee).

### Positional arguments

| Arguments     | Description |
|---------------|-------------|
| `ID`          | Specify the logpoint ID to retrieve. |

### Optional arguments

| Arguments                     | Description |
|-------------------------------|-------------|
| -h, --help                    | Show this help message and exit. |
| `--debuggee-id DEBUGGEE_ID`   | Specify the debuggee ID. It must be an ID obtained from the `list_debuggees` command. This value is required, it must be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DEBUGGEE_ID` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--database-url DATABASE_URL` | Specify the database URL for the CLI to use. This should only be used as an override to make the CLI talk to a specific instance and isn't expected to be needed. It is only required if the `--database-id` argument was used with the init command.  This value may be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DATABASE_URL` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--format FORMAT`             | Set the format for printing command output resources. The default is a command-specific human-friendly output format. The supported formats are: `default`, `json` (raw) and `pretty-json` (formatted `json`). |
| `--debug`                     | Enable CLI debug messages. |

## delete_logpoints

```
logpoint-cdbg-cli delete_logpoints
```

Usage: `__main__.py delete_logpoints [-h] [--database-url DATABASE_URL] [--format
FORMAT] [--debug] [--all-users] [--include-inactive]
[--quiet] [--debuggee-id DEBUGGEE_ID] [ID ...]`

Used to delete logpoints from a debug target (debuggee). You are prompted for
confirmation before any logpoints are deleted. To suppress confirmation, use the
--quiet option.


### Positional arguments

| Arguments     | Description |
|---------------|-------------|
| `ID`          | Zero or more logpoint IDs. The specified logpoints will be deleted. By default, if no logpoint IDs are specified, all active logpoints created by the user are selected for deletion. |

### Optional arguments

| Arguments                     | Description |
|-------------------------------|-------------|
| -h, --help                    | Show this help message and exit. |
| `--include-inactive`          | Include completed logpoints. |
| `--debuggee-id DEBUGGEE_ID`   | Specify the debuggee ID. It must be an ID obtained from the `list_debuggees` command. This value is required, it must be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DEBUGGEE_ID` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--database-url DATABASE_URL` | Specify the database URL for the CLI to use. This should only be used as an override to make the CLI talk to a specific instance and isn't expected to be needed. It is only required if the `--database-id` argument was used with the init command.  This value may be specified either via this command line argument or via the `SNAPSHOT_DEBUGGER_DATABASE_URL` environment variable.  When both are specified, the value from the command line takes precedence. |
| `--format FORMAT`             | Set the format for printing command output resources. The default is a command-specific human-friendly output format. The supported formats are: `default`, `json` (raw) and `pretty-json` (formatted `json`). |
| `--debug`                     | Enable CLI debug messages. |
| ` --all-users`                | If set, logpoints from all users will be deleted, rather than only logpoints created by the current user. This flag is not required when specifying the exact ID of a logpoint. |
| `--include-inactive`          | If set, also delete logpoints which have been completed. By default, only pending logpoints will be deleted. This flag is not required when specifying the exact ID of an inactive logpoint. |
| `--quiet`                     | If set, suppresses user confirmation of the command. |

