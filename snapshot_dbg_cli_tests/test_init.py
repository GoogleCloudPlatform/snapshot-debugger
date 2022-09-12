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
""" Unit test __init__.
"""

import unittest
import snapshot_dbg_cli


class CliInitTests(unittest.TestCase):
  """ Contains the unit tests for __init__.py
  """

  def test_version_is_expected_value(self):
    # Yes, this will need to be updated for each new version.
    self.assertEqual('0.1.1', snapshot_dbg_cli.__version__)
