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
"""Provides a service to retrieve the paths entities in the database.
"""

SNAPSHOT_DEBUGGER_ROOT_PATH = 'cdbg'

DEBUGGEES_PATH = '{root_path}/debuggees'
DEBUGGEES_PATH_FOR_ID = '{root_path}/debuggees/{debuggee_id}'

SCHEMA_VERSION_PATH = '{root_path}/schema_version'

BREAKPOINTS_PATH = '{root_path}/breakpoints/{debuggee_id}'

BREAKPOINTS_ACTIVE_PATH = '{root_path}/breakpoints/{debuggee_id}/active'
BREAKPOINTS_ACTIVE_PATH_FOR_ID = ('{root_path}/breakpoints/{debuggee_id}'
                                  '/active/{breakpoint_id}')

BREAKPOINTS_FINAL_PATH = '{root_path}/breakpoints/{debuggee_id}/final'
BREAKPOINTS_FINAL_PATH_FOR_ID = ('{root_path}/breakpoints/{debuggee_id}'
                                 '/final/{breakpoint_id}')

BREAKPOINTS_SNAPSHOT_PATH = '{root_path}/breakpoints/{debuggee_id}/snapshot'
BREAKPOINTS_SNAPSHOT_PATH_FOR_ID = ('{root_path}/breakpoints/{debuggee_id}'
                                    '/snapshot/{breakpoint_id}')


class SnapshotDebuggerSchema:
  """This class provides methods for retrieving database paths.

  The purpose of this class is to keep all the information about the database
  paths in one location and provide utility methods for retrieving them.
  """

  def get_path_schema_version(self):
    return SCHEMA_VERSION_PATH.format(root_path=SNAPSHOT_DEBUGGER_ROOT_PATH)

  def get_path_debuggees(self):
    return DEBUGGEES_PATH.format(root_path=SNAPSHOT_DEBUGGER_ROOT_PATH)

  def get_path_debuggees_for_id(self, debuggee_id):
    return DEBUGGEES_PATH_FOR_ID.format(
        root_path=SNAPSHOT_DEBUGGER_ROOT_PATH, debuggee_id=debuggee_id)

  def get_path_breakpoints(self, debuggee_id):
    return self._get_path_breakpoints(BREAKPOINTS_PATH, debuggee_id)

  def get_path_breakpoints_active(self, debuggee_id):
    return self._get_path_breakpoints(BREAKPOINTS_ACTIVE_PATH, debuggee_id)

  def get_path_breakpoints_active_for_id(self, debuggee_id, breakpoint_id):
    return self._get_path_breakpoints_for_id(BREAKPOINTS_ACTIVE_PATH_FOR_ID,
                                             debuggee_id, breakpoint_id)

  def get_path_breakpoints_final(self, debuggee_id):
    return self._get_path_breakpoints(BREAKPOINTS_FINAL_PATH, debuggee_id)

  def get_path_breakpoints_final_for_id(self, debuggee_id, breakpoint_id):
    return self._get_path_breakpoints_for_id(BREAKPOINTS_FINAL_PATH_FOR_ID,
                                             debuggee_id, breakpoint_id)

  def get_path_breakpoints_snapshot(self, debuggee_id):
    return self._get_path_breakpoints(BREAKPOINTS_SNAPSHOT_PATH, debuggee_id)

  def get_path_breakpoints_snapshot_for_id(self, debuggee_id, breakpoint_id):
    return self._get_path_breakpoints_for_id(BREAKPOINTS_SNAPSHOT_PATH_FOR_ID,
                                             debuggee_id, breakpoint_id)

  def _get_path_breakpoints(self, base_breakpoints_format_string, debuggee_id):
    return base_breakpoints_format_string.format(
        root_path=SNAPSHOT_DEBUGGER_ROOT_PATH, debuggee_id=debuggee_id)

  def _get_path_breakpoints_for_id(self, base_breakpoints_format_string,
                                   debuggee_id, breakpoint_id):
    return base_breakpoints_format_string.format(
        root_path=SNAPSHOT_DEBUGGER_ROOT_PATH,
        debuggee_id=debuggee_id,
        breakpoint_id=breakpoint_id)
