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
""" Unit test file for the SetLogpointCommand class.
"""

import json
import os
import sys
import unittest

from snapshot_dbg_cli import cli_run
from snapshot_dbg_cli import data_formatter
from snapshot_dbg_cli.cli_services import CliServices
from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli.snapshot_debugger_rtdb_service import SnapshotDebuggerRtdbService
from snapshot_dbg_cli.user_output import UserOutput

from io import StringIO
from unittest.mock import MagicMock
from unittest.mock import patch

TEST_LOGPOINT =  {
  'action': 'LOG',
  'createTimeUnixMsec': 1649962215426,
  'condition': '',
  'expressions': ['a', 'b'],
  'logMessageFormat': ['Hi $1 my name is $2'],
  'id': 'b-1649962215',
  'isFinalState': False,
  'location': {'line': 26, 'path': 'index.js'},
  'userEmail': 'user@foo.com',
  'createTime': '2022-04-14T18:50:15Z',
} # yapf: disable (Subjectively, more readable hand formatted)


class SetLogpointCommandTests(unittest.TestCase):
  """ Contains the unit tests for the SetLogpointCommand class.
  """

  def setUp(self):
    self.cli_services = MagicMock(spec=CliServices)

    self.data_formatter = data_formatter.DataFormatter()
    self.cli_services.data_formatter = self.data_formatter

    self.user_output_mock = MagicMock(
        wraps=UserOutput(
            is_debug_enabled=False,
            data_formatter=data_formatter.DataFormatter()))
    self.cli_services.user_output = self.user_output_mock

    self.rtdb_service_mock = MagicMock(spec=SnapshotDebuggerRtdbService)
    self.cli_services.get_snapshot_debugger_rtdb_service = MagicMock(
        return_value=self.rtdb_service_mock)

    # Just setup defaults. Tests that care about these values will simply
    # overrite these with their own values.
    self.cli_services.account = 'foo@bar.com'
    self.rtdb_service_mock.get_new_breakpoint_id = MagicMock(
        return_value='b-1650000000')

  def run_cmd(self, testargs, expected_exception=None):
    args = ['cli-test', 'set_logpoint'] + testargs

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

  def test_location_is_required(self):
    testargs = ['--debuggee-id=123']

    # Location should be a required parameter, the argparse library should
    # enforce this and use SystemExit if it's not found.
    out, err = self.run_cmd(testargs, expected_exception=SystemExit)

    self.assertIn('error: the following arguments are required: LOCATION',
                  err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_log_format_string_is_required(self):
    testargs = ['foo.py:10', '--debuggee-id=123']

    # Location should be a required parameter, the argparse library should
    # enforce this and use SystemExit if it's not found.
    out, err = self.run_cmd(testargs, expected_exception=SystemExit)

    self.assertIn(
        'error: the following arguments are required: LOG_FORMAT_STRING',
        err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_debuggee_id_is_required(self):
    testargs = ['foo.py:10', 'Foo log msg']

    # Location should be a required parameter, the argparse library should
    # enforce this and use SystemExit if it's not found.
    out, err = self.run_cmd(testargs, expected_exception=SystemExit)

    self.assertIn('error: the following arguments are required: --debuggee-id',
                  err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_location_is_invalid(self):
    # Missing line number.
    testargs = ['foo.py', 'Foo log msg', '--debuggee-id=123']

    # Location validation done by the argparse library, when the location
    # is invalid it will raise SystemExit.
    out, err = self.run_cmd(testargs, expected_exception=SystemExit)

    self.assertIn('Location must be in the format file:line', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_log_format_string_is_invalid(self):
    # Unmatched brace
    testargs = ['foo.py:10', 'Foo log msg {', '--debuggee-id=123']

    # Log format string validation done by the argparse library, when the
    # log_format_string is invalid it will raise SystemExit.
    out, err = self.run_cmd(testargs, expected_exception=SystemExit)

    self.assertIn('There are too many "{" characters in the log format string',
                  err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_log_level_is_invalid(self):
    testargs = [
        'foo.py:10', 'Foo log msg', '--debuggee-id=123', '--log-level=foo'
    ]

    # Log level validation done by the argparse library, when the log-level is
    # invalid it will raise SystemExit.
    out, err = self.run_cmd(testargs, expected_exception=SystemExit)

    self.assertIn('Invalid log-level argument provided: foo', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_validate_debuggee_id_called_as_expected(self):
    testargs = ['foo.py:10', 'Foo log msg', '--debuggee-id=123']
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(
        side_effect=SilentlyExitError())

    self.run_cmd(testargs, expected_exception=SilentlyExitError)

    self.rtdb_service_mock.validate_debuggee_id.assert_called_once_with('123')
    self.rtdb_service_mock.set_breakpoint.assert_not_called()

  def test_logpoint_data_is_correct(self):
    # (Test Name, CLI Args, account, breakpoint ID),
    testcases = [
        ('Location 1', ['foo.py:10', 'Msg'], 'foo@bar.com', 'b-1650000000',
         {
             'action': 'LOG',
             'id': 'b-1650000000',
             'location': {'path': 'foo.py', 'line': 10},
             'logMessageFormat': 'Msg',
             'logLevel': 'INFO',
             'userEmail': 'foo@bar.com',
             'createTimeUnixMsec': {'.sv': 'timestamp'},
         }
        ),
        ('Location 2', ['bar.py:20', 'Msg'], 'foo@bar.com', 'b-1650000000',
         {
             'action': 'LOG',
             'id': 'b-1650000000',
             'location': {'path': 'bar.py', 'line': 20},
             'logMessageFormat': 'Msg',
             'logLevel': 'INFO',
             'userEmail': 'foo@bar.com',
             'createTimeUnixMsec': {'.sv': 'timestamp'},
         }
        ),
        ('Message no expressions', ['foo.py:10', 'Hi there!'], 'foo@bar.com',
         'b-1650000000',
         {
             'action': 'LOG',
             'id': 'b-1650000000',
             'location': {'path': 'foo.py', 'line': 10},
             'logMessageFormat': 'Hi there!',
             'logLevel': 'INFO',
             'userEmail': 'foo@bar.com',
             'createTimeUnixMsec': {'.sv': 'timestamp'},
         }
        ),
        ('Message one expression', ['foo.py:10', 'Hi there {name}!'],
         'foo@bar.com', 'b-1650000000',
         {
             'action': 'LOG',
             'id': 'b-1650000000',
             'location': {'path': 'foo.py', 'line': 10},
             'logMessageFormat': 'Hi there $0!',
             'expressions': ['name'],
             'logLevel': 'INFO',
             'userEmail': 'foo@bar.com',
             'createTimeUnixMsec': {'.sv': 'timestamp'},
         }
        ),
        ('Message multiple expressions',
         ['foo.py:10', 'Hi there {name1}, {name2} and {name3}!'], 'foo@bar.com',
         'b-1650000000',
         {
             'action': 'LOG',
             'id': 'b-1650000000',
             'location': {'path': 'foo.py', 'line': 10},
             'logMessageFormat': 'Hi there $0, $1 and $2!',
             'expressions': ['name1', 'name2', 'name3'],
             'logLevel': 'INFO',
             'userEmail': 'foo@bar.com',
             'createTimeUnixMsec': {'.sv': 'timestamp'},
         }
        ),
        ('Log level default is INFO', ['foo.py:10', 'Hi there!'], 'foo@bar.com',
         'b-1650000000',
         {
             'action': 'LOG',
             'id': 'b-1650000000',
             'location': {'path': 'foo.py', 'line': 10},
             'logMessageFormat': 'Hi there!',
             'logLevel': 'INFO',
             'userEmail': 'foo@bar.com',
             'createTimeUnixMsec': {'.sv': 'timestamp'},
         }
        ),
        ('Log level specify info',
         ['foo.py:10', 'Hi there!', '--log-level=info'], 'foo@bar.com',
         'b-1650000000',
         {
             'action': 'LOG',
             'id': 'b-1650000000',
             'location': {'path': 'foo.py', 'line': 10},
             'logMessageFormat': 'Hi there!',
             'logLevel': 'INFO',
             'userEmail': 'foo@bar.com',
             'createTimeUnixMsec': {'.sv': 'timestamp'},
         }
        ),
        ('Log level specify warning',
         ['foo.py:10', 'Hi there!', '--log-level=warning'], 'foo@bar.com',
         'b-1650000000',
         {
             'action': 'LOG',
             'id': 'b-1650000000',
             'location': {'path': 'foo.py', 'line': 10},
             'logMessageFormat': 'Hi there!',
             'logLevel': 'WARNING',
             'userEmail': 'foo@bar.com',
             'createTimeUnixMsec': {'.sv': 'timestamp'},
         }
        ),
        ('Log level specify error',
         ['foo.py:10', 'Hi there!', '--log-level=error'], 'foo@bar.com',
         'b-1650000000',
         {
             'action': 'LOG',
             'id': 'b-1650000000',
             'location': {'path': 'foo.py', 'line': 10},
             'logMessageFormat': 'Hi there!',
             'logLevel': 'ERROR',
             'userEmail': 'foo@bar.com',
             'createTimeUnixMsec': {'.sv': 'timestamp'},
         }
        ),
        ('Email', ['foo.py:10', 'Msg'], 'test-email@foo.com', 'b-1650000000',
         {
             'action': 'LOG',
             'id': 'b-1650000000',
             'location': {'path': 'foo.py', 'line': 10},
             'logMessageFormat': 'Msg',
             'logLevel': 'INFO',
             'userEmail': 'test-email@foo.com',
             'createTimeUnixMsec': {'.sv': 'timestamp'},
         }
        ),
        ('Breakpoint ID', ['foo.py:10', 'Msg'], 'foo@bar.com', 'b-1651111111',
         {
             'action': 'LOG',
             'id': 'b-1651111111',
             'location': {'path': 'foo.py', 'line': 10},
             'logMessageFormat': 'Msg',
             'logLevel': 'INFO',
             'userEmail': 'foo@bar.com',
             'createTimeUnixMsec': {'.sv': 'timestamp'},
         }
        ),
        ('Condition 1', ['foo.py:10', 'Msg', '--condition', 'a == 3'],
         'foo@bar.com', 'b-1650000000',
         {
             'action': 'LOG',
             'id': 'b-1650000000',
             'location': {'path': 'foo.py', 'line': 10},
             'logMessageFormat': 'Msg',
             'logLevel': 'INFO',
             'userEmail': 'foo@bar.com',
             'createTimeUnixMsec': {'.sv': 'timestamp'},
             'condition': 'a == 3'
         }
        ),
        ('Condition 2', ['foo.py:10', 'Msg', '--condition', 'b == 9'],
         'foo@bar.com', 'b-1650000000',
         {
             'action': 'LOG',
             'id': 'b-1650000000',
             'location': {'path': 'foo.py', 'line': 10},
             'logMessageFormat': 'Msg',
             'logLevel': 'INFO',
             'userEmail': 'foo@bar.com',
             'createTimeUnixMsec': {'.sv': 'timestamp'},
             'condition': 'b == 9'
         }
        ),
        ('Full',
         [
             'foo.py:10',
             'a={a}, b={b}',
             '--condition', 'a == 3',
         ],
         'foo@bar.com',
         'b-1650000000',
         {
             'action': 'LOG',
             'id': 'b-1650000000',
             'location': {'path': 'foo.py', 'line': 10},
             'logMessageFormat': 'a=$0, b=$1',
             'expressions': ['a', 'b'],
             'logLevel': 'INFO',
             'userEmail': 'foo@bar.com',
             'createTimeUnixMsec': {'.sv': 'timestamp'},
             'condition': 'a == 3',
         }
        ),
    ] # yapf: disable (Subjectively, more readable hand formatted)

    for test_name, testargs, account, bp_id, expected_data in testcases:
      with self.subTest(test_name):
        self.rtdb_service_mock.set_breakpoint.reset_mock()

        testargs.append('--debuggee-id=123')

        self.cli_services.account = account
        self.rtdb_service_mock.get_new_breakpoint_id = MagicMock(
            return_value=bp_id)

        self.run_cmd(testargs)

        self.rtdb_service_mock.set_breakpoint.assert_called_once_with(
            '123', expected_data)

  def test_creation_failure_behaves_as_expected(self):
    testcases = [
        ('Default Format', []),
        ('Json Format', ['--format=json']),
        ('Pretty Json Format', ['--format=pretty-json']),
    ]

    # To note, the behaviour is expected to be the same regardless of output
    # format.
    for test_name, testargs in testcases:
      with self.subTest(test_name):
        testargs.extend(['foo.py:10', 'Foo log msg', '--debuggee-id=123'])

        self.rtdb_service_mock.set_breakpoint = MagicMock(return_value=None)

        out, err = self.run_cmd(testargs, expected_exception=SilentlyExitError)

        self.assertIn(
            'An unexpected error occurred while trying to add the logpoint.',
            err.getvalue())
        self.assertEqual('', out.getvalue())

  def test_logpoint_created_success_output_format_default(self):
    testargs = ['foo.py:10', 'Foo log msg', '--debuggee-id=123']

    # For the purpose of this test, the contents of the logpoint returned don't
    # matter, as long as it's not None. So an empty dict is sufficient.
    self.rtdb_service_mock.set_breakpoint = MagicMock(return_value={})
    self.rtdb_service_mock.get_new_breakpoint_id = MagicMock(
        return_value='b-1652222222')

    out, err = self.run_cmd(testargs)

    self.assertEqual('Successfully created logpoint with id: b-1652222222\n',
                     err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_logpoint_created_success_output_format_json(self):
    testargs = ['foo.py:10', 'Foo msg', '--debuggee-id=123', '--format=json']

    self.rtdb_service_mock.set_breakpoint = MagicMock(
        return_value=TEST_LOGPOINT)
    self.rtdb_service_mock.get_new_breakpoint_id = MagicMock(
        return_value=TEST_LOGPOINT['id'])

    out, err = self.run_cmd(testargs)

    self.user_output_mock.json_format.assert_called_once_with(
        TEST_LOGPOINT, pretty=False)
    self.assertEqual('', err.getvalue())
    self.assertEqual(TEST_LOGPOINT, json.loads(out.getvalue()))

  def test_logpoint_created_success_output_format_pretty_json(self):
    testargs = ['foo.py:10', 'Msg', '--debuggee-id=123', '--format=pretty-json']

    self.rtdb_service_mock.set_breakpoint = MagicMock(
        return_value=TEST_LOGPOINT)
    self.rtdb_service_mock.get_new_breakpoint_id = MagicMock(
        return_value=TEST_LOGPOINT['id'])

    out, err = self.run_cmd(testargs)

    self.user_output_mock.json_format.assert_called_once_with(
        TEST_LOGPOINT, pretty=True)
    self.assertEqual('', err.getvalue())
    self.assertEqual(TEST_LOGPOINT, json.loads(out.getvalue()))
