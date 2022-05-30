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
""" Unit test file for the SnapshotDebuggerSchema class.
"""

import unittest
from cli import snapshot_debugger_schema


class TestSnapshotDebuggerSchema(unittest.TestCase):
  """ Contains the unit tests for the SnapshotDebuggerSchema class.
  """

  def setUp(self):
    self.schema = snapshot_debugger_schema.SnapshotDebuggerSchema()

  def test_path_schema_version_is_correct(self):
    self.assertEqual(self.schema.get_path_schema_version(),
                     'cdbg/schema_version')

  def test_path_debuggees_is_correct(self):
    self.assertEqual(self.schema.get_path_debuggees(), 'cdbg/debuggees')

  def test_path_debuggees_for_id_is_correct(self):
    self.assertEqual(
        self.schema.get_path_debuggees_for_id(debuggee_id='123'),
        'cdbg/debuggees/123')

  def test_path_breakpoints_active_is_correct(self):
    self.assertEqual(
        self.schema.get_path_breakpoints_active(debuggee_id='123'),
        'cdbg/breakpoints/123/active')

  def test_path_breakpoints_active_for_id_is_correct(self):
    self.assertEqual(
        self.schema.get_path_breakpoints_active_for_id(
            debuggee_id='123', breakpoint_id='b-1653408119'),
        'cdbg/breakpoints/123/active/b-1653408119')

  def test_path_breakpoints_final_is_correct(self):
    self.assertEqual(
        self.schema.get_path_breakpoints_final(debuggee_id='123'),
        'cdbg/breakpoints/123/final')

  def test_path_breakpoints_final_for_id_is_correct(self):
    self.assertEqual(
        self.schema.get_path_breakpoints_final_for_id(
            debuggee_id='123', breakpoint_id='b-1653408119'),
        'cdbg/breakpoints/123/final/b-1653408119')

  def test_path_breakpoints_snapshot_is_correct(self):
    self.assertEqual(
        self.schema.get_path_breakpoints_snapshot(debuggee_id='123'),
        'cdbg/breakpoints/123/snapshot')

  def test_path_breakpoints_snapshot_for_id_is_correct(self):
    self.assertEqual(
        self.schema.get_path_breakpoints_snapshot_for_id(
            debuggee_id='123', breakpoint_id='b-1653408119'),
        'cdbg/breakpoints/123/snapshot/b-1653408119')


if __name__ == '__main__':
  unittest.main()
