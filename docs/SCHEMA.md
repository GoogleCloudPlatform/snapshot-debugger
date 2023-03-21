# Firebase Database Schema/Layout

The structure of the database layout is:

```
cdbg
├── breakpoints
│   ├── <debuggee id 1>
│   │   ├── active
│   │   │   ├── <breakpoint id 1>
│   │   │   │   └── <breakpoint entity>
│   │   │   ├── ...
│   │   │   └── <breakpoint id n>
│   │   │       └── <breakpoint entity>
│   │   ├── final
│   │   │   ├── <breakpoint id 1>
│   │   │   │   └── <breakpoint entity>
│   │   │   ├── ...
│   │   │   └── <breakpoint id n>
│   │   │       └── <breakpoint entity>
│   │   └──  snapshot
│   │       ├── <breakpoint id 1>
│   │       │   └── <breakpoint entity>
│   │       ├── ...
│   │       └── <breakpoint id n>
│   │           └── <breakpoint entity>
│   ├── ....
│   └── <debuggee id n>
│       ├── active
│       │   └── ...
│       ├── final ...
│       │   └── ...
│       └──  snapshot
│           └── ...
├── debuggees
│   ├── <debuggee id 1>
│   │   └── <debuggee entity>
│   ├── ....
│   └── <debuggee id n>
│       └── <debuggee entity>
└── schema_version: "<version_number>"
```

## cdbg/schema_version

Specifies the schema version of the database. The presence of this field is also
used as an indication that the database has been configured by the Snapshot
Debugger's `init` CLI command.

## cdbg/debuggees

This node contains information about the debuggees themselves. Upon startup the
agent computes a consistent debuggee ID, and `registers` itself in the DB.  It
does this by first checking if an entry already exists for the given ID. If it
does the agent simply updates the by writing the `registrationTimeUnixMsec` to
the current time, otherwise it writes out the full debuggee details.

It is also the responsibility of the agent to keep the `lastUpdateTimeUnixMsec`
field up to date by refreshing it at least once per hour while the agent is
running. The Snapshot Debugger CLI uses this value to determine which debuggees
are active.

### Debuggee Entity

The debuggee entity is fully documented in protobuf form
[here][debuggee_entity]. The data in the Firebase DB is in JSON format, which
protobuf maps to as described [here][json_mapping].

## cdbg/breakpoints

This node contains the breakpoints for debuggees stored on a per debuggee id
basis. The breakpoints are grouped into `active`, `final` and `snapshot`.

### Breakpoint Entity

The breakpoint entity is fully documented in protobuf form
[here][breakpoint_entity]. The data in the Firebase DB is in JSON format, which
protobuf maps to as described [here][json_mapping]. One thing to note
is how Firebase stores [arrays][firebase_arrays].

Breakpoints can represent either a `Snapshot` or a `Logpoint`. The value of the
`action` field of the breakpoint makes this determination, which will be either
`CAPTURE` or `LOG`. If the `action` field is not populated the agents will
default to `CAPTURE`.

### cdbg/breakpoints/debuggee_id/active

This node contains all of the active breakpoints for a given debuggee. When a
breakpoint is created it is considered active. It remains active until it is
either deleted by the user or it is finalized by an agent.

Then agents will finalize a breakpoint under the following scenarios:

1. A newly created breakpoint fails initial validation and is finalized being
   marked with an error. One reason for this would be an inability to set a
   breakpoint at the specified location, which may not exist.
1. The breakpoint is a `Snapshot` and it triggers.
1. The breakpoint is a `Snapshot` and it expires before being hit (by default
   after 24 hours).
1. The breakpoint is a `Logpoint` and it expires (by default after 24 hours).

When the agent finalizes a breakpoint it will be removed from the `active` node
and added to the `final` node, and possibly the `snapshot` node, see below for
further details.

### cdbg/breakpoints/debuggee_id/final

This node contains all finalized breakpoints (both `Snapshot` and `Logpoint`)
until deleted by the user. One important point to note, for `Snapshot`
breakpoints, the `stackFrames`, `variableTable` and `evaluatedExpressions` are
not present in the breakpoints under this node, it is the responsibility of the
agent to ensure they do not populate these fields for this node. This is to make
it cheaper to read all final breakpoints. When users need the full snapshot
data, this can then be retrieved using the complete data found under the
`snapshot` node.

Also to note, it is the agent's responsibility to set the `finalTimeUnixMsec`
field.

### cdbg/breakpoints/debuggee_id/snaphsot

This node contains all finalized `Snapshot` breakpoints until deleted by the
user. For finalized `Snapshot` breakpoints that have capture data, the full data
is present here, meaning the `stackFrames`, `variableTable` and
`evaluatedExpressions` are present, unlike under the `final` node.

[breakpoint_entity]: https://github.com/GoogleCloudPlatform/cloud-debug-java/blob/01148711d4d3f9ee566d21b21b80079a7b7206b1/schema/data.proto#L306
[debuggee_entity]: https://github.com/GoogleCloudPlatform/cloud-debug-java/blob/01148711d4d3f9ee566d21b21b80079a7b7206b1/schema/data.proto#L439
[json_mapping]: https://protobuf.dev/programming-guides/proto3/#json
[firebase_arrays]: https://firebase.googleblog.com/2014/04/best-practices-arrays-in-firebase.html

