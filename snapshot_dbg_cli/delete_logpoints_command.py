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

from snapshot_dbg_cli import breakpoint_utils
from snapshot_dbg_cli import delete_breakpoints

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
    delete_breakpoints.run_cmd('LOG', args, cli_services, SUMMARY_HEADERS,
                               transform_to_logpoint_summary)
