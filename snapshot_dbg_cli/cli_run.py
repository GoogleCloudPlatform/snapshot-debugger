# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" The main Snapshot Debugger CLI startup code.

This module provides the run() function, which sets up the CLI commands, parses
the command line arguments and runs the specified command.
"""

import argparse
import sys

from snapshot_dbg_cli.cli_services import CliServices
from snapshot_dbg_cli import cli_common_arguments
from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli.delete_debuggees_command import DeleteDebuggeesCommand
from snapshot_dbg_cli.delete_logpoints_command import DeleteLogpointsCommand
from snapshot_dbg_cli.delete_snapshots_command import DeleteSnapshotsCommand
from snapshot_dbg_cli.get_logpoint_command import GetLogpointCommand
from snapshot_dbg_cli.get_snapshot_command import GetSnapshotCommand
from snapshot_dbg_cli.init_command import InitCommand
from snapshot_dbg_cli.list_debuggees_command import ListDebuggeesCommand
from snapshot_dbg_cli.list_logpoints_command import ListLogpointsCommand
from snapshot_dbg_cli.list_snapshots_command import ListSnapshotsCommand
from snapshot_dbg_cli.set_logpoint_command import SetLogpointCommand
from snapshot_dbg_cli.set_snapshot_command import SetSnapshotCommand


def run(cli_services=None):
  cli_commands = [
      DeleteDebuggeesCommand(),
      DeleteLogpointsCommand(),
      DeleteSnapshotsCommand(),
      GetLogpointCommand(),
      GetSnapshotCommand(),
      InitCommand(),
      ListLogpointsCommand(),
      ListSnapshotsCommand(),
      ListDebuggeesCommand(),
      SetLogpointCommand(),
      SetSnapshotCommand()
  ]

  args_parser = argparse.ArgumentParser()
  common_parsers = cli_common_arguments.CommonArgumentParsers()
  required_parsers = cli_common_arguments.RequiredArgumentParsers().parsers

  args_subparsers = args_parser.add_subparsers()

  for cmd in cli_commands:
    cmd.register(
        args_subparsers,
        required_parsers=required_parsers,
        common_parsers=common_parsers)

  args = args_parser.parse_args()

  if 'func' not in args:
    print(
        'Missing required argument, please specify --help for more information',
        file=sys.stderr)

    raise SilentlyExitError

  if cli_services is None:
    cli_services = CliServices(args)

  # This will run the appropriate command.
  args.func(args=args, cli_services=cli_services)
