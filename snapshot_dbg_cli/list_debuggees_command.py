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

DESCRIPTION = """
Used to display a list of the debug targets (debuggees) registered with the
Snapshot Debugger.
"""


def validate_debuggee(debuggee):
  required_fields = ['id']

  return all(k in debuggee for k in required_fields)


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

    # The result will be a dictionary, convert it to an array, while also
    # filtering out any invalid entries, such as if it's missing a debuggee ID,
    # which is a required field.
    debuggees = list(filter(validate_debuggee, debuggees.values()))

    if args.format.is_a_json_value():
      user_output.json_format(debuggees, pretty=args.format.is_pretty_json())
    else:
      headers = ['Name', 'ID', 'Description']

      values = [[
          get_debuggee_name(d),
          d.get('id', ''),
          d.get('description', '')
      ] for d in debuggees]

      user_output.tabular(headers, values)
