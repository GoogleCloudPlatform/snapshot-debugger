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
"""This module contains the support for the get_snapshot command.

The get_snapshot command is used to create a snapshot on a debug target
(Debuggee).
"""

from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli import breakpoint_utils
from snapshot_dbg_cli.snapshot_parser import SnapshotParser

DESCRIPTION = """
Used to retrieve a debug snapshot from a debug target (debuggee). If the
snapshot has completed, the output includes details on the stack trace and local
variables. By default the expressions and local variables for the first stack
frame are displayed to 3 levels deep. To see the local variables from another
stack frame specify the '--frame-index' option. When the 'json' or 'pretty-json'
format outputs are selected, the entire snapshot data is emitted in a compact
form which is intended to be machine-readable rather than human-readable.
"""

ID_HELP = 'Specify the snapshot ID to retrieve.'

FRAME_INDEX_HELP = """
Set the stack frame to display local variables from, the default is 0, which is
the top of the stack.
"""

MAX_LEVEL_HELP = """
Set the maximum variable expansion to use when the '--format' option is
'default'. The default value is {0}.
"""

DEFAULT_MAX_LEVEL = 3


class GetSnapshotCommand:
  """This class implements the get_snapshot command.

  The register() method is called by the CLI startup code to install the
  get_snapshot command information, and the cmd() function will be invoked if
  the get_snapshot command was specified by the user.
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
        'get_snapshot', description=DESCRIPTION, parents=parent_parsers)
    parser.add_argument('snapshot_id', metavar='ID', help=ID_HELP)
    parser.add_argument(
        '--frame-index', type=int, help=FRAME_INDEX_HELP, default=0)
    parser.add_argument(
        '--max-level',
        type=int,
        help=MAX_LEVEL_HELP.format(DEFAULT_MAX_LEVEL),
        default=DEFAULT_MAX_LEVEL)
    parser.set_defaults(func=self.cmd)

  def display_header(self, title):
    self.user_output.normal('')
    self.user_output.normal('-' * 80)
    self.user_output.normal(f'| {title}')
    self.user_output.normal('-' * 80)
    self.user_output.normal('')

  def display_summary(self, bp, status_message):
    # To note we're being defensive here with respect to the condition and
    # expressions fields so that their absence and them being present but empty
    # are treated to the same way.
    location = breakpoint_utils.transform_location_to_file_line(bp['location'])
    condition = bp.get('condition', '')
    condition = condition if condition != '' else 'No condition set'
    expressions = bp.get('expressions', [])
    expressions = expressions if len(expressions) > 0 else 'No expressions set'
    create_time = bp['createTime']
    final_time = bp.get('finalTime', '')

    status = 'Complete' if bp['isFinalState'] else 'Active'

    if status_message.parsed_message is not None:
      if (status_message.is_error and
          status_message.refers_to != 'BREAKPOINT_AGE'):
        status = (f'ERROR: {status_message.parsed_message} '
                  f'(refers to: {status_message.refers_to})')
      else:
        status = status_message.parsed_message

    self.display_header('Summary')
    self.user_output.normal(f'Location:    {location}')
    self.user_output.normal(f'Condition:   {condition}')
    self.user_output.normal(f'Expressions: {expressions}')
    self.user_output.normal(f'Status:      {status}')
    self.user_output.normal(f'Create Time: {create_time}')
    self.user_output.normal(f'Final Time:  {final_time}')

  def display_expressions(self, parsed_expressions):
    self.display_header('Evaluated Expressions')

    self.user_output.normal(
        self.data_formatter.to_json_string(parsed_expressions, pretty=True)
        if parsed_expressions else 'There were no expressions specified.')

  def display_locals(self, parsed_locals, stack_frame_index):
    self.display_header(
        f'Local Variables For Stack Frame Index {stack_frame_index}:')

    self.user_output.normal(
        self.data_formatter.to_json_string(parsed_locals, pretty=True)
        if parsed_locals else 'There are no local variables.')

  def display_call_stack(self, parsed_call_stack):
    self.display_header('CallStack:')
    headers = ['Function', 'Location']
    self.user_output.tabular(headers, parsed_call_stack)

  def cmd(self, args, cli_services):
    self.data_formatter = cli_services.data_formatter
    self.user_output = cli_services.user_output
    debugger_rtdb_service = cli_services.get_snapshot_debugger_rtdb_service()

    debugger_rtdb_service.validate_debuggee_id(args.debuggee_id)
    snapshot = debugger_rtdb_service.get_snapshot_detailed(
        args.debuggee_id, args.snapshot_id)

    if snapshot is None or snapshot['action'] != 'CAPTURE':
      self.user_output.error(f'Snapshot ID not found: {args.snapshot_id}')
      raise SilentlyExitError

    if args.format.is_a_json_value():
      self.user_output.json_format(
          snapshot, pretty=args.format.is_pretty_json())
      return

    snapshot_parser = SnapshotParser(snapshot, args.max_level)

    # Don't display the summary data if the user is requesting a specific stack
    # frame.
    if args.frame_index == 0:
      self.display_summary(snapshot, snapshot_parser.status_message)

    # Only proceed if there may be captured snapshot data to present
    if not snapshot['isFinalState'] or snapshot_parser.status_message.is_error:
      return

    if args.frame_index > 0 and args.frame_index >= len(
        snapshot_parser.stack_frames):
      self.user_output.error(
          f'Stack frame index {args.frame_index} too big, there are only '
          f'{len(snapshot_parser.stack_frames)} stack frames.')
      raise SilentlyExitError

    # When the top stack frame is selected, we display the expressions and call
    # stack, otherwise we only display the locals for the given frame.
    if args.frame_index == 0:
      self.display_expressions(snapshot_parser.parse_expressions())
      self.display_locals(
          snapshot_parser.parse_locals(args.frame_index), args.frame_index)
      self.display_call_stack(snapshot_parser.parse_call_stack())
    else:
      self.display_locals(
          snapshot_parser.parse_locals(args.frame_index), args.frame_index)
