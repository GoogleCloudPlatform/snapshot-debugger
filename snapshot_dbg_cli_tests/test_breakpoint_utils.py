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
""" Unit test file for the breakpoint_utils module.
"""

import copy
import unittest

from snapshot_dbg_cli.breakpoint_utils import convert_unix_msec_to_rfc3339
from snapshot_dbg_cli.breakpoint_utils import parse_and_validate_location
from snapshot_dbg_cli.breakpoint_utils import normalize_breakpoint
from snapshot_dbg_cli.breakpoint_utils import set_converted_timestamps
from snapshot_dbg_cli.breakpoint_utils import split_log_expressions
from snapshot_dbg_cli.breakpoint_utils import transform_location_to_file_line

SNAPSHOT_ACTIVE =  {
  'action': 'CAPTURE',
  'createTimeUnixMsec': 1649962215426,
  'id': 'b-1649962215',
  'isFinalState': False,
  'location': {'line': 26, 'path': 'index.js'},
  'userEmail': 'foo@bar.com',
  'createTime': '2022-04-14T18:50:15.426000Z',
} # yapf: disable (Subjectively, more readable hand formatted)

SNAPSHOT_COMPLETE =  {
  'action': 'CAPTURE',
  'createTimeUnixMsec': 1649962215426,
  'finalTimeUnixMsec': 1649962230637,
  'id': 'b-1649962215',
  'isFinalState': True,
  'location': {'line': 26, 'path': 'index.js'},
  'userEmail': 'foo@bar.com',
  'createTime': '2022-04-14T18:50:15.426000Z',
  'finalTime': '2022-04-14T18:50:30.637000Z',
} # yapf: disable (Subjectively, more readable hand formatted)


class SnapshotDebuggerBreakpointUtilsTests(unittest.TestCase):
  """ Contains the unit tests for the breakpoint_utils module.
  """

  def test_parse_and_validate_location_prevents_invalid_input(self):
    self.assertIsNone(parse_and_validate_location(''))
    self.assertIsNone(parse_and_validate_location(':'))
    self.assertIsNone(parse_and_validate_location('::'))
    self.assertIsNone(parse_and_validate_location(':f:1'))
    self.assertIsNone(parse_and_validate_location('f:f:1'))
    self.assertIsNone(parse_and_validate_location('noline:'))
    self.assertIsNone(parse_and_validate_location('src/noline:'))
    self.assertIsNone(parse_and_validate_location(':123'))
    self.assertIsNone(parse_and_validate_location('f:1f'))
    self.assertIsNone(parse_and_validate_location('f:11*'))
    self.assertIsNone(parse_and_validate_location('main.java:0'))
    self.assertIsNone(parse_and_validate_location('main.java:-1'))
    self.assertIsNone(parse_and_validate_location('file:foo:9'))
    self.assertIsNone(parse_and_validate_location('file:999999999999999999'))

  def test_parse_and_validate_location_accepts_valid_input(self):
    self.assertEqual({
        'path': 'foo',
        'line': 1
    }, parse_and_validate_location('foo:1'))
    self.assertEqual({
        'path': 'f.java',
        'line': 1
    }, parse_and_validate_location('f.java:1'))
    self.assertEqual({
        'path': 'foo.py',
        'line': 123456789
    }, parse_and_validate_location('foo.py:123456789'))
    self.assertEqual({
        'path': 'src/foo.py',
        'line': 12
    }, parse_and_validate_location('src/foo.py:12'))
    self.assertEqual({
        'path': '/src/foo.py',
        'line': 12
    }, parse_and_validate_location('/src/foo.py:12'))

  def test_transform_location_to_file_line(self):
    self.assertEqual(None, transform_location_to_file_line({}))
    self.assertEqual(None, transform_location_to_file_line({'path': 'foo.py'}))
    self.assertEqual(None, transform_location_to_file_line({'line': 10}))
    self.assertEqual(
        'foo.py:10',
        transform_location_to_file_line({
            'path': 'foo.py',
            'line': 10
        }))

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
            'createTime gets populated',
            {
                'createTimeUnixMsec': 1649962215000
            },
            {
                'createTimeUnixMsec': 1649962215000,
                'createTime': '2022-04-14T18:50:15.000000Z'
            },
        ),
        (
            'createTime not overrwritten',
            {
                'createTimeUnixMsec': 1649962215000,
                'createTime': 'exists not overwritten'
            },
            {
                'createTimeUnixMsec': 1649962215000,
                'createTime': 'exists not overwritten'
            },
        ),
        (
            'finalTime gets populated',
            {
                'finalTimeUnixMsec': 1649962215000
            },
            {
                'finalTimeUnixMsec': 1649962215000,
                'finalTime': '2022-04-14T18:50:15.000000Z'
            },
        ),
        (
            'finalTime not overrwritten',
            {
                'finalTimeUnixMsec': 1649962215000,
                'finalTime': 'exists not overwritten'
            },
            {
                'finalTimeUnixMsec': 1649962215000,
                'finalTime': 'exists not overwritten'
            },
        ),
        (
            'Both createTime and finalTime populated',
            {
                'createTimeUnixMsec': 1649962215000,
                'finalTimeUnixMsec': 1649962215001
            },
            {
                'createTimeUnixMsec': 1649962215000,
                'createTime': '2022-04-14T18:50:15.000000Z',
                'finalTimeUnixMsec': 1649962215001,
                'finalTime': '2022-04-14T18:50:15.001000Z'
            },
        ),
    ]

    for test_name, bp, expected_bp in testcases:
      with self.subTest(test_name):
        self.assertEqual(expected_bp, set_converted_timestamps(bp))

  def test_normalize_breakpoint_returns_none_when_breakpoint_not_a_dict(self):
    self.assertIsNone(normalize_breakpoint(None))
    self.assertIsNone(normalize_breakpoint(None, 'b-123'))
    self.assertIsNone(normalize_breakpoint(1))
    self.assertIsNone(normalize_breakpoint(1, 'b-123'))
    self.assertIsNone(normalize_breakpoint([1]))
    self.assertIsNone(normalize_breakpoint([1], 'b-123'))
    self.assertIsNone(normalize_breakpoint('foo'))
    self.assertIsNone(normalize_breakpoint('foo', 'b-123'))
    self.assertIsNone(normalize_breakpoint(['foo']))
    self.assertIsNone(normalize_breakpoint(['foo'], 'b-123'))

  def test_normalize_breakpoint_returns_none_when_missing_required_fields(self):
    """Verify normalize_breakpoint() returns None when required fields missing.

    The function will generally fill in some missing fields with sane defaults,
    however certain critical required fields cannot be filled in this way. These
    are fields a valid breakpoint would be expected to have populated.
    """
    bp_missing_id = copy.deepcopy(SNAPSHOT_ACTIVE)
    bp_missing_id = copy.deepcopy(SNAPSHOT_ACTIVE)
    bp_missing_location = copy.deepcopy(SNAPSHOT_ACTIVE)
    bp_missing_path = copy.deepcopy(SNAPSHOT_ACTIVE)
    bp_missing_line = copy.deepcopy(SNAPSHOT_ACTIVE)

    del bp_missing_id['id']
    del bp_missing_location['location']
    del bp_missing_path['location']['path']
    del bp_missing_line['location']['line']

    # Sanity check the bp we're using as a base is valid.
    self.assertIsNotNone(normalize_breakpoint(SNAPSHOT_ACTIVE))

    self.assertIsNone(normalize_breakpoint(None))
    self.assertIsNone(normalize_breakpoint(bp_missing_id))
    self.assertIsNone(normalize_breakpoint(bp_missing_location))
    self.assertIsNone(normalize_breakpoint(bp_missing_path))
    self.assertIsNone(normalize_breakpoint(bp_missing_line))

  def test_normalize_breakpoint_fills_in_expected_missing_fields(self):
    # To note, we're using a completed snapshot here since finalTime will only
    # be polpulated if the breakpoint is final.

    testcases = [
        # (Test name, missing field, expected fill in value)
        ('Action', 'action', 'CAPTURE'),
        ('Is Final State', 'isFinalState', False),
        ('Create Time Unix Msec', 'createTimeUnixMsec', 0),
        ('Final Time Unix Msec', 'finalTimeUnixMsec', 0),
        ('Create Time', 'createTime', SNAPSHOT_COMPLETE['createTime']),
        ('Final Time', 'finalTime', SNAPSHOT_COMPLETE['finalTime']),
        ('User Email', 'userEmail', 'unknown'),
    ]

    for test_name, missing_field, expected_field_value in testcases:
      with self.subTest(test_name):
        bp = copy.deepcopy(SNAPSHOT_COMPLETE)
        del bp[missing_field]
        self.assertNotIn(missing_field, bp)

        obtained_bp = normalize_breakpoint(bp)

        # It's expected the same instance is returned.
        self.assertIs(obtained_bp, bp)
        self.assertIn(missing_field, obtained_bp)
        self.assertEqual(expected_field_value, obtained_bp[missing_field])

  def test_normalize_breakpoint_final_time_not_populated_on_active_bp(self):
    bp = copy.deepcopy(SNAPSHOT_ACTIVE)

    self.assertFalse(bp['isFinalState'])
    self.assertNotIn('finalTimeUnixMsec', bp)
    self.assertNotIn('finalTime', bp)

    obtained_bp = normalize_breakpoint(bp)

    self.assertNotIn('finalTimeUnixMsec', obtained_bp)
    self.assertNotIn('finalTime', obtained_bp)

  def test_normalize_breakpoint_populates_id_if_provided(self):
    bp = copy.deepcopy(SNAPSHOT_ACTIVE)

    del bp['id']
    self.assertNotIn('id', bp)

    obtained_bp = normalize_breakpoint(bp, bpid='b-123')

    self.assertIn('id', obtained_bp)
    self.assertEqual('b-123', obtained_bp['id'])

  def test_split_log_expressions_no_expressions(self):
    self.assertEqual(split_log_expressions('Hi there.'), ('Hi there.', []))

  def test_split_log_expressions_simple(self):
    self.assertEqual(
        split_log_expressions('a={a}, b={b}, c={c}'),
        ('a=$0, b=$1, c=$2', ['a', 'b', 'c']))

  def test_split_log_expressions_escaped_dollar(self):
    self.assertEqual(
        split_log_expressions('$ {abc$}$ $0'), ('$$ $0$$ $$0', ['abc$']))

  def test_split_log_expressions_repeated_field(self):
    self.assertEqual(
        split_log_expressions('a={a}, b={b}, a={a}, c={c}, b={b}'),
        ('a=$0, b=$1, a=$0, c=$2, b=$1', ['a', 'b', 'c']))

  def test_split_log_expressions_nested_braces(self):
    self.assertEqual(
        split_log_expressions('a={{a} and {b}}, b={a{b{{cde}f}}g}'),
        ('a=$0, b=$1', ['{a} and {b}', 'a{b{{cde}f}}g']))

  def test_split_log_expressions_trailing_numbers(self):
    self.assertEqual(split_log_expressions('a={abc}100'), ('a=$0 100', ['abc']))

  def test_split_log_expressions_unbalanced_right(self):
    with self.assertRaisesRegex(ValueError, 'too many'):
      split_log_expressions('a={abc}}')

  def test_split_log_expressions_unbalanced_left(self):
    with self.assertRaisesRegex(ValueError, 'too many'):
      split_log_expressions('a={{a}')
