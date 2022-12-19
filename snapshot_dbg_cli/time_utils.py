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
"""This module provides utilities related to timestamps.
"""

import datetime
import time


def get_current_time_unix_msec():
  return int(time.time() * 1000)


def convert_unix_msec_to_rfc3339(unix_msec):
  """Converts a Unix timestamp represented in milliseconds since the epoch to an

  RFC3339 string representation.

  Args:
    unix_msec: The Unix timestamp, represented in milliseconds since the epoch.

  Returns:
    An RFC3339 encoded timestamp string in format: "%Y-%m-%dT%H:%M:%SZ".
  """
  try:
    seconds = unix_msec / 1000
    timestamp = seconds
    dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
  except (OverflowError, OSError, TypeError, ValueError):
    # By using 0, we'll still get the expected formatted string, and the value
    # will be '1970-01-01...', which visually will be recognizable as beginning
    # of epoch and that the value was not known.
    return convert_unix_msec_to_rfc3339(0)


def set_converted_timestamps(data, field_mappings):
  """Converts raw unix timestamp fields to human readable versions.

  If the destination field already exists it won't be overwritten.

  Example:
  data = {
    fooTimeUnixMsec: 1649962215000
    barTimeUnixMsec: 1649962216000
  }

  field_mappings = [
    ('fooTime', 'fooTimeUnixMsec'),
    ('barTIme, 'barTimeUnixMsec')
  ]

  set_converted_timestamps(data, field_mappings)
  data = {
    fooTimeUnixMsec: 1649962215000
    fooTime: '2022-04-14T18:50:15Z'
    barTimeUnixMsec = 1649962216000
    barTime: '2022-04-14T18:50:16Z'
  }


  Args:
    data: The container dict, expected to represent either a breakpoint a
      debuggee.
    field_mappings: [(str, str)] List of field mappings. For each entry the
      first member is the destination field to be set with a human readable
      timestamp. The second member is the source field and should map to a unix
      timestamp in data.

  Returns:
    The data dict that was passed in.
  """

  for m in field_mappings:
    if m[0] not in data and m[1] in data:
      data[m[0]] = convert_unix_msec_to_rfc3339(
          data[m[1]]) if data[m[1]] != 0 else 'not set'

  return data
