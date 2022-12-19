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
"""This module provides a variety of utilities related to debuggees processing.
"""

import snapshot_dbg_cli.time_utils

MSEC_PER_HOUR = 60 * 60 * 1000
DEBUGGEE_ACTIVE_THRESHOLD_MSEC = 6 * MSEC_PER_HOUR
DEBUGGEE_STALE_THRESHOLD_MSEC = 7 * 24 * MSEC_PER_HOUR


def get_display_name(labels):
  module = labels.get('module', 'default')
  version = labels.get('version', '')

  return f'{module} - {version}'


def set_converted_timestamps(debuggee):
  field_mappings = [('registrationTime', 'registrationTimeUnixMsec'),
                    ('lastUpdateTime', 'lastUpdateTimeUnixMsec')]

  return snapshot_dbg_cli.time_utils.set_converted_timestamps(
      debuggee, field_mappings)


def get_debuggee_status(debuggee):
  if not debuggee['activeDebuggeeEnabled']:
    return 'UNKNOWN'

  if debuggee['isActive']:
    return 'ACTIVE'

  if not debuggee['isStale']:
    return 'INACTIVE'

  return 'STALE'


def normalize_debuggee(debuggee, current_time_unix_msec):
  """Validates and normalizes a debuggee.

  This method ensures all required and expected fields are set. If any required
  field is not set, and cannot be filled in, None will be returned.

  If a debuggee is returned, the following fields are guaranteed to
  be populated:

    id
    displayName
    description
    activeDebuggeeEnabled - Indicates the agent this debuggee represents
                            supports the 'active debuggee' feature, and so the
                            isActive and isStale fields are valid and accurate
                            to rely on.  Early versions of the agents did not
                            populate the lastUpdateTimeUnixMsec field.
    isActive      - Indicates it has been recently active ~6hours. By default
                    this will be false if activeDebuggeeEnabled is false.
    isStale       - Indicates it has not been active for a long period
                    (~7days).  By default this will be false if
                    activeDebuggeeEnabled is false.
    lastUpdateTime
    lastUpdateTimeUnixMsec
    registrationTime
    registrationTimeUnixMsec

  Returns:
    The normalized debuggee on success, None on failure.
  """
  if not isinstance(debuggee, dict):
    return None

  required_fields = ['id']
  for f in required_fields:
    if f not in debuggee:
      return None

  if 'description' not in debuggee:
    debuggee['description'] = ''

  debuggee['displayName'] = get_display_name(debuggee.get('labels', {}))

  debuggee['activeDebuggeeEnabled'] = 'lastUpdateTimeUnixMsec' in debuggee

  if 'registrationTimeUnixMsec' not in debuggee:
    # Debuggees created by older agents won't have this field present,
    # initialize it to 0 so it's set to something, but it's clear the
    # time was not actually known.
    debuggee['registrationTimeUnixMsec'] = 0

  if 'lastUpdateTimeUnixMsec' not in debuggee:
    # Debuggees created by older agents won't have this field present,
    # initialize it to 0 so it's set to something, but it's clear the
    # time was not actually known.
    debuggee['lastUpdateTimeUnixMsec'] = 0

  set_converted_timestamps(debuggee)

  debuggee['isActive'] = (
      current_time_unix_msec -
      debuggee['lastUpdateTimeUnixMsec']) <= DEBUGGEE_ACTIVE_THRESHOLD_MSEC
  debuggee['isStale'] = (
      current_time_unix_msec -
      debuggee['lastUpdateTimeUnixMsec']) > DEBUGGEE_STALE_THRESHOLD_MSEC

  return debuggee


def sort_debuggees(debuggees):
  """Utility to provide a consistent sorting of debuggee entries.
  """

  # We add the second sort parameter on displayName for older agents that
  # don't support the 'active debuggee' feature. They will all have the same
  # lastUpdateTimeUnixMsec of 0, so they will still get some useful sorting.
  return sorted(
      debuggees,
      key=lambda d: (d['lastUpdateTimeUnixMsec'], d['displayName']),
      reverse=True)
