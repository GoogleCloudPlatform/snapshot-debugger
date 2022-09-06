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
""" Unit test file for the ListLogpointsCommand class.
"""

import os
import sys
import json
import unittest
from io import StringIO

from snapshot_dbg_cli import cli_run
from snapshot_dbg_cli import data_formatter
from snapshot_dbg_cli.cli_services import CliServices
from snapshot_dbg_cli.snapshot_debugger_rtdb_service import SnapshotDebuggerRtdbService
from snapshot_dbg_cli.user_output import UserOutput

from snapshot_dbg_cli.exceptions import SilentlyExitError

from unittest.mock import MagicMock
from unittest.mock import patch

TEST_ACCOUNT = 'user@foo.com'

LOGPOINT_ACTIVE =  {
  'action': 'LOG',
  'logMessageFormat': 'a: $0',
  'expressions': ['a'],
  'logMessageFormatString': 'a: {a}',
  'logLevel': 'INFO',
  'createTimeUnixMsec': 1649962215426,
  'id': 'b-1649962215',
  'isFinalState': False,
  'location': {'line': 26, 'path': 'index.js'},
  'userEmail': 'user_a@foo.com',
  'createTime': '2022-04-14T18:50:15.852000Z',
} # yapf: disable (Subjectively, more readable hand formatted)

# NOTE: It would actually be unexpected to receive a logpoint that is complete
# in this sense. Generally a successful logpoint that 'completes' actually
# expires, so it would be marked as failed with reason BREAKPOINT_AGE. But for
# testing purposes we include this complete logpoint still.
LOGPOINT_COMPLETE =  {
  'action': 'LOG',
  'logMessageFormat': 'b: $0',
  'expressions': ['b'],
  'logMessageFormatString': 'b: {b}',
  'logLevel': 'WARNING',
  'createTimeUnixMsec': 1649962216426,
  'finalTimeUnixMsec': 1649962230637,
  'id': 'b-1649962216',
  'isFinalState': True,
  'location': {'line': 27, 'path': 'index.js'},
  'userEmail': 'user_b@foo.com',
  'createTime': '2022-04-14T18:50:16.852000Z',
  'finalTime': '2022-04-14T18:50:31.274000Z',
} # yapf: disable (Subjectively, more readable hand formatted)

LOGPOINT_EXPIRED =  {
  'action': 'LOG',
  'logMessageFormat': 'c: $0',
  'expressions': ['c'],
  'logMessageFormatString': 'c: {c}',
  'logLevel': 'ERROR',
  'createTimeUnixMsec': 1649962217426,
  'id': 'b-1649962217',
  'isFinalState': True,
  'location': {'line': 28, 'path': 'index.js'},
  'userEmail': 'user_c@foo.com',
  'createTime': '2022-04-14T18:50:17.852000Z',
  'finalTime': '2022-04-14T18:50:31.274000Z',
  'status': {
    'description': {
      'format': 'The logpoint has expired'
    },
    'isError': True,
    'refersTo': 'BREAKPOINT_AGE'
  },
} # yapf: disable (Subjectively, more readable hand formatted)

LOGPOINT_FAILED =  {
  'action': 'LOG',
  'logMessageFormat': 'd: $0',
  'expressions': ['d'],
  'logMessageFormatString': 'd: {d}',
  'logLevel': 'INFO',
  'createTimeUnixMsec': 1649962218426,
  'condition': '',
  'id': 'b-1649962218',
  'isFinalState': True,
  'location': {'line': 29, 'path': 'index.js'},
  'userEmail': 'user_d@foo.com',
  'createTime': '2022-04-14T18:50:18.852000Z',
  'finalTime': '2022-04-14T18:50:31.274000Z',
  'status': {
    'description': {
        'format': 'No code found at line 29'
    },
    'isError': True,
    'refersTo': 'BREAKPOINT_SOURCE_LOCATION'
  },
} # yapf: disable (Subjectively, more readable hand formatted)

LOGPOINT_WITH_CONDITION =  {
  'action': 'LOG',
  'logMessageFormat': 'e: $0',
  'expressions': ['e'],
  'logMessageFormatString': 'e: {e}',
  'logLevel': 'WARNING',
  'createTimeUnixMsec': 1649962219426,
  'condition': 'a == 3',
  'id': 'b-1649962219',
  'isFinalState': False,
  'location': {'line': 30, 'path': 'index.js'},
  'userEmail': 'user_e@foo.com',
  'createTime': '2022-04-14T18:50:19.852000Z',
} # yapf: disable (Subjectively, more readable hand formatted)

class ListLogpointTests(unittest.TestCase):
  """ Contains the unit tests for the ListLogpoints class.
  """

  def setUp(self):
    self.cli_services = MagicMock(spec=CliServices)

    self.cli_services.account = TEST_ACCOUNT
    self.data_formatter = data_formatter.DataFormatter()
    self.cli_services.data_formatter = self.data_formatter

    # By wrapping a real UserOutput instance, we can test the method calls etc,
    # and it will still perform the actual stdout/stderr output which we can
    # also check when desired.
    self.user_output_mock = MagicMock(
        wraps=UserOutput(
            is_debug_enabled=False,
            data_formatter=data_formatter.DataFormatter()))
    self.cli_services.user_output = self.user_output_mock

    self.rtdb_service_mock = MagicMock(spec=SnapshotDebuggerRtdbService)
    self.cli_services.get_snapshot_debugger_rtdb_service = MagicMock(
        return_value=self.rtdb_service_mock)

  def run_cmd(self, testargs, expected_exception=None):
    args = ['cli-test', 'list_logpoints'] + testargs

    # We patch os.environ as some cli arguments can come from environment
    # variables, and if they happen to be set in the terminal running the tests
    # it will affect things.
    with patch.object(sys, 'argv', args), \
         patch.dict(os.environ, {}, clear=True), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      if expected_exception is not None:
        with self.assertRaises(expected_exception):
          cli_run.run(self.cli_services)
      else:
        cli_run.run(self.cli_services)

    return out, err

  def test_validate_debuggee_id_called_as_expected(self):
    testargs = ['--debuggee-id=123']
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(
        side_effect=SilentlyExitError())

    self.run_cmd(testargs, expected_exception=SilentlyExitError)

    self.rtdb_service_mock.validate_debuggee_id.assert_called_once_with('123')
    self.rtdb_service_mock.get_logpoints.assert_not_called()

  def test_get_logpoints_called_as_expected(self):
    testcases = [
        (
            'Defaults',
            ['--debuggee-id=123'],
            {
                'debuggee_id': '123',
                'include_inactive': False,
                # By default --all-users is enabled, so no email filtering
                # should be done
                'user_email': None
            }
        ),
        (
            'All Users Specified',
            ['--debuggee-id=123', '--all-users'],
            {
                'debuggee_id': '123',
                'include_inactive': False,
                'user_email': None
            }
        ),
        (
            'No All Users Specified',
            ['--debuggee-id=123', '--no-all-users'],
            {
                'debuggee_id': '123',
                'include_inactive': False,
                'user_email': TEST_ACCOUNT
            }
        ),
        (
            'Include Inactive Specified',
            ['--debuggee-id=123', '--include-inactive'],
            {
                'debuggee_id': '123',
                'include_inactive': True,
                'user_email': None
            }
        )
    ] # yapf: disable

    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)
    self.rtdb_service_mock.get_logpoints = MagicMock(return_value=[])

    for test_name, testargs, expected_params in testcases:
      with self.subTest(test_name):
        self.rtdb_service_mock.reset_mock()
        self.run_cmd(testargs)

        self.rtdb_service_mock.get_logpoints.assert_called_once_with(
            **expected_params)

  def test_output_format_json(self):
    testcases = [
        ('No Logpoints', []),
        ('One Logpoint', [LOGPOINT_ACTIVE]),
        ('Multi Logpoints', [
            LOGPOINT_ACTIVE, LOGPOINT_COMPLETE, LOGPOINT_EXPIRED,
            LOGPOINT_FAILED
        ]),
    ]

    for test_name, logpoints in testcases:
      with self.subTest(test_name):
        self.user_output_mock.reset_mock()

        testargs = ['--debuggee-id=123', '--format=json']
        self.rtdb_service_mock.get_logpoints = MagicMock(return_value=logpoints)

        out, err = self.run_cmd(testargs)

        self.user_output_mock.json_format.assert_called_once_with(
            logpoints, pretty=False)
        self.assertEqual('', err.getvalue())
        self.assertEqual(logpoints, json.loads(out.getvalue()))

  def test_output_format_json_pretty(self):
    testcases = [
        ('No Logpoints', []),
        ('One Logpoint', [LOGPOINT_ACTIVE]),
        ('Multi Logpoints', [
            LOGPOINT_ACTIVE, LOGPOINT_COMPLETE, LOGPOINT_EXPIRED,
            LOGPOINT_FAILED
        ]),
    ]

    for test_name, logpoints in testcases:
      with self.subTest(test_name):
        self.user_output_mock.reset_mock()

        testargs = ['--debuggee-id=123', '--format=pretty-json']
        self.rtdb_service_mock.get_logpoints = MagicMock(return_value=logpoints)

        out, err = self.run_cmd(testargs)

        self.user_output_mock.json_format.assert_called_once_with(
            logpoints, pretty=True)
        self.assertEqual('', err.getvalue())
        self.assertEqual(logpoints, json.loads(out.getvalue()))

  def test_output_default(self):
    expected_active_row = ('user_a@foo.com', 'index.js:26', '', 'INFO',
                           'a: {a}', 'b-1649962215', 'ACTIVE')
    expected_completed_row = ('user_b@foo.com', 'index.js:27', '', 'WARNING',
                              'b: {b}', 'b-1649962216', 'COMPLETED')
    expected_expired_row = ('user_c@foo.com', 'index.js:28', '', 'ERROR',
                            'c: {c}', 'b-1649962217', 'EXPIRED')
    expected_failed_row = ('user_d@foo.com', 'index.js:29', '', 'INFO',
                           'd: {d}', 'b-1649962218',
                           'SOURCE_LOCATION: No code found at line 29')
    expected_with_condition_row = ('user_e@foo.com', 'index.js:30', 'a == 3',
                                   'WARNING', 'e: {e}', 'b-1649962219',
                                   'ACTIVE')

    testcases = [
        ('No Logpoints', [], []),
        ('Active', [LOGPOINT_ACTIVE], [expected_active_row]),
        ('Completed', [LOGPOINT_COMPLETE], [expected_completed_row]),
        ('Expired', [LOGPOINT_EXPIRED], [expected_expired_row]),
        ('Failed', [LOGPOINT_FAILED], [expected_failed_row]),
        ('With Condition', [LOGPOINT_WITH_CONDITION],
         [expected_with_condition_row]),
        ('Multi', [
            LOGPOINT_ACTIVE, LOGPOINT_COMPLETE, LOGPOINT_EXPIRED,
            LOGPOINT_FAILED, LOGPOINT_WITH_CONDITION
        ], [
            expected_active_row, expected_completed_row, expected_expired_row,
            expected_failed_row, expected_with_condition_row
        ]),
    ]

    for test_name, logpoints, expected_rows in testcases:
      with self.subTest(test_name):
        testargs = ['--debuggee-id=123']
        self.rtdb_service_mock.get_logpoints = MagicMock(return_value=logpoints)
        expected_header = [
            'User Email', 'Location', 'Condition', 'Log Level',
            'Log Message Format', 'ID', 'Status'
        ]
        expected_output = self.data_formatter.build_table(
            expected_header, expected_rows) + '\n'

        out, err = self.run_cmd(testargs)

        self.assertEqual(expected_output, err.getvalue())
        self.assertEqual('', out.getvalue())
