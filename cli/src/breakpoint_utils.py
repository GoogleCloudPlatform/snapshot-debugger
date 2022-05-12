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
import time

from exceptions import SilentlyExitError

# Regex that can be used to validate a user inputted location which should be in
# the format file:line.
LOCATION_REGEX = '^[^:]+:[1-9][0-9]*$'

# Impose some 'reasonable' max, here we choose 2^31-1, won't cause any overflows
# anywhere and is more than enough for a file's line number.
MAX_LINE_NUMBER = 2147483647

LOCATION_ERROR_MSG = f"""
Location must be in the format file:line, with the maximum line number being
{MAX_LINE_NUMBER}
"""


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


# Per
# https://firebase.googleblog.com/2014/04/best-practices-arrays-in-firebase.html
# "If all of the keys are integers, and more than half of the keys are between
# 0 and the maximum key in the object have non-empty values, then Firebase
# will render it as an array."
#
# As the breakpoint IDs will used as keys in the RTDB we do not want the above
# behaviour, as we always want maps to be returned instead of arrays.
def get_new_breakpoint_id(user_output, firebase_rtdb_service, debuggee_id):
  time_secs = int(time.time())
  breakpoint_id = None
  found = False

  for i in range(0, 10):
    breakpoint_id = f'b-{time_secs + i}'
    active_path = f'breakpoints/{debuggee_id}/active/{breakpoint_id}'
    final_path = f'breakpoints/{debuggee_id}/final/{breakpoint_id}'

    bp_active = firebase_rtdb_service.get(active_path, shallow=True)
    bp_final = firebase_rtdb_service.get(final_path, shallow=True)

    # This case means there are no breakpoints at all.
    if bp_active is None and bp_final is None:
      found = True
      break

  if not found:
    user_output.error(
        'ERROR Failed to determine a new breakpoint ID, please try again')
    raise SilentlyExitError

  return breakpoint_id


def convert_unix_msec_to_rfc3339(unix_msec):
  """Converts a Unix timestamp represented in milliseconds since the epoch to an

  RFC3339 string representation.

  Args:
    unix_msec: The Unix timestamp, represented in milliseconds since the epoch.

  Returns:
    An RFC3339 encoded timestamp string in format: "%Y-%m-%dT%H:%M:%S.%fZ".
  """
  seconds = unix_msec / 1000
  msec = unix_msec % 1000
  timestamp = seconds + msec / float(1000)
  dt = datetime.datetime.utcfromtimestamp(timestamp)
  return dt.strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'


def set_converted_timestamps(bp):
  conversions = [['createTime', 'createTimeUnixMsec'],
                 ['finalTime', 'finalTimeUnixMsec']]

  for c in conversions:
    if c[0] not in bp and c[1] in bp:
      bp[c[0]] = convert_unix_msec_to_rfc3339(bp[c[1]])

  return bp


# Returns None if there's an issue
def normalize_breakpoint(bp, bpid=None):
  if bp is None:
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


def get_breakpoints_by_state(firebase_rtdb_service, bp_state, debuggee_id,
                             action, user_email):
  path = f'breakpoints/{debuggee_id}/{bp_state}'
  breakpoints = firebase_rtdb_service.get(path) or {}

  # We want the breakpoints to be in list form, they will be in dict form after
  # the firebase call.

  breakpoints = [
      bp for bpid, bp in breakpoints.items()
      if normalize_breakpoint(bp, bpid) and bp['action'] == action and
      (user_email is None or bp['userEmail'] == user_email)
  ]

  return breakpoints


def delete_breakpoints(firebase_rtdb_service, debuggee_id, breakpoints):
  for b in breakpoints:
    active_path = f"breakpoints/{debuggee_id}/active/{b['id']}"
    final_path = f"breakpoints/{debuggee_id}/final/{b['id']}"
    snapshot_path = f"breakpoints/{debuggee_id}/snapshot/{b['id']}"

    firebase_rtdb_service.delete(active_path)
    firebase_rtdb_service.delete(final_path)

    if b['action'] == 'CAPTURE':
      firebase_rtdb_service.delete(snapshot_path)


def get_breakpoint(firebase_rtdb_service, debuggee_id, breakpoint_id):
  active_path = f'breakpoints/{debuggee_id}/active/{breakpoint_id}'
  final_path = f'breakpoints/{debuggee_id}/final/{breakpoint_id}'

  bp = firebase_rtdb_service.get(active_path)

  # If it wasn't active, the response will be None, so then try the final
  # path.
  if bp is None:
    bp = firebase_rtdb_service.get(final_path)

  return normalize_breakpoint(bp, breakpoint_id)


def get_snapshot(firebase_rtdb_service, debuggee_id, snapshot_id):
  active_path = f'breakpoints/{debuggee_id}/active/{snapshot_id}'
  snapshot_path = f'breakpoints/{debuggee_id}/snapshot/{snapshot_id}'

  bp = firebase_rtdb_service.get(active_path)

  # If it wasn't active, the response will be None, so then try the full
  # snapshot path.
  if bp is None:
    bp = firebase_rtdb_service.get(snapshot_path)

  return normalize_breakpoint(bp, snapshot_id)


def get_active_breakpoints(firebase_rtdb_service, debuggee_id, action,
                           user_email):
  return get_breakpoints_by_state(firebase_rtdb_service, 'active', debuggee_id,
                                  action, user_email)


def get_final_breakpoints(firebase_rtdb_service, debuggee_id, action,
                          user_email):
  return get_breakpoints_by_state(firebase_rtdb_service, 'final', debuggee_id,
                                  action, user_email)


def get_breakpoints(firebase_rtdb_service,
                    debuggee_id,
                    include_inactive,
                    action,
                    user_email=None):
  breakpoints = get_active_breakpoints(firebase_rtdb_service, debuggee_id,
                                       action, user_email)

  if include_inactive:
    breakpoints += get_final_breakpoints(firebase_rtdb_service, debuggee_id,
                                         action, user_email)

  return breakpoints


def get_snapshots(firebase_rtdb_service,
                  debuggee_id,
                  include_inactive,
                  user_email=None):
  return get_breakpoints(firebase_rtdb_service, debuggee_id, include_inactive,
                         'CAPTURE', user_email)
