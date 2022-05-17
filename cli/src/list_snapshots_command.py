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

import breakpoint_utils
import command_utils
import format_utils

DESCRIPTION = """
Used to display the debug snapshots for a debug target (debuggee). By default
all active snapshots are returned.  To obtain completed snapshots specify the
--include-inactive option.
"""

INCLUDE_INACTIVE_HELP = 'Include all snapshots which have completed.'

SUMMARY_HEADERS = ['Status', 'Location', 'Condition', 'CompletedTime', 'ID']


def transform_to_snapshot_summary(snapshot):
  # Match the fields from SUMMARY_HEADERS
  return [
      'COMPLETED' if snapshot['isFinalState'] else 'ACTIVE',
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
    parser.set_defaults(func=self.cmd)

  def cmd(self, args, cli_services):
    user_output = cli_services.user_output
    firebase_rtdb_service = cli_services.get_firebase_rtdb_service()

    command_utils.validate_debuggee_id(user_output, firebase_rtdb_service,
                                       args.debuggee_id)

    snapshots = breakpoint_utils.get_snapshots(firebase_rtdb_service,
                                               args.debuggee_id,
                                               args.include_inactive)

    if args.format in ('json', 'pretty-json'):
      format_utils.print_json(
          user_output, snapshots, pretty=(args.format == 'pretty-json'))
    else:
      values = list(map(transform_to_snapshot_summary, snapshots))
      format_utils.print_table(user_output, SUMMARY_HEADERS, values)
