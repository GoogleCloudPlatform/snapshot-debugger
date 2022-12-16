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
"""This module contains the support for the list_debuggees command.

The list_debugees command is used to display a list of the debug targets
(debuggees) registered with the Snapshot Debugger.
"""

from snapshot_dbg_cli.debuggee_utils import get_debuggee_status
from snapshot_dbg_cli.debuggee_utils import sort_debuggees
from snapshot_dbg_cli.time_utils import get_current_time_unix_msec

DESCRIPTION = """
Used to display a list of the debug targets (debuggees) registered with the
Snapshot Debugger. By default all active debuggees are returned. To also obtain
inactive debuggees specify the --include-inactive option.  A debuggee is
considered to be active if it currently running or last ran in the past 5-6
hours.
"""

INCLUDE_INACTIVE_HELP = 'Include inactive debuggees.'

SUMMARY_HEADERS = headers = [
    'Name', 'ID', 'Description', 'Last Active', 'Status'
]


def transform_to_debuggee_summary(debuggee):
  # Match the fields from SUMMARY_HEADERS
  return [
      debuggee['displayName'],
      debuggee['id'],
      debuggee['description'],
      debuggee['lastUpdateTime'],
      get_debuggee_status(debuggee),
  ]


class ListDebuggeesCommand:
  """This class implements the list_debuggees command.

  The register() method is called by the CLI startup code to install the
  list_debuggees command information, and the cmd() function will be invoked if
  the list_debuggees command was specified by the user.
  """

  def __init__(self):
    pass

  def register(self, args_subparsers, required_parsers, common_parsers):
    parent_parsers = [common_parsers.database_url, common_parsers.format]
    parent_parsers += required_parsers
    parser = args_subparsers.add_parser(
        'list_debuggees', description=DESCRIPTION, parents=parent_parsers)
    parser.add_argument(
        '--include-inactive', help=INCLUDE_INACTIVE_HELP, action='store_true')
    parser.set_defaults(func=self.cmd)

  def cmd(self, args, cli_services):
    user_output = cli_services.user_output

    current_time_unix_msec = get_current_time_unix_msec()
    debugger_rtdb_service = cli_services.get_snapshot_debugger_rtdb_service()
    debuggees = debugger_rtdb_service.get_debuggees(current_time_unix_msec)

    if not args.include_inactive:
      # If there are any debuggees that support the 'active debuggee' feature,
      # then we go ahead and apply isActive filter. Any debuggees that don't
      # support it will be filtered out, but given there are debuggees from
      # newer agents present odds then that debugees without this feature are
      # inactive.
      if any(d['activeDebuggeeEnabled'] for d in debuggees):
        debuggees = list(filter(lambda d: d['isActive'], debuggees))

    debuggees = sort_debuggees(debuggees)

    if args.format.is_a_json_value():
      user_output.json_format(debuggees, pretty=args.format.is_pretty_json())
    else:
      values = list(map(transform_to_debuggee_summary, debuggees))
      user_output.tabular(SUMMARY_HEADERS, values)
