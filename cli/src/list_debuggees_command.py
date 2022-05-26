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

import format_utils

DESCRIPTION = """
Used to display a list of the debug targets (debuggees) registered with the
Snapshot Debugger.
"""


def get_debuggee_name(debuggee):
  module = debuggee.get('labels', {}).get('module', 'default')
  version = debuggee.get('labels', {}).get('version', '')

  return f'{module} - {version}'


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
    parser.set_defaults(func=self.cmd)

  def cmd(self, args, cli_services):
    user_output = cli_services.user_output

    debugger_rtdb_service = cli_services.get_snapshot_debugger_rtdb_service()
    debuggees = debugger_rtdb_service.get_debuggees() or {}

    # The result will be a dictionary, convert it to an array
    debuggees = list(debuggees.values())

    if args.format in ('json', 'pretty-json'):
      format_utils.print_json(
          user_output, debuggees, pretty=(args.format == 'pretty-json'))
    else:
      headers = ['Name', 'ID', 'Description']

      values = [[
          get_debuggee_name(d),
          d.get('id', ''),
          d.get('description', '')
      ] for d in debuggees]

      format_utils.print_table(user_output, headers, values)
