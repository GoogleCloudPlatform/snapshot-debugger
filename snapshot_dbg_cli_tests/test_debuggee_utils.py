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

import copy
import unittest

from snapshot_dbg_cli.debuggee_utils import get_display_name
from snapshot_dbg_cli.debuggee_utils import normalize_debuggee
from snapshot_dbg_cli.debuggee_utils import set_converted_timestamps


class SnapshotDebuggerDebuggeeUtilsTests(unittest.TestCase):
  """ Contains the unit tests for the breakpoint_utils module.
  """

  def test_set_converted_timestamps(self):
    """Verifies the set_converted_timestamps() works as expected.

    If the human readable time is not in the breakpoint, but the unix msec
    version is, the human readable version should be populated, otherwise no
    changes are done.
    """

    # Note, these tests don't need fully flesched out breakpoints, the function
    # under test only cares about time fields in a dict, so these minimal dicts
    # suffice.
    testcases = [
        ('No time fields', {}, {}),
        (
            'registrationTime gets populated',
            {
                'registrationTimeUnixMsec': 1649962215000
            },
            {
                'registrationTimeUnixMsec': 1649962215000,
                'registrationTime': '2022-04-14T18:50:15.000000Z'
            },
        ),
        (
            'registrationTime not overrwritten',
            {
                'registrationTimeUnixMsec': 1649962215000,
                'registrationTime': 'exists not overwritten'
            },
            {
                'registrationTimeUnixMsec': 1649962215000,
                'registrationTime': 'exists not overwritten'
            },
        ),
        (
            'lastUpdateTime gets populated',
            {
                'lastUpdateTimeUnixMsec': 1649962215000
            },
            {
                'lastUpdateTimeUnixMsec': 1649962215000,
                'lastUpdateTime': '2022-04-14T18:50:15.000000Z'
            },
        ),
        (
            'lastUpdateTime not overrwritten',
            {
                'lastUpdateTimeUnixMsec': 1649962215000,
                'lastUpdateTime': 'exists not overwritten'
            },
            {
                'lastUpdateTimeUnixMsec': 1649962215000,
                'lastUpdateTime': 'exists not overwritten'
            },
        ),
        (
            'Both registrationTime and lastUpdateTime populated',
            {
                'registrationTimeUnixMsec': 1649962215000,
                'lastUpdateTimeUnixMsec': 1649962215001
            },
            {
                'registrationTimeUnixMsec': 1649962215000,
                'registrationTime': '2022-04-14T18:50:15.000000Z',
                'lastUpdateTimeUnixMsec': 1649962215001,
                'lastUpdateTime': '2022-04-14T18:50:15.001000Z'
            },
        ),
    ]

    for test_name, debuggee, expected_debuggee in testcases:
      with self.subTest(test_name):
        self.assertEqual(expected_debuggee, set_converted_timestamps(debuggee))

  def test_normalize_debuggee_returns_none_when_breakpoint_not_a_dict(self):
    current_time = 1649962215000888
    self.assertIsNone(normalize_debuggee(None, current_time))
    self.assertIsNone(normalize_debuggee(1, current_time))
    self.assertIsNone(normalize_debuggee([1], current_time))
    self.assertIsNone(normalize_debuggee('foo', current_time))
    self.assertIsNone(normalize_debuggee(['foo'], current_time))

  def test_normalize_debuggee_returns_none_when_missing_required_fields(self):
    """Verify normalize_debuggee() returns None when required fields missing.

    The function will generally fill in some missing fields with sane defaults,
    however certain critical required fields cannot be filled in this way. These
    are fields a valid debuggee would be expected to have populated.
    """
    current_time = 1649962215000888
    debuggee = {
        'id': 'd-ab1234cd',
        'labels': {
            'module': 'foo',
            'version': 'v1'
        },
        'description': 'foo msg'
    }

    # Sanity check the debuggee we're using as a base is valid.
    self.assertIsNotNone(normalize_debuggee(debuggee, current_time))

    missing_debuggee_id = copy.deepcopy(debuggee)
    del missing_debuggee_id['id']

    self.assertIsNone(normalize_debuggee(missing_debuggee_id, current_time))

  def test_normalize_debuggee_populates_display_name_when_labels_missing(self):
    current_time = 1649962215000888
    debuggee = {'id': 'd-ab1234cd', 'description': 'foo msg'}

    self.assertIsNotNone(normalize_debuggee(debuggee, current_time))
    self.assertIn('displayName', debuggee)
    self.assertEqual(get_display_name({}), debuggee['displayName'])

  def test_normalize_debuggee_active_debuggee_enabled_field(self):
    current_time = 1649962215000888
    debuggee_not_enabled = {'id': 'd-ab1234cd', 'description': 'foo msg'}

    debuggee_enabled = {
        'id': 'd-ab1234cd',
        'description': 'foo msg',
        'registrationTimeUnixMsec': 1649962215426,
        'lastUpdateTimeUnixMsec': 1670000000001,
    }

    self.assertIsNotNone(normalize_debuggee(debuggee_not_enabled, current_time))
    self.assertIsNotNone(normalize_debuggee(debuggee_enabled, current_time))
    self.assertIn('activeDebuggeeEnabled', debuggee_not_enabled)
    self.assertIn('activeDebuggeeEnabled', debuggee_enabled)
    self.assertFalse(debuggee_not_enabled['activeDebuggeeEnabled'])
    self.assertTrue(debuggee_enabled['activeDebuggeeEnabled'])

  def test_normalize_debuggee_is_active_field_defaults_false(self):
    current_time = 1670000000000

    # When the lastUpdateTimeUnixMsec is missing, 'isActive' should be false
    debuggee = {'id': 'd-ab1234cd', 'description': 'foo msg'}

    self.assertIsNotNone(normalize_debuggee(debuggee, current_time))
    self.assertIn('isActive', debuggee)
    self.assertFalse(debuggee['isActive'])

  def test_normalize_debuggee_is_active_field(self):
    current_time = 1670000000000
    msec_per_hour = 60 * 60 * 1000

    # The active threshold is expected to be 6 hours
    active_threshold = 6 * msec_per_hour

    base_debuggee = {
        'id': 'd-ab1234cd',
        'description': 'foo msg',
        'registrationTimeUnixMsec': 1649962215426,
        'lastUpdateTimeUnixMsec': 0
    }

    testcases = [
        ('Not active by 100 msec', current_time - active_threshold - 100,
         False),
        ('Not active by 1 msec', current_time - active_threshold - 1, False),
        ('Active at threshold', current_time - active_threshold, True),
        ('Active under threshold by 1', current_time - active_threshold + 1,
         True),
        ('Active under threshold by 100', current_time - active_threshold + 100,
         True),

        # Just in case local clock is slightly ahead of the server time, ensure
        # it works as expected.
        ('Active update time newer than current', current_time + 100, True),
    ]

    for test_name, last_update_time_msec, expected_is_valid in testcases:
      with self.subTest(test_name):
        debuggee = copy.deepcopy(base_debuggee)
        debuggee['lastUpdateTimeUnixMsec'] = last_update_time_msec

        self.assertIsNotNone(normalize_debuggee(debuggee, current_time))
        self.assertIn('isActive', debuggee)
        self.assertEqual(expected_is_valid, debuggee['isActive'])

  def test_normalize_debuggee_is_stale_field_defaults_true(self):
    current_time = 1670000000000

    # When the lastUpdateTimeUnixMsec is missing, 'isActive' should be false
    debuggee = {'id': 'd-ab1234cd', 'description': 'foo msg'}

    self.assertIsNotNone(normalize_debuggee(debuggee, current_time))
    self.assertIn('isStale', debuggee)
    self.assertTrue(debuggee['isStale'])

  def test_normalize_debuggee_is_stale_field(self):
    current_time = 1670000000000
    msec_per_hour = 60 * 60 * 1000

    # The stale threshold is expected to be 7 days
    active_threshold = 7 * 24 * msec_per_hour

    base_debuggee = {
        'id': 'd-ab1234cd',
        'description': 'foo msg',
        'registrationTimeUnixMsec': 1649962215426,
        'lastUpdateTimeUnixMsec': 0
    }

    testcases = [
        ('Stale by 100 msec', current_time - active_threshold - 100, True),
        ('Stale by 1 msec', current_time - active_threshold - 1, True),
        ('Not stale at threshold', current_time - active_threshold, False),
        ('Not stale under threshold by 1', current_time - active_threshold + 1,
         False),
        ('Not stale under threshold by 100',
         current_time - active_threshold + 100, False),

        # Just in case local clock is slightly ahead of the server time, ensure
        # it works as expected.
        ('Not stale update time newer than current', current_time + 100, False),
    ]

    for test_name, last_update_time_msec, expected_is_valid in testcases:
      with self.subTest(test_name):
        debuggee = copy.deepcopy(base_debuggee)
        debuggee['lastUpdateTimeUnixMsec'] = last_update_time_msec

        self.assertIsNotNone(normalize_debuggee(debuggee, current_time))
        self.assertIn('isStale', debuggee)
        self.assertEqual(expected_is_valid, debuggee['isStale'])

  def test_normalize_debuggee_populates_missing_fields_as_expected(self):
    # To note, we're using a completed snapshot here since finalTime will only
    # be polpulated if the breakpoint is final.

    current_time = 1649962215000888
    base_debuggee = {
        'id': 'd-ab1234cd',
        'labels': {
            'module': 'foo',
            'version': 'v1'
        },
        'description': 'foo msg',
        'registrationTimeUnixMsec': 1649962215426,
        'lastUpdateTimeUnixMsec': 1649962230637,
        'registrationTime': '2022-04-14T18:50:15.426000Z',
        'lastUpdateTime': '2022-04-14T18:50:30.637000Z',
        'displayName': 'foo - v1',
    }

    testcases = [
        # (missing field, expected fill in value)
        ('description', ''),
        ('registrationTimeUnixMsec', 0),
        ('lastUpdateTimeUnixMsec', 0),
        ('registrationTime', '2022-04-14T18:50:15.426000Z'),
        ('lastUpdateTime', '2022-04-14T18:50:30.637000Z'),
        ('displayName', 'foo - v1'),
    ]

    for missing_field, expected_field_value in testcases:
      test_name = missing_field
      with self.subTest(test_name):
        debuggee = copy.deepcopy(base_debuggee)
        del debuggee[missing_field]
        self.assertNotIn(missing_field, debuggee)

        obtained_debuggee = normalize_debuggee(debuggee, current_time)

        # It's expected the same instance is returned.
        self.assertIs(obtained_debuggee, debuggee)
        self.assertIn(missing_field, obtained_debuggee)
        self.assertEqual(expected_field_value, obtained_debuggee[missing_field])

  def test_get_display_name(self):
    self.assertEqual(get_display_name({}), 'default - ')
    self.assertEqual(get_display_name({'module': 'foo'}), 'foo - ')
    self.assertEqual(get_display_name({'version': 'v1'}), 'default - v1')
    self.assertEqual(
        get_display_name({
            'module': 'foo',
            'version': 'v1'
        }), 'foo - v1')
