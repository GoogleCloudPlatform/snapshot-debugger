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
  """

  def __init__(self, is_debug_enabled):
    self._is_debug_enabled = is_debug_enabled

  # Debug messages that are output when the user enables the --debug option.
  # For instance this should be used for outputting REST calls and their
  # responses, etc.
  def debug(self, *args, **kwargs):
    if self._is_debug_enabled:
      print(*args, **kwargs)

  # Normal user output when providing output information from a successful
  # command.
  def normal(self, *args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

  # Meant for anything 'exceptional', that is not part of the normal user output
  # when the commands succeeds.
  def error(self, *args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
