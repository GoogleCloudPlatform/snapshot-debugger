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
""" Unit test file for the GetLogpoint class.
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
  'createTime': '2022-04-14T18:50:15Z',
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
  'createTime': '2022-04-14T18:50:17Z',
  'finalTime': '2022-04-14T18:50:31Z',
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
  'id': 'b-1649962218',
  'isFinalState': True,
  'location': {'line': 29, 'path': 'index.js'},
  'userEmail': 'user_d@foo.com',
  'createTime': '2022-04-14T18:50:18Z',
  'finalTime': '2022-04-14T18:50:31Z',
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
  'createTime': '2022-04-14T18:50:19Z',
} # yapf: disable (Subjectively, more readable hand formatted)

SNAPSHOT_ACTIVE =  {
  'action': 'CAPTURE',
  'createTimeUnixMsec': 1649962215426,
  'condition': 'a == 3',
  'expressions': ['a', 'b', 'a+b'],
  'id': 'b-1649962215',
  'isFinalState': False,
  'location': {'line': 26, 'path': 'index.js'},
  'userEmail': 'foo@bar.com',
  'createTime': '2022-04-14T18:50:15Z',
} # yapf: disable (Subjectively, more readable hand formatted)

class GetLogpointTests(unittest.TestCase):
  """ Contains the unit tests for the GetLogpoint class.
  """

  def setUp(self):
    self.cli_services = MagicMock(spec=CliServices)

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
    args = ['cli-test', 'get_logpoint'] + testargs

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
    testargs = ['b-111', '--debuggee-id=123']
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(
        side_effect=SilentlyExitError())

    self.run_cmd(testargs, expected_exception=SilentlyExitError)

    self.rtdb_service_mock.validate_debuggee_id.assert_called_once_with('123')
    self.rtdb_service_mock.get_breakpoint.assert_not_called()

  def test_get_breakpoint_called_as_expected(self):
    testargs = ['b-111', '--debuggee-id=123']
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)
    self.rtdb_service_mock.get_breakpoint = MagicMock(
        return_value=LOGPOINT_ACTIVE)

    self.run_cmd(testargs)

    self.rtdb_service_mock.get_breakpoint.assert_called_once_with(
        '123', 'b-111')

  def test_logpoint_not_found_works_as_expected(self):
    testargs = ['b-111', '--debuggee-id=123']
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)
    self.rtdb_service_mock.get_logpoint = MagicMock(return_value=None)

    out, err = self.run_cmd(testargs, expected_exception=SilentlyExitError)

    self.user_output_mock.error.assert_called_once()
    self.assertEqual('Logpoint ID not found: b-111\n', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_id_matches_a_snapshot_not_a_logpoint(self):
    testargs = ['b-111', '--debuggee-id=123']
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)
    self.rtdb_service_mock.get_logpoint = MagicMock(
        return_value=SNAPSHOT_ACTIVE)

    out, err = self.run_cmd(testargs, expected_exception=SilentlyExitError)

    self.user_output_mock.error.assert_called_once()
    self.assertEqual('Logpoint ID not found: b-111\n', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_output_format_json(self):
    testargs = [LOGPOINT_EXPIRED['id'], '--debuggee-id=123', '--format=json']
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)
    self.rtdb_service_mock.get_breakpoint = MagicMock(
        return_value=LOGPOINT_EXPIRED)

    out, err = self.run_cmd(testargs)

    self.user_output_mock.json_format.assert_called_once_with(
        LOGPOINT_EXPIRED, pretty=False)
    self.assertEqual('', err.getvalue())
    self.assertEqual(LOGPOINT_EXPIRED, json.loads(out.getvalue()))

  def test_output_format_pretty_json(self):
    testargs = [
        LOGPOINT_EXPIRED['id'], '--debuggee-id=123', '--format=pretty-json'
    ]
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)
    self.rtdb_service_mock.get_breakpoint = MagicMock(
        return_value=LOGPOINT_EXPIRED)

    out, err = self.run_cmd(testargs)

    self.user_output_mock.json_format.assert_called_once_with(
        LOGPOINT_EXPIRED, pretty=True)

    self.assertEqual('', err.getvalue())
    self.assertEqual(LOGPOINT_EXPIRED, json.loads(out.getvalue()))

  def test_logpoint_summary_is_as_expected(self):
    logpoint_active = LOGPOINT_ACTIVE
    logpoint_with_condition = LOGPOINT_WITH_CONDITION

    logpoint_without_condition = logpoint_with_condition.copy()
    del logpoint_without_condition['condition']

    # The field is present, but empty
    logpoint_condition_empty = logpoint_with_condition.copy()
    logpoint_condition_empty['condition'] = ''

    logpoint_expired = LOGPOINT_EXPIRED
    logpoint_failed = LOGPOINT_FAILED

    logpoint_user_email_missing = logpoint_active.copy()
    del logpoint_user_email_missing['userEmail']

    expected_summary_active = ('Logpoint ID:        b-1649962215\n'
                               'Log Message Format: a: {a}\n'
                               'Location:           index.js:26\n'
                               'Condition:          No condition set\n'
                               'Status:             ACTIVE\n'
                               'Create Time:        2022-04-14T18:50:15Z\n'
                               'Final Time:         \n'
                               'User Email:         user_a@foo.com\n')

    expected_summary_with_condition = (
        'Logpoint ID:        b-1649962219\n'
        'Log Message Format: e: {e}\n'
        'Location:           index.js:30\n'
        'Condition:          a == 3\n'
        'Status:             ACTIVE\n'
        'Create Time:        2022-04-14T18:50:19Z\n'
        'Final Time:         \n'
        'User Email:         user_e@foo.com\n')

    expected_summary_without_condition = (
        'Logpoint ID:        b-1649962219\n'
        'Log Message Format: e: {e}\n'
        'Location:           index.js:30\n'
        'Condition:          No condition set\n'
        'Status:             ACTIVE\n'
        'Create Time:        2022-04-14T18:50:19Z\n'
        'Final Time:         \n'
        'User Email:         user_e@foo.com\n')

    # It's expectd they are the same, the condition field missing or being
    # present but empty should produce the same result.
    expected_summary_condition_empty = expected_summary_without_condition

    expected_summary_expired = ('Logpoint ID:        b-1649962217\n'
                                'Log Message Format: c: {c}\n'
                                'Location:           index.js:28\n'
                                'Condition:          No condition set\n'
                                'Status:             EXPIRED\n'
                                'Create Time:        2022-04-14T18:50:17Z\n'
                                'Final Time:         2022-04-14T18:50:31Z\n'
                                'User Email:         user_c@foo.com\n')

    expected_summary_failed = (
        'Logpoint ID:        b-1649962218\n'
        'Log Message Format: d: {d}\n'
        'Location:           index.js:29\n'
        'Condition:          No condition set\n'
        'Status:             SOURCE_LOCATION: No code found at line 29\n'
        'Create Time:        2022-04-14T18:50:18Z\n'
        'Final Time:         2022-04-14T18:50:31Z\n'
        'User Email:         user_d@foo.com\n')

    expected_summary_user_email_missing = (
        'Logpoint ID:        b-1649962215\n'
        'Log Message Format: a: {a}\n'
        'Location:           index.js:26\n'
        'Condition:          No condition set\n'
        'Status:             ACTIVE\n'
        'Create Time:        2022-04-14T18:50:15Z\n'
        'Final Time:         \n'
        'User Email:         \n')

    testcases = [
        ('Active', logpoint_active, expected_summary_active),
        ('With Condition', logpoint_with_condition,
         expected_summary_with_condition),
        ('Without Condition', logpoint_without_condition,
         expected_summary_without_condition),
        ('Condition Empty', logpoint_condition_empty,
         expected_summary_condition_empty),
        ('Expired', logpoint_expired, expected_summary_expired),
        ('Failed', logpoint_failed, expected_summary_failed),
        ('User Email Missing', logpoint_user_email_missing,
         expected_summary_user_email_missing),
    ]

    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)

    for test_name, logpoint, expected_summary in testcases:
      with self.subTest(test_name):
        self.rtdb_service_mock.get_breakpoint = MagicMock(return_value=logpoint)

        testargs = [logpoint['id'], '--debuggee-id=123']
        out, err = self.run_cmd(testargs)

        self.assertEqual(expected_summary, err.getvalue())
        self.assertEqual('', out.getvalue())
