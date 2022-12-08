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
