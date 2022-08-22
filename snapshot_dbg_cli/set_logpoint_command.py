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
"""This module contains the support for the set_logpoint command.

The set_logpoint command is used to create a logpoint on a debug target
(Debuggee).
"""

import argparse

from enum import Enum

from snapshot_dbg_cli import breakpoint_utils
from snapshot_dbg_cli.exceptions import SilentlyExitError


class LogLevel(Enum):
  """ Enum that represents the logging level to use for emitted logpoints.

  For storing the log level in the breakpoint data that the agents consume, we
  use uppercase. When accepting the argument from the user in the set_logpoint
  command we use lower case.
  """

  INFO = 'INFO'
  WARNING = 'WARNING'
  ERROR = 'ERROR'

  def __str__(self):
    return str(self.value)

  @staticmethod
  def parse_arg(log_level_arg):
    # We use user friendly lowercase strings from the user.
    mappings = {
        'info': LogLevel.INFO,
        'warning': LogLevel.WARNING,
        'error': LogLevel.ERROR
    }
    enum_val = mappings.get(log_level_arg, None)

    if enum_val is None:
      raise argparse.ArgumentTypeError(
          f'Invalid log-level argument provided: {log_level_arg}')

    return enum_val


DESCRIPTION = """
Adds a debug logpoint to a debug target (debuggee).  Logpoints add logging to
your running service without changing your code or restarting your application.
When you create a logpoint, the message you specify will be added to your logs
whenever any instance of your service executes the specified line of code.

The default lifetime of a logpoint is 24 hours from creation, and the output
will go to the standard log for the programming language of the target
(java.logging for Java, logging for Python, etc.)
"""

LOCATION_HELP = """
Specify the location to add the logpoint. Locations are of the form FILE:LINE,
where FILE is the file name, or the file name preceded by enough path components
to differentiate it from other files with the same name. If the file name isn't
unique in the debuggee, the behavior is unspecified.
"""

LOG_FORMAT_STRING_HELP = """
Specify a format string which will be logged every time the logpoint location is
executed. If the string contains curly braces ('{' and '}'), any text within the
curly braces will be interpreted as a run-time expression in the debug target's
language, which will be evaluated when the logpoint is hit.

The value of the expression will then replace the {} expression in the resulting
log output. For example, if you specify the format string "a={a}, b={b}", and
the logpoint is hit when local variable a is 1 and b is 2, the resulting log
output would be "a=1, b=2".
"""

LOG_LEVEL_HELP = """
The logging level to use when producing the log message. LOG_LEVEL must be one
of: [info, warning, error]. By default 'info' is used.
"""

CONDITION_HELP = """
Specify a condition to restrict when the log output is generated. When the
logpoint is hit, the condition will be evaluated, and the log output will be
generated only if the condition is true.
"""

CREATE_SUCCESS_MESSAGE = ('Successfully created logpoint with id: '
                          '{breakpoint_id}')

CREATE_FAILED_MESSAGE = ('An unexpected error occurred while trying to add '
                         'the logpoint.')


class SetLogpointCommand:
  """This class implements the set_logpoint command.

  The register() method is called by the CLI startup code to install the
  set_logpoint command information, and the cmd() function will be invoked if
  the set_logpoint command was specified by the user.
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
        'set_logpoint', description=DESCRIPTION, parents=parent_parsers)
    parser.set_defaults(func=self.cmd)

    def location(location_arg):
      loc = breakpoint_utils.parse_and_validate_location(location_arg)

      if loc is None:
        raise argparse.ArgumentTypeError(breakpoint_utils.LOCATION_ERROR_MSG)

      return loc

    parser.add_argument('location', help=LOCATION_HELP, type=location)
    parser.add_argument(
        'log_format_string',
        help=LOG_FORMAT_STRING_HELP,
        type=SetLogpointCommand.parse_log_format_string_arg)
    parser.add_argument(
        '--log-level',
        help=LOG_LEVEL_HELP,
        default='info',
        type=LogLevel.parse_arg)
    parser.add_argument('--condition', help=CONDITION_HELP)
    self.args_parser = parser

  def cmd(self, args, cli_services):
    user_output = cli_services.user_output
    debugger_rtdb_service = cli_services.get_snapshot_debugger_rtdb_service()

    debugger_rtdb_service.validate_debuggee_id(args.debuggee_id)

    logpoint_data = {
        'action': 'LOG',
        'logMessageFormat': args.log_format_string['log_message_format'],
        'location': args.location,
        'logLevel': str(args.log_level),
        'userEmail': cli_services.account
    }

    if len(args.log_format_string['expressions']) > 0:
      logpoint_data['expressions'] = args.log_format_string['expressions']

    # This is a magic Server Value, createTime will get set to the time since
    # UNIX epoch, in milliseconds.
    # https://firebase.google.com/docs/reference/rest/database#section-server-values
    logpoint_data['createTimeUnixMsec'] = {'.sv': 'timestamp'}

    if args.condition:
      logpoint_data['condition'] = args.condition

    breakpoint_id = debugger_rtdb_service.get_new_breakpoint_id(
        args.debuggee_id)

    logpoint_data['id'] = breakpoint_id

    bp = debugger_rtdb_service.set_breakpoint(args.debuggee_id, logpoint_data)

    if bp is None:
      user_output.error(CREATE_FAILED_MESSAGE)
      raise SilentlyExitError

    if args.format.is_a_json_value():
      user_output.json_format(bp, pretty=args.format.is_pretty_json())
    else:
      user_output.normal(
          CREATE_SUCCESS_MESSAGE.format(breakpoint_id=breakpoint_id))

  @staticmethod
  def parse_log_format_string_arg(format_string):
    """Extracts {expression} substrings into a separate array.

    Each substring of the form {expression} will be extracted into an array, and
    each {expression} substring will be replaced with $N, where N is the index
    of the extraced expression in the array. Any '$' sequence outside an
    expression will be escaped with '$$'.

    For example, given the input:
      'a={a}, b={b}'
     The return value would be:
      ('a=$0, b=$1', ['a', 'b'])

    Args:
      format_string: The string to process.
    Returns:
      {log_message_format: string, expressions: [string]) - The new format
        string and the array of expressions.
    Raises:
      argparse.ArgumentTypeError: If the string has unbalanced braces.
    """
    expressions = []
    log_format = ''
    current_expression = ''
    brace_count = 0
    need_separator = False
    for c in format_string:
      if need_separator and c.isdigit():
        log_format += ' '
      need_separator = False
      if c == '{':
        if brace_count:
          # Nested braces
          current_expression += c
        else:
          # New expression
          current_expression = ''
        brace_count += 1
      elif not brace_count:
        if c == '}':
          # Unbalanced left brace.
          raise argparse.ArgumentTypeError(
              'There are too many "}" characters in the log format string')
        elif c == '$':
          # Escape '$'
          log_format += '$$'
        else:
          # Not in or starting an expression.
          log_format += c
      else:
        # Currently reading an expression.
        if c != '}':
          current_expression += c
          continue
        brace_count -= 1
        if brace_count == 0:
          # Finish processing the expression
          if current_expression in expressions:
            i = expressions.index(current_expression)
          else:
            i = len(expressions)
            expressions.append(current_expression)
          log_format += f'${i}'
          # If the next character is a digit, we need an extra space to prevent
          # the agent from combining the positional argument with the subsequent
          # digits.
          need_separator = True
        else:
          # Closing a nested brace
          current_expression += c

    if brace_count:
      # Unbalanced left brace.
      raise argparse.ArgumentTypeError(
          'There are too many "{" characters in the log format string')

    return {'log_message_format': log_format, 'expressions': expressions}
