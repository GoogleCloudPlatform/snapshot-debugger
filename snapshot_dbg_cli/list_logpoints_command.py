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
"""This module contains the support for the list_logpoints command.

The list_logpoints command is Used to display the debug logpoints for a debug
target (debuggee).
"""

from snapshot_dbg_cli import breakpoint_utils

DESCRIPTION = """
Used to display the debug logpoints for a debug target (debuggee). By default
all active logpoints are returned. To obtain older, expired logpoints, specify
the --include-inactive option.
"""

INCLUDE_INACTIVE_HELP = 'Include all logpoints which have completed.'

ALL_USERS_HELP = """
If false, display only logpoints created by the current user. Enabled by
default, use --no-all-users to disable.
"""

NO_ALL_USERS_HELP = """
Disables --all-users, which is enabled by default.
"""

SUMMARY_HEADERS = [
    'User Email', 'Location', 'Condition', 'Log Level', 'Log Message Format',
    'ID', 'Status'
]


def transform_to_logpoint_summary(logpoint):
  # Match the fields from SUMMARY_HEADERS
  return [
      logpoint['userEmail'],
      breakpoint_utils.transform_location_to_file_line(logpoint['location']),
      logpoint['condition'] if 'condition' in logpoint else '',
      logpoint['logLevel'],
      logpoint['logMessageFormatString'],
      logpoint['id'],
      breakpoint_utils.get_logpoint_short_status(logpoint),
  ]


class ListLogpointsCommand:
  """This class implements the list_logpoints command.

  The register() method is called by the CLI startup code to install the
  list_logpoints command information, and the cmd() function will be invoked if
  the list_logpoints command was specified by the user.
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
        'list_logpoints', description=DESCRIPTION, parents=parent_parsers)
    parser.add_argument(
        '--include-inactive', help=INCLUDE_INACTIVE_HELP, action='store_true')
    parser.add_argument(
        '--all-users',
        help=ALL_USERS_HELP,
        default=True,
        action='store_true',
        dest='all_users')
    parser.add_argument(
        '--no-all-users',
        help=NO_ALL_USERS_HELP,
        action='store_false',
        dest='all_users')
    parser.set_defaults(func=self.cmd)

  def cmd(self, args, cli_services):
    user_output = cli_services.user_output
    debugger_rtdb_service = cli_services.get_snapshot_debugger_rtdb_service()

    debugger_rtdb_service.validate_debuggee_id(args.debuggee_id)

    user_email = None if args.all_users is True else cli_services.account

    logpoints = debugger_rtdb_service.get_logpoints(
        debuggee_id=args.debuggee_id,
        include_inactive=args.include_inactive,
        user_email=user_email)

    if args.format.is_a_json_value():
      user_output.json_format(logpoints, pretty=args.format.is_pretty_json())
    else:
      values = list(map(transform_to_logpoint_summary, logpoints))
      user_output.tabular(SUMMARY_HEADERS, values)
