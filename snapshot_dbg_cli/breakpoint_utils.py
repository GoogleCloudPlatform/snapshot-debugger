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

import datetime
import re

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


# Returns the id to use when creating a new breakpoint.
# To note, we use the format 'b_<unix epoc seconds>'
#
# To note, this ensures the ID cannot be interpreted as an integer. This is
# specifically done for the following reason:


def convert_unix_msec_to_rfc3339(unix_msec):
  """Converts a Unix timestamp represented in milliseconds since the epoch to an

  RFC3339 string representation.

  Args:
    unix_msec: The Unix timestamp, represented in milliseconds since the epoch.

  Returns:
    An RFC3339 encoded timestamp string in format: "%Y-%m-%dT%H:%M:%S.%fZ".
  """
  try:
    seconds = unix_msec / 1000
    msec = unix_msec % 1000
    timestamp = seconds
    dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    return dt.strftime(f'%Y-%m-%dT%H:%M:%S.{msec:03}000') + 'Z'
  except (OverflowError, OSError, TypeError, ValueError):
    # By using 0, we'll still get the expected formatted string, and the value
    # will be '1970-01-01...', which visually will be recognizable as beginning
    # of epoch and that the value was not known.
    return convert_unix_msec_to_rfc3339(0)


def set_converted_timestamps(bp):
  conversions = [['createTime', 'createTimeUnixMsec'],
                 ['finalTime', 'finalTimeUnixMsec']]

  for c in conversions:
    if c[0] not in bp and c[1] in bp:
      bp[c[0]] = convert_unix_msec_to_rfc3339(bp[c[1]])

  return bp


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

  return bp
