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
from snapshot_dbg_cli.time_utils import set_converted_timestamps


class ListDebuggeesCommandTests(unittest.TestCase):
  """ Contains the unit tests for the time_utils module.
  """

  def test_convert_unix_msec_to_rfc3339(self):
    self.assertEqual('2022-04-14T18:50:15Z',
                     convert_unix_msec_to_rfc3339(1649962215000))
    self.assertEqual('2022-04-14T18:50:16Z',
                     convert_unix_msec_to_rfc3339(1649962216000))

    # For any invalid input, the function will default to using a value of 0,
    # which represents the epoch (1970-01-01). This way the function can still
    # return a properly formatting string, and the value is recognizable as
    # indicating there was an issue and the actual time is not known.
    self.assertEqual('1970-01-01T00:00:00Z',
                     convert_unix_msec_to_rfc3339(999999999999999))
    self.assertEqual('1970-01-01T00:00:00Z',
                     convert_unix_msec_to_rfc3339('asdf'))

  def test_set_converted_timestamps_one_conversion(self):
    data = {'fooTimeUnixMsec': 1649962215000}

    field_mappings = [
        ('fooTime', 'fooTimeUnixMsec'),
    ]

    expected_data = {
        'fooTime': '2022-04-14T18:50:15Z',
        'fooTimeUnixMsec': 1649962215000
    }

    self.assertIs(data, set_converted_timestamps(data, field_mappings))
    self.assertEqual(expected_data, data)

  def test_set_converted_timestamps_two_conversions(self):
    data = {'fooTimeUnixMsec': 1649962215000, 'barTimeUnixMsec': 1649962216000}

    field_mappings = [
        ('fooTime', 'fooTimeUnixMsec'),
        ('barTime', 'barTimeUnixMsec'),
    ]

    expected_data = {
        'fooTime': '2022-04-14T18:50:15Z',
        'fooTimeUnixMsec': 1649962215000,
        'barTime': '2022-04-14T18:50:16Z',
        'barTimeUnixMsec': 1649962216000
    }

    self.assertIs(data, set_converted_timestamps(data, field_mappings))
    self.assertEqual(expected_data, data)

  def test_set_converted_timestamps_does_not_overwrite_if_dest_exists(self):
    data = {'fooTime': 'already exists', 'fooTimeUnixMsec': 1649962215000}

    field_mappings = [
        ('fooTime', 'fooTimeUnixMsec'),
    ]

    expected_data = {
        'fooTime': 'already exists',
        'fooTimeUnixMsec': 1649962215000
    }

    self.assertIs(data, set_converted_timestamps(data, field_mappings))
    self.assertEqual(expected_data, data)

  def test_set_converted_timestamps_source_does_not_exist(self):
    """Test ensures if source field doesn't exists nothing bad happens.
    """
    data = {'fooTimeUnixMsec': 1649962215000}

    field_mappings = [
        ('fooTime', 'fooTimeSourceDoesNotExist'),
    ]

    expected_data = {'fooTimeUnixMsec': 1649962215000}

    self.assertIs(data, set_converted_timestamps(data, field_mappings))
    self.assertEqual(expected_data, data)

  def test_set_converted_timestamps_source_is_zero(self):
    data = {'fooTimeUnixMsec': 0}

    field_mappings = [
        ('fooTime', 'fooTimeUnixMsec'),
    ]

    expected_data = {'fooTime': 'not set', 'fooTimeUnixMsec': 0}

    self.assertIs(data, set_converted_timestamps(data, field_mappings))
    self.assertEqual(expected_data, data)
