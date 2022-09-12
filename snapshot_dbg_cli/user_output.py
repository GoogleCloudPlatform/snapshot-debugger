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
"""This module provides a simple user output utility class.

This class should be used by the CLI anytime it needs to output any messages to
the user.
"""

import sys


class UserOutput:
  """This class handles outputting messages to the user.

  This class should be used by the CLI anytime it needs to output any messages
  to the user. Depending on the message type, it will be output to the correct
  location, eg stdout or stderr. For debug messages, they will be suppressed
  unless debugging has been enabled.

  All non json output goes to stderr, and everything else, including debug level
  messages go to stderr. This is done to keep things simple and allows for the
  case where the CLI is being driven prgramatically, then only formatted JSON
  ends up in stdout.
  """

  def __init__(self, is_debug_enabled, data_formatter):
    """Initializes the UserOuput instance.

    Args:
      is_debug_enabled: Flag that when true indicates debug messages should be
        emitted. The are suppressed otherwise.
    """
    self._is_debug_enabled = is_debug_enabled
    self.data_formatter = data_formatter

  def debug(self, *args, **kwargs):
    """Outputs a debug message.

    This method is meant for any debug messages that will only be emitted when
    the --debug options is has been specified on the CLI input line.
    The output goes to stderr (as stdout is reserved for JSON output only).

    Args:
      args: Variable length unnamed argument list which will be passed to print.
      kwargs: Variable length named argument list which will be passed to print.
    """
    if self._is_debug_enabled:
      self.local_print(*args, file=sys.stderr, **kwargs)

  def normal(self, *args, **kwargs):
    """Outputs a normal user message.

    This method is meant for any normal user output when providing information
    from a successful command. The output goes to stderr (as stdout is reserved
    for JSON output only).

    Args:
      args: Variable length unnamed argument list which will be passed to print.
      kwargs: Variable length named argument list which will be passed to print.
    """
    self.local_print(*args, file=sys.stderr, **kwargs)

  def error(self, *args, **kwargs):
    """Outputs an error message to the user.

    This method is meant for anything 'exceptional', that is not part of the
    normal user output when the commands succeeds. The output goes to stderr.

    Args:
      args: Variable length unnamed argument list which will be passed to print.
      kwargs: Variable length named argument list which will be passed to print.
    """
    self.local_print(*args, file=sys.stderr, **kwargs)

  def json_format(self, data, pretty):
    """Transforms the data to a JSON string and prints it to stdout.

    Args:
      data: The data to convert to a JSON string and printed to stdout. It is
        expected to be a Python object representation of the data.
      pretty: Boolean flag that when True will be cause the json string to be
        human readable, otherwise it will be in a compact representation.
    """
    json_string = self.data_formatter.to_json_string(data, pretty)
    self.local_print(json_string, file=sys.stdout)

  def tabular(self, headers, values):
    """Outputs the data in a human friendly tabular form.

    Args:
      headers: Array of strings to be used as the top row of the table,
        representing the column names.
      values: Array of tuples containing one row of output (1 value for each
        column). Each tuple must have the same number of elements, which much
        also match the length of the headers tuple.
    """
    table = self.data_formatter.build_table(headers, values)
    self.normal(table)

  def local_print(self, *args, **kwargs):
    print(*args, **kwargs)
