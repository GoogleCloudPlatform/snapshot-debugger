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
"""This module provides a variety of utilities useful to multiple commands.
"""

from exceptions import SilentlyExitError

DEBUGGEE_NOT_FOUND_ERROR_MESSAGE = (
    'Debuggee ID {debuggee_id} was not found.  Specify a debuggee ID found in '
    'the result of the list_debuggees command.')


def validate_debuggee_id(user_output, firebase_rtdb_service, debuggee_id):
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

  debuggee = firebase_rtdb_service.get(f'debuggees/{debuggee_id}')

  if debuggee is None:
    user_output.error(
        DEBUGGEE_NOT_FOUND_ERROR_MESSAGE.format(debuggee_id=debuggee_id))
    raise SilentlyExitError
