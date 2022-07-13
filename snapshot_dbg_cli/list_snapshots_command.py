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
"""This module contains the support for the list_snapshots command.

The list_snapshots command is Used to display the debug snapshots for a debug
target (debuggee).
"""

from snapshot_dbg_cli import breakpoint_utils
from snapshot_dbg_cli.status_message import StatusMessage

DESCRIPTION = """
Used to display the debug snapshots for a debug target (debuggee). By default
all active snapshots are returned.  To obtain completed snapshots specify the
--include-inactive option.
"""

INCLUDE_INACTIVE_HELP = 'Include all snapshots which have completed.'

ALL_USERS_HELP = """
If set, display snapshots from all users, rather than only the current user.
"""

SUMMARY_HEADERS = ['Status', 'Location', 'Condition', 'CompletedTime', 'ID']


def get_snapshot_state(snapshot):
  if not snapshot['isFinalState']:
    return 'ACTIVE'

  status_message = StatusMessage(snapshot)

  if not status_message.is_error:
    return 'COMPLETED'

  refers_to = status_message.refers_to
  if refers_to == 'BREAKPOINT_AGE':
    return 'EXPIRED'

  return 'FAILED'


def transform_to_snapshot_summary(snapshot):
  # Match the fields from SUMMARY_HEADERS
  return [
      get_snapshot_state(snapshot),
      breakpoint_utils.transform_location_to_file_line(snapshot['location']),
      snapshot['condition'] if 'condition' in snapshot else '',
      snapshot['finalTime'] if 'finalTime' in snapshot else '', snapshot['id']
  ]


class ListSnapshotsCommand:
  """This class implements the list_snapshots command.

  The register() method is called by the CLI startup code to install the
  list_snapshots command information, and the cmd() function will be invoked if
  the list_snapshots command was specified by the user.
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
        'list_snapshots', description=DESCRIPTION, parents=parent_parsers)
    parser.add_argument(
        '--include-inactive', help=INCLUDE_INACTIVE_HELP, action='store_true')
    parser.add_argument('--all-users', help=ALL_USERS_HELP, action='store_true')
    parser.set_defaults(func=self.cmd)

  def cmd(self, args, cli_services):
    user_output = cli_services.user_output
    debugger_rtdb_service = cli_services.get_snapshot_debugger_rtdb_service()

    debugger_rtdb_service.validate_debuggee_id(args.debuggee_id)

    user_email = None if args.all_users is True else cli_services.account

    snapshots = debugger_rtdb_service.get_snapshots(
        debuggee_id=args.debuggee_id,
        include_inactive=args.include_inactive,
        user_email=user_email)

    if args.format.is_a_json_value():
      user_output.json_format(snapshots, pretty=args.format.is_pretty_json())
    else:
      values = list(map(transform_to_snapshot_summary, snapshots))
      user_output.tabular(SUMMARY_HEADERS, values)
