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
"""This module contains the support for the get_logpoint command.

The get_logpoint command is used to create a logpoint on a debug target
(Debuggee).
"""

from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli import breakpoint_utils

DESCRIPTION = """
Used to retrieve a debug logpoint from a debug target (debuggee).
"""

ID_HELP = 'Specify the logpoint ID to retrieve.'


class GetLogpointCommand:
  """This class implements the get_logpoint command.

  The register() method is called by the CLI startup code to install the
  get_logpoint command information, and the cmd() function will be invoked if
  the get_logpoint command was specified by the user.
  """

  def __init__(self):
    pass

  def register(self, args_subparsers, required_parsers, common_parsers):
    parent_parsers = [
        common_parsers.database_url, common_parsers.format,
        common_parsers.debuggee_id
    ]
    parent_parsers += required_parsers
    parser = args_subparsers.add_parser(
        'get_logpoint', description=DESCRIPTION, parents=parent_parsers)
    parser.add_argument('logpoint_id', metavar='ID', help=ID_HELP)
    parser.set_defaults(func=self.cmd)

  def display_summary(self, bp):
    # To note we're being defensive here with respect to the condition field the
    # that its absence is treated to the same way as it being present but empty.
    logpoint_id = bp['id']
    location = breakpoint_utils.transform_location_to_file_line(bp['location'])
    condition = bp.get('condition', '')
    condition = condition if condition != '' else 'No condition set'
    status = breakpoint_utils.get_logpoint_short_status(bp)
    log_message_format = bp['logMessageFormatString']
    create_time = bp['createTime']
    final_time = bp.get('finalTime', '')
    user_email = bp.get('userEmail', '')

    self.user_output.normal(f'Logpoint ID:        {logpoint_id}')
    self.user_output.normal(f'Log Message Format: {log_message_format}')
    self.user_output.normal(f'Location:           {location}')
    self.user_output.normal(f'Condition:          {condition}')
    self.user_output.normal(f'Status:             {status}')
    self.user_output.normal(f'Create Time:        {create_time}')
    self.user_output.normal(f'Final Time:         {final_time}')
    self.user_output.normal(f'User Email:         {user_email}')

  def cmd(self, args, cli_services):
    self.data_formatter = cli_services.data_formatter
    self.user_output = cli_services.user_output
    debugger_rtdb_service = cli_services.get_snapshot_debugger_rtdb_service()

    debugger_rtdb_service.validate_debuggee_id(args.debuggee_id)
    logpoint = debugger_rtdb_service.get_breakpoint(args.debuggee_id,
                                                    args.logpoint_id)

    if logpoint is None or logpoint['action'] != 'LOG':
      self.user_output.error(f'Logpoint ID not found: {args.logpoint_id}')
      raise SilentlyExitError

    if args.format.is_a_json_value():
      self.user_output.json_format(
          logpoint, pretty=args.format.is_pretty_json())
      return

    self.display_summary(logpoint)
