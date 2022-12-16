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
"""This module contains the support for the delete_debuggees command.

The delete_debuggees command is used to delete debuggees. Deleting a debuggee
will also delete all breakpoints that belong to the debuggee.
"""

from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli.debuggee_utils import get_debuggee_status
from snapshot_dbg_cli.debuggee_utils import sort_debuggees
from snapshot_dbg_cli.time_utils import get_current_time_unix_msec

DESCRIPTION = """
Used to delete debuggees. Deleting a debuggee will also delete all breakpoints
that belong to the debuggee.  You are prompted for confirmation before any
debuggees are deleted. To suppress confirmation, use the --quiet option. By
default only stale debuggees will be deleted. To include other debuggees for
deletion include either the --include-inactive or --include-all flags.  A
debuggee is considered stale if it has not run for the past 7 days.
"""

ID_HELP = """
Zero or more debuggee IDs. The specified debugges will be deleted. By default,
if no debuggees IDs are specified, all stale debuggees are selected for
deletion.  A debuggee is considered stale if it has not run for the past 7 days.
"""

INCLUDE_INACTIVE_HELP = """
If set, include all inactive debuggees. A debuggee is considered to be inactive
if it has not run in the past 5-6 hours. By default, only stale debuggees will
be deleted. This flag is not required when specifying the exact ID of a
debuggee.
"""

INCLUDE_ALL_HELP = """
If set, include all debuggees. By default, only stale debuggees will be deleted.
This flag is not required when specifying the exact ID of a debuggee.
"""

QUIET_HELP = 'If set, suppresses user confirmation of the command.'

DELETE_ABORTED_QUIET_NOT_ALLOWED_MSG = """
Delete aborted. Run the command again without the --quiet option specified, it
cannot be used due to the unknown status of one or more debuggees.
"""

UNKNOWN_DEBUGGEE_STATUS_WARNING_MSG = """
WARNING, some debuggee entries do not have a last activity time (status is
UNKNOWN).  Be sure they are not in use before proceeding. To avoid this in the
future install the latest available version of the agent.
"""

SUMMARY_HEADERS = ['Name', 'ID', 'Last Active', 'Status']


def transform_to_debuggee_summary(debuggee):
  # Match the fields from SUMMARY_HEADERS
  return [
      debuggee['displayName'],
      debuggee['id'],
      debuggee['lastUpdateTime'],
      get_debuggee_status(debuggee),
  ]


def should_delete_debuggee_check(debuggee, args):
  if args.include_all:
    return True

  if args.include_inactive:
    return not debuggee['isActive']

  # By default we only delete stale and unknown debuggees. Debuggees who's last
  # update time is unknown will have their isStale flag set to true.
  return debuggee['isStale']


class DeleteDebuggeesCommand:
  """This class implements the delete_debuggees command.

  The register() method is called by the CLI startup code to install the
  delete_debuggees command information, and the cmd() function will be invoked
  if the delete_debuggees command was specified by the user.
  """

  def __init__(self):
    pass

  def register(self, args_subparsers, required_parsers, common_parsers):
    parent_parsers = [common_parsers.database_url, common_parsers.format]
    parent_parsers += required_parsers
    parser = args_subparsers.add_parser(
        'delete_debuggees', description=DESCRIPTION, parents=parent_parsers)
    parser.add_argument('ID', help=ID_HELP, nargs='*')
    parser.add_argument(
        '--include-inactive', help=INCLUDE_INACTIVE_HELP, action='store_true')
    parser.add_argument(
        '--include-all', help=INCLUDE_ALL_HELP, action='store_true')
    parser.add_argument('--quiet', help=QUIET_HELP, action='store_true')
    parser.set_defaults(func=self.cmd)

  def cmd(self, args, cli_services):
    user_input = cli_services.user_input
    user_output = cli_services.user_output
    debugger_rtdb_service = cli_services.get_snapshot_debugger_rtdb_service()

    # This will be a list, if no IDs were specified it will be empty. If any IDs
    # are specified those are the only ones that will be deleted.
    debuggee_ids = args.ID

    debuggees = []
    current_time_unix_msec = get_current_time_unix_msec()

    if debuggee_ids:
      ids_not_found = []

      for debuggee_id in debuggee_ids:
        debuggee = debugger_rtdb_service.get_debuggee(debuggee_id,
                                                      current_time_unix_msec)
        if debuggee is None:
          ids_not_found.append(debuggee_id)
        else:
          debuggees.append(debuggee)

      if ids_not_found:
        user_output.error('Debuggee ID not found: '
                          f"{', '.join(ids_not_found)}")
        raise SilentlyExitError
    else:
      debuggees = debugger_rtdb_service.get_debuggees(current_time_unix_msec)
      debuggees = list(
          filter(lambda d: should_delete_debuggee_check(d, args), debuggees))

    debuggees = sort_debuggees(debuggees)
    is_unknown_status_entries = any(
        not d['activeDebuggeeEnabled'] for d in debuggees)

    if debuggees:
      user_output.normal('This command will delete the following debuggees:\n')
      values = list(map(transform_to_debuggee_summary, debuggees))
      user_output.tabular(SUMMARY_HEADERS, values)
      user_output.normal('\n')

      if is_unknown_status_entries:
        if args.quiet:
          user_output.error(DELETE_ABORTED_QUIET_NOT_ALLOWED_MSG)
          return
        else:
          user_output.normal(UNKNOWN_DEBUGGEE_STATUS_WARNING_MSG)

      if not args.quiet and not user_input.prompt_user_to_continue():
        user_output.error('Delete aborted.')
        return

      debugger_rtdb_service.delete_debuggees(debuggees)

    # The status is output regardless of the requested output format. It should
    # go to stderr, and if json output is requested, that should end up on
    # stdout.
    user_output.normal(f'Deleted {len(debuggees)} debuggees.')

    if args.format.is_a_json_value():
      user_output.json_format(debuggees, pretty=args.format.is_pretty_json())
