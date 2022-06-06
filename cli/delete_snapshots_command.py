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
"""This module contains the support for the delete_snapshots command.

The delete_snapshots command is used to delete snapshots from a debug target
(debuggee).
"""

from cli.exceptions import SilentlyExitError
from cli import breakpoint_utils

DESCRIPTION = """
Used to delete snapshots from a debug target (debuggee). You are prompted for
confirmation before any snapshots are deleted. To suppress confirmation, use the
--quiet option.
"""

ID_HELP = """
Zero or more snapshot IDs. The specified snapshots will be deleted. By default,
If no snapshot IDs are specified, all active snapshots created by the user are
selected for deletion.
"""

ALL_USERS_HELP = """
If set, snapshots from all users will be deleted, rather than only snapshots
created by the current user. This flag is not required when specifying the exact
ID of a snapshot.
"""

INCLUDE_INACTIVE_HELP = """
If set, also delete snapshots which have been completed. By default, only
pending snapshots will be deleted. This flag is not required when specifying the
exact ID of an inactive snapshot.
"""

QUIET_HELP = 'If set, suppresses user confirmation of the command.'

SUMMARY_HEADERS = ['Status', 'Location', 'Condition', 'ID']


def transform_to_snapshot_summary(snapshot):
  # Match the fields from SUMMARY_HEADERS
  return [
      'COMPLETED' if snapshot['isFinalState'] else 'ACTIVE',
      breakpoint_utils.transform_location_to_file_line(snapshot['location']),
      snapshot['condition'] if 'condition' in snapshot else '', snapshot['id']
  ]


class DeleteSnapshotsCommand:
  """This class implements the delete_snapshots command.

  The register() method is called by the CLI startup code to install the
  delete_snapshots command information, and the cmd() function will be invoked
  if the delete_snapshots command was specified by the user.
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
        'delete_snapshots', description=DESCRIPTION, parents=parent_parsers)
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
    snapshot_ids = args.ID

    user_email = None if args.all_users is True else cli_services.account

    snapshots = []

    if snapshot_ids:
      ids_not_found = []

      for bp_id in snapshot_ids:
        snapshot = debugger_rtdb_service.get_breakpoint(args.debuggee_id, bp_id)
        if snapshot is None:
          ids_not_found.append(bp_id)
        else:
          snapshots.append(snapshot)

      if ids_not_found:
        user_output.error(f"Snapshot ID not found: {', '.join(ids_not_found)}")
        raise SilentlyExitError
    else:
      snapshots = debugger_rtdb_service.get_snapshots(args.debuggee_id,
                                                      args.include_inactive,
                                                      user_email)

    if snapshots:
      user_output.normal('This command will delete the following snapshots:\n')
      values = list(map(transform_to_snapshot_summary, snapshots))
      user_output.tabular(SUMMARY_HEADERS, values)
      user_output.normal('\n')

      if not args.quiet and not user_input.prompt_user_to_continue():
        user_output.error('Delete aborted.')
        return

    debugger_rtdb_service.delete_breakpoints(args.debuggee_id, snapshots)

    # Status output goes to stderr
    user_output.normal(f'Deleted {len(snapshots)} snapshots.')

    if args.format in ('json', 'pretty-json'):
      user_output.json_format(snapshots, pretty=(args.format == 'pretty-json'))
