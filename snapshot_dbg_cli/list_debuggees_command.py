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

import time

DESCRIPTION = """
Used to display a list of the debug targets (debuggees) registered with the
Snapshot Debugger. By default all active debuggees are returned. To also obtain
inactive debuggees specify the --include-inactive option.
"""

INCLUDE_INACTIVE_HELP = 'Include inactive debuggees.'


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

    current_time_unix_msec = int(time.time() * 1000)
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

    # We add the second sort parameter on displayName for older agents that
    # don't support the 'active debuggee' feature. They will all have the same
    # lastUpdateTimeUnixMsec of 0, so they will still get some useful sorting.
    debuggees = sorted(
        debuggees,
        key=lambda d: (d['lastUpdateTimeUnixMsec'], d['displayName']),
        reverse=True)

    if args.format.is_a_json_value():
      user_output.json_format(debuggees, pretty=args.format.is_pretty_json())
    else:
      headers = ['Name', 'ID', 'Description']

      values = [[d['displayName'], d['id'], d['description']] for d in debuggees
               ]

      user_output.tabular(headers, values)
