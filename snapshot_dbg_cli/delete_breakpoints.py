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
"""This module provides common functionality for delete breakpoints commands.

Provides the command functionality for the delete_snapshots and
delete_breakpoints commands.
"""

from snapshot_dbg_cli.exceptions import SilentlyExitError


def run_cmd(action, args, cli_services, summary_headers, summary_transform):
  """Contains the common logic to run a delete snapshots or logpoints command.

  Args:
    action: A string matching the action from breakpoints, either 'CAPTURE' (for
      snapshots) or 'LOG' (for logpoints).
    args: The argsparse args for the delete command.
    cli_services: The CliServices instance to use for running the command.
    summary_headers: The headers for the breakpoints table the delete command
      emits for the user.
  Returns:
    string, [string]) - The new format string and the array of expressions.
  Raises:
    Error: If the string has unbalanced braces.
  """
  # This two variables provide customization for emitted user messages.
  breakpoint_type = 'snapshot' if action == 'CAPTURE' else 'logpoint'
  breakpoint_type_capitalized = breakpoint_type[0].upper() + breakpoint_type[1:]

  user_input = cli_services.user_input
  user_output = cli_services.user_output
  debugger_rtdb_service = cli_services.get_snapshot_debugger_rtdb_service()

  debugger_rtdb_service.validate_debuggee_id(args.debuggee_id)

  # This will be a list, if no IDs were specified it will be empty. If any IDs
  # are specified those are the only ones that will be deleted.
  breakpoint_ids = args.ID

  user_email = None if args.all_users is True else cli_services.account

  breakpoints = []

  if breakpoint_ids:
    ids_not_found = []

    for bp_id in breakpoint_ids:
      bp = debugger_rtdb_service.get_breakpoint(args.debuggee_id, bp_id)
      if bp is None or bp['action'] != action:
        ids_not_found.append(bp_id)
      else:
        breakpoints.append(bp)

    if ids_not_found:
      user_output.error(f'{breakpoint_type_capitalized} ID not found: '
                        f"{', '.join(ids_not_found)}")
      raise SilentlyExitError
  else:
    if action == 'CAPTURE':
      breakpoints = debugger_rtdb_service.get_snapshots(args.debuggee_id,
                                                        args.include_inactive,
                                                        user_email)
    else:
      breakpoints = debugger_rtdb_service.get_logpoints(args.debuggee_id,
                                                        args.include_inactive,
                                                        user_email)

  if breakpoints:
    user_output.normal(
        f'This command will delete the following {breakpoint_type}s:\n')
    values = list(map(summary_transform, breakpoints))
    user_output.tabular(summary_headers, values)
    user_output.normal('\n')

    if not args.quiet and not user_input.prompt_user_to_continue():
      user_output.error('Delete aborted.')
      return

    debugger_rtdb_service.delete_breakpoints(args.debuggee_id, breakpoints)

  # The status is output regardless of the requested output format. It should
  # go to stderr, and if json output is requested, that should end up on
  # stdout.
  user_output.normal(f'Deleted {len(breakpoints)} {breakpoint_type}s.')

  if args.format.is_a_json_value():
    user_output.json_format(breakpoints, pretty=args.format.is_pretty_json())
