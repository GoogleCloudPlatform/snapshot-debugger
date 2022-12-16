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
"""Service for making requests to the Firebase RTDB.
"""

from snapshot_dbg_cli.breakpoint_utils import normalize_breakpoint
from snapshot_dbg_cli.debuggee_utils import normalize_debuggee
from snapshot_dbg_cli.exceptions import SilentlyExitError

import time

DEBUGGEE_NOT_FOUND_ERROR_MESSAGE = (
    'Debuggee ID {debuggee_id} was not found.  Specify a debuggee ID found in '
    'the result of the list_debuggees command.')


class SnapshotDebuggerRtdbService:
  """This class provides methods that communicates with the database.

  This service provides utility methods that need to communicate with the
  Firebase RTDB instance.
  """

  def __init__(self, firebase_rtdb_rest_service, snapshot_debugger_schema,
               user_output):
    """Initializes a BreakpointsRtdbService instance with required services.

    Args:
      firebase_rtdb_rest_service: A FirebaseRtdbRestService instance.
      snapshot_debugger_schema: A SnapshotDebuggerSchema instance.
      user_output: A UserOutput instance.
    """
    self.rest_service = firebase_rtdb_rest_service
    self.schema = snapshot_debugger_schema
    self.user_output = user_output

  def get_schema_version(self):
    return self.rest_service.get(self.schema.get_path_schema_version())

  def set_schema_version(self, version):
    return self.rest_service.set(self.schema.get_path_schema_version(), version)

  def get_debuggee(self, debuggee_id, current_time_unix_msec):
    """Retrieves debuggee data for the given debuggee ID.

    Args:
      debuggee_id: The ID of the debuggee to retrieve.

    Returns:
      The debuggee (in dict form) if found, None otherwise. If the debuggee
      was found it will have the debuggee_utils.normalize_debuggee function
      applied to it to ensure all expected fields are set.
    """
    debuggee_path = self.schema.get_path_debuggees_for_id(debuggee_id)
    debuggee = self.rest_service.get(debuggee_path)

    return normalize_debuggee(debuggee, current_time_unix_msec)

  def get_debuggees(self, current_time_unix_msec):
    debuggees = self.rest_service.get(self.schema.get_path_debuggees()) or {}

    # The result will be a dictionary, convert it to an array, while also
    # filtering out any invalid entries. normalize_debuggee returns None for
    # invalid debuggees.
    debuggees = [
        dbgee for dbgee_id, dbgee in debuggees.items()
        if normalize_debuggee(dbgee, current_time_unix_msec)
    ]

    return debuggees

  def validate_debuggee_id(self, debuggee_id):
    """Validates the debuggee ID exists.

    Verifies the debuggee ID exists in the Firebase RTDB instance. If the
    debuggee ID did not exist an appropriate error message is emitted to the
    user and the SilentlyExitError exception is raised.

    Args:
      debuggee_id: The debuggee ID to validate.

    Raises:
      SilentlyExitError: When the debuggee ID did not exist, or an underlying
        error occurred attempting to contact the RTDB instance.
    """

    debuggee_path = self.schema.get_path_debuggees_for_id(debuggee_id)

    if self.rest_service.get(debuggee_path) is None:
      self.user_output.error(
          DEBUGGEE_NOT_FOUND_ERROR_MESSAGE.format(debuggee_id=debuggee_id))
      raise SilentlyExitError

  def delete_debuggees(self, debuggees):
    for d in debuggees:
      debuggee_id = d['id']
      breakpoints_path = self.schema.get_path_breakpoints(debuggee_id)
      debuggee_path = self.schema.get_path_debuggees_for_id(debuggee_id)

      # The order here is deliberate to avoid orphaned breakpoints, the main
      # debuggee entry is only deleted after all of it's breakpoints have been
      # successfully deleted.
      self.rest_service.delete(breakpoints_path)
      self.rest_service.delete(debuggee_path)

  # Returns the id to use when creating a new breakpoint.
  # To note, we use the format 'b_<unix epoc seconds>' this ensures the ID
  # cannot be interpreted as an integer. This is specifically done for the
  # following reason:
  #
  # Per
  # https://firebase.googleblog.com/2014/04/best-practices-arrays-in-firebase.html
  # "If all of the keys are integers, and more than half of the keys are between
  # 0 and the maximum key in the object have non-empty values, then Firebase
  # will render it as an array."
  #
  # As the breakpoint IDs will used as keys in the RTDB we do not want the above
  # behaviour, as we always want maps to be returned instead of arrays.
  def get_new_breakpoint_id(self, debuggee_id):
    time_secs = int(time.time())
    breakpoint_id = None
    found = False

    for i in range(0, 10):
      breakpoint_id = f'b-{time_secs + i}'

      bp = self.get_breakpoint(debuggee_id, breakpoint_id, shallow=True)

      # This case means there no breakpoints were found with that id, which
      # means the id is free to use.
      if bp is None:
        found = True
        break

    if not found:
      self.user_output.error(
          'ERROR Failed to determine a new breakpoint ID, please try again')
      raise SilentlyExitError

    return breakpoint_id

  def delete_breakpoints(self, debuggee_id, breakpoints):
    for b in breakpoints:
      active_path = self.schema.get_path_breakpoints_active_for_id(
          debuggee_id, b['id'])
      final_path = self.schema.get_path_breakpoints_final_for_id(
          debuggee_id, b['id'])
      snapshot_path = self.schema.get_path_breakpoints_snapshot_for_id(
          debuggee_id, b['id'])

      if not b['isFinalState']:
        self.rest_service.delete(active_path)

      # Given usually on delete we prompt the user before continuing with the
      # delete, it's possible that the breakpoint has finialized in the
      # intervening seconds, so we always attempt to delete final paths. If
      # there is no breakpoint at the path there is no harm, nothing fails etc.
      self.rest_service.delete(final_path)

      if b['action'] == 'CAPTURE':
        self.rest_service.delete(snapshot_path)

  def get_breakpoint(self, debuggee_id, breakpoint_id, shallow=False):
    """Retrieves breakpoint data for the given debuggee and breakpoint ID.

    To note, if the breakpoint ID refers to a snapshot which has completed, the
    capture data is expressly not returned via this call. To retrieve the full
    snapshot data the get_snapshot_detailed() method should be used instead.

    Args:
      debuggee_id: The debuggee to retrieve the breakpoint from.
      breakpoint_id: The ID of the breakpoint to retrieve.
      shallow: Boolean flag passed to the RTDB Rest call. When true it will cut
        down on the data returned. In the case of a breakpoint, only the keys,
        all mapped to True will be returned.

    Returns:
      The breakpoint (in dict form) if found, None otherwise. If the breakpoint
      was found it will have the breakpoint_utils.normalize_breakpoint function
      applied to it to ensure all expected fields are set.
    """
    active_path = self.schema.get_path_breakpoints_active_for_id(
        debuggee_id, breakpoint_id)
    bp = self.rest_service.get(active_path, shallow=shallow)

    # If it wasn't active, the response will be None, so then try the final
    # path.
    if bp is None:
      final_path = self.schema.get_path_breakpoints_final_for_id(
          debuggee_id, breakpoint_id)
      bp = self.rest_service.get(final_path, shallow=shallow)

    return normalize_breakpoint(bp, breakpoint_id)

  def get_snapshot_detailed(self, debuggee_id, breakpoint_id):
    """Retrieves the snapshot data for the given debuggee and breakpoint ID.

    To note, if the breakpoint ID refers to a snapshot which has completed, the
    full capture data (if any) is returned via this call.

    Args:
      debuggee_id: The debuggee to retrieve the snapshots from.
      breakpoint_id: The ID of the snapshot to retrieve.

    Returns:
      The snapshot (in dict form) if found, None otherwise. If the snapshot
      was found it will have the breakpoint_utils.normalize_breakpoint function
      applied to it to ensure all expected fields are set.
    """
    active_path = self.schema.get_path_breakpoints_active_for_id(
        debuggee_id, breakpoint_id)
    snapshot_path = self.schema.get_path_breakpoints_snapshot_for_id(
        debuggee_id, breakpoint_id)

    bp = self.rest_service.get(active_path)

    # If it wasn't active, the response will be None, so then try the full
    # snapshot path.
    if bp is None:
      bp = self.rest_service.get(snapshot_path)

    return normalize_breakpoint(bp, breakpoint_id)

  def get_logpoints(self, debuggee_id, include_inactive, user_email=None):
    """Retrieves all the logpoints matching the search criteria.

    Args:
      debuggee_id: The debuggee to retrieve the logpoints from.
      include_inactive: Boolean flag that when true will return both active and
        completed logpoints. When false, only active logpoints will be returned.
      user_email: A filter that when set to a string value, will only return
        snapshots whose 'userEmail' matches. When this value is None, snapshots
        from all users are returned.

    Returns:
      The logpoints (list of dicts). If no snapshots were found this list will
      simply be empty. All returned logpoints will have the
      breakpoint_utils.normalize_breakpoint function applied to ensure all
      expected fields are set.
    """
    return self._get_breakpoints(debuggee_id, include_inactive, 'LOG',
                                 user_email)

  def get_snapshots(self, debuggee_id, include_inactive, user_email=None):
    """Retrieves all the snapshots matching the search criteria.

    To note, for any snapshots that have completed, no capture data is retrieved
    via this call. To get the full capture data an individual call to
    get_snapshot_detailed() is required.

    Args:
      debuggee_id: The debuggee to retrieve the snapshots from.
      include_inactive: Boolean flag that when true will return both active and
        completed snapshots. When false, only active snapshots will be returned.
      user_email: A filter that when set to a string value, will only return
        snapshots whose 'userEmail' matches. When this value is None, snapshots
        from all users are returned.

    Returns:
      The snapshots (list of dicts). If no snapshots were found this list will
      simply be empty. All returned snapshots will have the
      breakpoint_utils.normalize_breakpoint function applied to ensure all
      expected fields are set.
    """
    return self._get_breakpoints(debuggee_id, include_inactive, 'CAPTURE',
                                 user_email)

  def _get_breakpoints(self,
                       debuggee_id,
                       include_inactive,
                       action,
                       user_email=None):
    breakpoints = self._get_breakpoints_by_path_and_filter(
        self.schema.get_path_breakpoints_active(debuggee_id), action,
        user_email)

    if include_inactive:
      breakpoints += self._get_breakpoints_by_path_and_filter(
          self.schema.get_path_breakpoints_final(debuggee_id), action,
          user_email)

    return breakpoints

  def _get_breakpoints_by_path_and_filter(self, path, action, user_email):
    breakpoints = self.rest_service.get(path) or {}

    # We want the breakpoints to be in list form, they will be in dict form
    # after the firebase call.
    breakpoints = [
        bp for bpid, bp in breakpoints.items()
        if normalize_breakpoint(bp, bpid) and bp['action'] == action and
        (user_email is None or bp['userEmail'] == user_email)
    ]

    return breakpoints

  def set_breakpoint(self, debuggee_id, breakpoint_data):
    path = self.schema.get_path_breakpoints_active_for_id(
        debuggee_id, breakpoint_data['id'])
    bp = self.rest_service.set(path, data=breakpoint_data)

    return normalize_breakpoint(bp)
