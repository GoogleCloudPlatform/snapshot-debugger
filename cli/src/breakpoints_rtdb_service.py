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
"""Service for making breakpoint related requests to the Firebase RTDB.
"""

from breakpoint_utils import normalize_breakpoint
from exceptions import SilentlyExitError

import time


class BreakpointsRtdbService:
  """This class provides breakpoints query/update methods.

  This service provides breakpoints related utility methods that need to
  communicate with the Firebase RTDB instance.
  """

  def __init__(self, firebase_rtdb_service, schema_service, user_output):
    """Initializes a BreakpointsRtdbService instance with required services.

    Args:
      firebase_rtdb_service: A FirebaseRtdbService instance.
      schema_service: A SnapshotDebuggerSchema instance.
      user_output: A UserOutput instance.
    """
    self.firebase_rtdb_service = firebase_rtdb_service
    self.schema_service = schema_service
    self.user_output = user_output

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
      active_path = self.schema_service.get_path_breakpoints_active_for_id(
          debuggee_id, breakpoint_id)
      final_path = self.schema_service.get_path_breakpoints_final_for_id(
          debuggee_id, breakpoint_id)

      bp_active = self.firebase_rtdb_service.get(active_path, shallow=True)
      bp_final = self.firebase_rtdb_service.get(final_path, shallow=True)

      # This case means there no breakpoints were found with that id, which
      # means the id is free to use.
      if bp_active is None and bp_final is None:
        found = True
        break

    if not found:
      self.user_output.error(
          'ERROR Failed to determine a new breakpoint ID, please try again')
      raise SilentlyExitError

    return breakpoint_id

  def delete_breakpoints(self, debuggee_id, breakpoints):
    for b in breakpoints:
      active_path = self.schema_service.get_path_breakpoints_active_for_id(
          debuggee_id, b['id'])
      final_path = self.schema_service.get_path_breakpoints_final_for_id(
          debuggee_id, b['id'])
      snapshot_path = self.schema_service.get_path_breakpoints_snapshot_for_id(
          debuggee_id, b['id'])

      self.firebase_rtdb_service.delete(active_path)
      self.firebase_rtdb_service.delete(final_path)

      if b['action'] == 'CAPTURE':
        self.firebase_rtdb_service.delete(snapshot_path)

  def get_breakpoint(self, debuggee_id, breakpoint_id):
    active_path = self.schema_service.get_path_breakpoints_active_for_id(
        debuggee_id, breakpoint_id)
    final_path = self.schema_service.get_path_breakpoints_snapshot_for_id(
        debuggee_id, breakpoint_id)

    bp = self.firebase_rtdb_service.get(active_path)

    # If it wasn't active, the response will be None, so then try the final
    # path.
    if bp is None:
      bp = self.firebase_rtdb_service.get(final_path)

    return normalize_breakpoint(bp, breakpoint_id)

  def get_snapshot(self, debuggee_id, snapshot_id):
    active_path = self.schema_service.get_path_breakpoints_active_for_id(
        debuggee_id, snapshot_id)
    snapshot_path = self.schema_service.get_path_breakpoints_snapshot_for_id(
        debuggee_id, snapshot_id)

    bp = self.firebase_rtdb_service.get(active_path)

    # If it wasn't active, the response will be None, so then try the full
    # snapshot path.
    if bp is None:
      bp = self.firebase_rtdb_service.get(snapshot_path)

    return normalize_breakpoint(bp, snapshot_id)

  def get_active_breakpoints(self, debuggee_id, action, user_email):
    path = self.schema_service.get_path_breakpoints_active(debuggee_id)
    return self._get_breakpoints(path, action, user_email)

  def get_final_breakpoints(self, debuggee_id, action, user_email):
    path = self.schema_service.get_path_breakpoints_final(debuggee_id)
    return self._get_breakpoints(path, action, user_email)

  def get_breakpoints(self,
                      debuggee_id,
                      include_inactive,
                      action,
                      user_email=None):
    breakpoints = self.get_active_breakpoints(debuggee_id, action, user_email)

    if include_inactive:
      breakpoints += self.get_final_breakpoints(debuggee_id, action, user_email)

    return breakpoints

  def get_snapshots(self, debuggee_id, include_inactive, user_email=None):
    return self.get_breakpoints(debuggee_id, include_inactive, 'CAPTURE',
                                user_email)

  def _get_breakpoints(self, path, action, user_email):
    breakpoints = self.firebase_rtdb_service.get(path) or {}

    # We want the breakpoints to be in list form, they will be in dict form
    # after the firebase call.

    breakpoints = [
        bp for bpid, bp in breakpoints.items()
        if normalize_breakpoint(bp, bpid) and bp['action'] == action and
        (user_email is None or bp['userEmail'] == user_email)
    ]

    return breakpoints

  def set_breakpoint(self, debuggee_id, breakpoint_data):
    path = self.schema_service.get_path_breakpoints_active_for_id(
        debuggee_id, breakpoint_data['id'])
    bp = self.firebase_rtdb_service.set(path, data=breakpoint_data)
    return normalize_breakpoint(bp)
