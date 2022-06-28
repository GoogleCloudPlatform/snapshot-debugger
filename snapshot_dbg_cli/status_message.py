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
"""This module provides a breakpoint StatusMessage utility class.
"""

import string


class StatusMessage:
  """This class implements the Snapshot Debugger StatusMessage parser.

  It accepts a Snapshot Debugger Breakpoint message which main contain a
  StatusMessage in a 'status' field. StatusMessages may appear in a Breakpoint,
  a Debuggee or a Variable. It will parse the message and provide a human
  readable version.

  Attributes:
    parsed_message: Human readable version of the message. It will be None if
      there was no StatusMessage present or it could not be parsed for some
      reason.
    is_error: Flag indicating of the StatusMessage represents an error or not.
      It will be None if there was no StatusMessage present.
    refers_to: If not None, indicates what the message refers to. Expected
      values would be one of the following:
        BREAKPOINT_CONDITION
        BREAKPOINT_EXPRESSION
        VARIABLE_NAME
        VARIABLE_VALUE
        BREAKPOINT_SOURCE_LOCATION
        BREAKPOINT_AGE
        UNSPECIFIED
  """

  def __init__(self, parent):
    self.parsed_message = None
    self.is_error = None
    self.refers_to = None

    if 'status' not in parent:
      return

    status = parent['status']
    description = status.get('description', {})

    self.parsed_message = self._parse_message(description)
    self.is_error = status.get('isError', False)
    self.refers_to = status.get('refersTo', None)

  def _parse_message(self, description):
    if 'format' not in description:
      return None

    # Get the formatting string such as "Failed to load '$0' which
    # helps debug $1"
    format_string = description['format']

    # Get the number of parameters to replace '$' prefixed vars.
    parameters = description.get('parameters', [])
    total_parameters = len(parameters)

    dollar_index = None
    output_string = ''

    # While we have remaining '$' place holders keep traversing the format
    # string.
    dollar_index = format_string.find('$')
    while dollar_index > -1:
      # Add the first portion of the format string to the output.
      output_string += format_string[:dollar_index]
      if len(format_string) > (dollar_index + 1):
        # Get the parameters index value in the parameters list or a '$' if
        # the value is escaped.
        next_char = format_string[(dollar_index + 1):(dollar_index + 2)]

        if next_char == '$':
          # The next character is a '$' this is an escaped character, be sure
          # to maintain the next '$'.
          output_string += '$'
          format_string = format_string[(dollar_index + 2):]
        elif next_char in string.digits and int(next_char) < total_parameters:
          # Get the proper parameter for the index.
          output_string += parameters[int(next_char)]
          format_string = format_string[(dollar_index + 2):]
        else:
          # FormatMessage with too many arguments, unclear what to do from
          # the spec, will just keep it verbatim.
          output_string += '$'
          format_string = format_string[(dollar_index + 1):]
      else:
        # A '$' was the last value add it back.
        output_string += '$'
        format_string = ''

      dollar_index = format_string.find('$')

    # Add the remainder of the format string to the returned value.
    output_string += format_string
    return output_string
