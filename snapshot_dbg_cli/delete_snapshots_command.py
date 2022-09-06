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

from snapshot_dbg_cli import breakpoint_utils
from snapshot_dbg_cli import delete_breakpoints

DESCRIPTION = """
Used to delete snapshots from a debug target (debuggee). You are prompted for
confirmation before any snapshots are deleted. To suppress confirmation, use the
--quiet option.
"""

ID_HELP = """
Zero or more snapshot IDs. The specified snapshots will be deleted. By default,
if no snapshot IDs are specified, all active snapshots created by the user are
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
    delete_breakpoints.run_cmd('CAPTURE', args, cli_services, SUMMARY_HEADERS,
                               transform_to_snapshot_summary)
