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
""" Unit test file for the debuggee_utils module.
"""

import unittest

from snapshot_dbg_cli.time_utils import convert_unix_msec_to_rfc3339


class ListDebuggeesCommandTests(unittest.TestCase):
  """ Contains the unit tests for the time_utils module.
  """

  def test_convert_unix_msec_to_rfc3339(self):
    self.assertEqual('2022-04-14T18:50:15.000000Z',
                     convert_unix_msec_to_rfc3339(1649962215000))
    self.assertEqual('2022-04-14T18:50:15.001000Z',
                     convert_unix_msec_to_rfc3339(1649962215001))
    self.assertEqual('2022-04-14T18:50:15.010000Z',
                     convert_unix_msec_to_rfc3339(1649962215010))
    self.assertEqual('2022-04-14T18:50:15.100000Z',
                     convert_unix_msec_to_rfc3339(1649962215100))
    self.assertEqual('2022-04-14T18:50:15.426000Z',
                     convert_unix_msec_to_rfc3339(1649962215426))

    # For any invalid input, the function will default to using a value of 0,
    # which represents the epoch (1970-01-01). This way the function can still
    # return a properly formatting string, and the value is recognizable as
    # indicating there was an issue and the actual time is not known.
    self.assertEqual('1970-01-01T00:00:00.000000Z',
                     convert_unix_msec_to_rfc3339(999999999999999))
    self.assertEqual('1970-01-01T00:00:00.000000Z',
                     convert_unix_msec_to_rfc3339('asdf'))
