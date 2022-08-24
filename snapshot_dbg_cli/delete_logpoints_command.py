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
"""This module contains the support for the delete_logpoints command.

The delete_logpoints command is used to delete logpoints from a debug target
(debuggee).
"""

from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli import breakpoint_utils

DESCRIPTION = """
Used to delete logpoints from a debug target (debuggee). You are prompted for
confirmation before any logpoints are deleted. To suppress confirmation, use the
--quiet option.
"""

ID_HELP = """
Zero or more logpoint IDs. The specified logpoints will be deleted. By default,
if no logpoint IDs are specified, all active logpoints created by the user are
selected for deletion.
"""

ALL_USERS_HELP = """
If set, logpoints from all users will be deleted, rather than only logpoints
created by the current user. This flag is not required when specifying the exact
ID of a logpoint.
"""

INCLUDE_INACTIVE_HELP = """
If set, also delete logpoints which have been completed. By default, only
pending logpoints will be deleted. This flag is not required when specifying the
exact ID of an inactive logpoint.
"""

QUIET_HELP = 'If set, suppresses user confirmation of the command.'

SUMMARY_HEADERS = [
    'Location', 'Condition', 'Log Level', 'Log Message Format', 'ID'
]


def transform_to_logpoint_summary(logpoint):
  # Match the fields from SUMMARY_HEADERS
  return [
      breakpoint_utils.transform_location_to_file_line(logpoint['location']),
      logpoint['condition'] if 'condition' in logpoint else '',
      logpoint['logLevel'],
      logpoint['logMessageFormatString'],
      logpoint['id'],
  ]


class DeleteLogpointsCommand:
  """This class implements the delete_logpoints command.

  The register() method is called by the CLI startup code to install the
  delete_logpoints command information, and the cmd() function will be invoked
  if the delete_logpoints command was specified by the user.
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
        'delete_logpoints', description=DESCRIPTION, parents=parent_parsers)
    parser.add_argument('ID', help=ID_HELP, nargs='*')
    parser.add_argument('--all-users', help=ALL_USERS_HELP, action='store_true')
    parser.add_argument(
        '--include-inactive', help=INCLUDE_INACTIVE_HELP, action='store_true')
    parser.add_argument('--quiet', help=QUIET_HELP, action='store_true')
    parser.set_defaults(func=self.cmd)

  def cmd(self, args, cli_services):
    user_input = cli_services.user_input
    user_output = cli_services.user_output
    debugger_rtdb_service = cli_services.get_snapshot_debugger_rtdb_service()

    debugger_rtdb_service.validate_debuggee_id(args.debuggee_id)

    # This will be a list, if no IDs were specified it will be empty. If any IDs
    # are specified those are the only ones that will be deleted.
    logpoint_ids = args.ID

    user_email = None if args.all_users is True else cli_services.account

    logpoints = []

    if logpoint_ids:
      ids_not_found = []

      for bp_id in logpoint_ids:
        logpoint = debugger_rtdb_service.get_breakpoint(args.debuggee_id, bp_id)
        if logpoint is None or logpoint['action'] != 'LOG':
          ids_not_found.append(bp_id)
        else:
          logpoints.append(logpoint)

      if ids_not_found:
        user_output.error(f"Logpoint ID not found: {', '.join(ids_not_found)}")
        raise SilentlyExitError
    else:
      logpoints = debugger_rtdb_service.get_logpoints(args.debuggee_id,
                                                      args.include_inactive,
                                                      user_email)

    if logpoints:
      user_output.normal('This command will delete the following logpoints:\n')
      values = list(map(transform_to_logpoint_summary, logpoints))
      user_output.tabular(SUMMARY_HEADERS, values)
      user_output.normal('\n')

      if not args.quiet and not user_input.prompt_user_to_continue():
        user_output.error('Delete aborted.')
        return

      debugger_rtdb_service.delete_breakpoints(args.debuggee_id, logpoints)

    # The status is output regardless of the requested output format. It should
    # go to stderr, and if json output is requested, that should end up on
    # stdout.
    user_output.normal(f'Deleted {len(logpoints)} logpoints.')

    if args.format.is_a_json_value():
      user_output.json_format(logpoints, pretty=args.format.is_pretty_json())
