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

from breakpoints_rtdb_service import BreakpointsRtdbService
from exceptions import SilentlyExitError

DEBUGGEE_NOT_FOUND_ERROR_MESSAGE = (
    'Debuggee ID {debuggee_id} was not found.  Specify a debuggee ID found in '
    'the result of the list_debuggees command.')


class FirebaseRtdbService:
  """This class provides methods that communicates with the database.

  This service provides utility methods that need to communicate with the
  Firebase RTDB instance.

  Attributes:
    breakpoints_rtdb_service: Service to use for breakpoints related read/write
      requests to the Firebase RTDB instance.
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
    self.breakpoints_rtdb_service = BreakpointsRtdbService(
        self.rest_service, self.schema, self.user_output)

  def get_schema_version(self):
    return self.rest_service.get(self.schema.get_path_schema_version())

  def set_schema_version(self, version):
    return self.rest_service.set(self.schema.get_path_schema_version(), version)

  def get_debuggees(self):
    return self.rest_service.get(self.schema.get_path_debuggees())

  def validate_debuggee_id(self, debuggee_id):
    """Validates the debuggee ID exists.

    Verifies the debuggee ID exists in the Firebase RTDB instance. If the
    debuggee ID did not exist an appropriate error message is emitted to the
    user and the SilentlyExitError exception is raised.

    Args:
      user_output: A UserOutput instance.
      firebase_rtdb_service: A FirebaseRtdbRestService instance.
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
