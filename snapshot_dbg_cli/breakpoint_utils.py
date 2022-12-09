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
"""This module provides a variety of utilities related to breakpoint processing.

These utilities are useful in multiple snapshot and logpoint commands.
"""

import re
import snapshot_dbg_cli.time_utils

from snapshot_dbg_cli.status_message import StatusMessage

# Regex that can be used to validate a user inputted location which should be in
# the format file:line.
LOCATION_REGEX = '^[^:]+:[1-9][0-9]*$'

# Impose some 'reasonable' max, here we choose 2^31-1, won't cause any overflows
# anywhere and is more than enough for a file's line number.
MAX_LINE_NUMBER = 2147483647

LOCATION_ERROR_MSG = ('Location must be in the format file:line, with the '
                      f'maximum line number being {MAX_LINE_NUMBER}')


# Returns dict containing {'path': string, 'line:' int} on success.
# Returns None on failure (ie invalid input).
def parse_and_validate_location(file_line):
  match = re.search(LOCATION_REGEX, file_line)

  if match is None:
    return None

  parsed_value = file_line.split(':')

  line = int(parsed_value[1])

  if line > MAX_LINE_NUMBER:
    return None

  return {'path': parsed_value[0], 'line': line}


def transform_location_to_file_line(location):
  """Returns a location in the format of 'file:line'.

  Parameters:
    location (dict): Location in dict form with 'path' and 'line' fields.

  Returns:
    location (string): The location in the format 'file:line'
  """
  if 'path' not in location or 'line' not in location:
    return None

  return f"{location['path']}:{location['line']}"


def set_converted_timestamps(bp):
  field_mappings = [('createTime', 'createTimeUnixMsec'),
                    ('finalTime', 'finalTimeUnixMsec')]

  return snapshot_dbg_cli.time_utils.set_converted_timestamps(
      bp, field_mappings)


# Returns None if there's an issue
def normalize_breakpoint(bp, bpid=None):
  """Validates and normalizes a breakpoint.

  This method ensures all required and expected fields are set. If any required
  field is not set, and cannot be filled in, None will be returned.

  If a breakpoint is returned, the following fields are guaranteed to
  be populated:

    id
    location
      path
      line
    action
    isFinalState
    createTime
    createTimeUnixMsec
    finalTime
    finalTimeUnixMsec
    userEmail

  If the 'action' field is 'CAPTURE', the breakpoint represents a snapshot, and
  if it's 'LOG', the breakpoint represents a logpoint.

  Additionally, if the breakpoint represents a logpoint (action is 'LOG'), the
  following fields will be present:

    logMessageFormat        - Form of 'a: $0, b: $1', used by the agents
    logMessageFormatString  - Form of 'a: {a}, b: {b}', friendly user version
    logLevel

  Returns:
    The normalized breakpoint on success, None on failure.
  """
  if not isinstance(bp, dict):
    return None

  if 'id' not in bp and bpid is not None:
    bp['id'] = bpid

  required_fields = ['id', 'location']
  for f in required_fields:
    if f not in bp:
      return None

  required_location_fields = ['path', 'line']
  for f in required_location_fields:
    if f not in bp['location']:
      return None

  if 'action' not in bp:
    bp['action'] = 'CAPTURE'

  if 'isFinalState' not in bp:
    bp['isFinalState'] = False

  if 'createTimeUnixMsec' not in bp:
    # Assuming everything is working correctly the createTimeUnixMsec value
    # should be present, if not initialize it to 0 so it's set to something,
    # but it's clear the time was not actually known.
    bp['createTimeUnixMsec'] = 0

  if 'finalTimeUnixMsec' not in bp and bp['isFinalState']:
    bp['finalTimeUnixMsec'] = 0

  if 'userEmail' not in bp:
    bp['userEmail'] = 'unknown'

  set_converted_timestamps(bp)

  if bp['action'] == 'LOG':
    if 'logLevel' not in bp:
      bp['logLevel'] = 'INFO'

    if 'logMessageFormat' not in bp:
      bp['logMessageFormat'] = ''

    bp['logMessageFormatString'] = merge_log_expressions(
        bp['logMessageFormat'], bp.get('expressions', []))

  return bp


def split_log_expressions(format_string):
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
    string, [string]) - The new format string and the array of expressions.
  Raises:
    Error: If the string has unbalanced braces.
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
        raise ValueError(
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
    raise ValueError(
        'There are too many "{" characters in the log format string')

  return log_format, expressions


def merge_log_expressions(log_format, expressions):
  """Replaces each $N substring with the corresponding {expression}.

  This function is intended for reconstructing an input expression string that
  has been split using split_log_expressions.

  Args:
    log_format: A string containing 0 or more $N substrings, where N is any
      valid index into the expressions array. Each such substring will be
      replaced by '{expression}', where "expression" is expressions[N].
    expressions: The expressions to substitute into the format string.
  Returns:
    The combined string.
  """

  def get_expression(m):
    try:
      index = int(m.group(0)[1:])
      return f'{{{expressions[index]}}}'
    except IndexError:
      return m.group(0)

  parts = log_format.split('$$')
  return '$'.join(re.sub(r'\$\d+', get_expression, part) for part in parts)


def get_logpoint_short_status(logpoint):
  if not logpoint['isFinalState']:
    return 'ACTIVE'

  status_message = StatusMessage(logpoint)

  # This would be unexpected, as logpoints expire, which is classified as an
  # error.
  if not status_message.is_error:
    return 'COMPLETED'

  refers_to = status_message.refers_to

  if refers_to is None or len(refers_to) == 0:
    refers_to = 'BREAKPOINT_FAILED'

  if refers_to == 'BREAKPOINT_AGE':
    return 'EXPIRED'

  # The refers_to is expected to always starts with 'BREAKPOINT_', so here we
  # strip it off to shorten the output.
  short_refers_to = refers_to.replace('BREAKPOINT_', '')

  message = status_message.parsed_message

  if message is None or len(message) == 0:
    message = 'Unknown failure reason'

  return f'{short_refers_to}: {message}'
