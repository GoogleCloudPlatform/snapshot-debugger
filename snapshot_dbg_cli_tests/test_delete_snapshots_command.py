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
""" Unit test file for the DeleteSnapshotsCommand class.
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
from snapshot_dbg_cli.user_input import UserInput
from snapshot_dbg_cli.user_output import UserOutput

from io import StringIO
from unittest.mock import ANY
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch

SNAPSHOT_ACTIVE =  {
  'action': 'CAPTURE',
  'createTimeUnixMsec': 1649962215426,
  'id': 'b-1650000000',
  'isFinalState': False,
  'location': {'line': 26, 'path': 'index.js'},
  'userEmail': 'user@foo.com',
  'createTime': '2022-04-14T18:50:15Z',
} # yapf: disable (Subjectively, more readable hand formatted)

SNAPSHOT_WITH_CONDITION =  {
  'action': 'CAPTURE',
  'condition': 'a == 3',
  'createTimeUnixMsec': 1649962215426,
  'id': 'b-1650000001',
  'isFinalState': False,
  'location': {'line': 27, 'path': 'index.js'},
  'userEmail': 'user@foo.com',
  'createTime': '2022-04-14T18:50:15Z',
} # yapf: disable (Subjectively, more readable hand formatted)


SNAPSHOT_COMPLETED =  {
  'action': 'CAPTURE',
  'createTimeUnixMsec': 1649962215426,
  'id': 'b-1650000002',
  'isFinalState': True,
  'location': {'line': 28, 'path': 'index.js'},
  'userEmail': 'user@foo.com',
  'createTime': '2022-04-14T18:50:15Z',
} # yapf: disable (Subjectively, more readable hand formatted)

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

class DeleteSnapshotsCommandTests(unittest.TestCase):
  """ Contains the unit tests for the DeleteSnapshotsCommand class.
  """

  def setUp(self):
    self.cli_services = MagicMock(spec=CliServices)

    self.user_input_mock = MagicMock(spec=UserInput)
    self.cli_services.user_input = self.user_input_mock

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

    # Just setup some sane defaults. Tests that care about these values and need
    # different behaviour will simply overrite as needed.
    self.cli_services.account = 'foo@bar.com'
    self.user_input_mock.prompt_user_to_continue = MagicMock(return_value=True)
    self.rtdb_service_mock.get_breakpoint = MagicMock(return_value=None)
    self.rtdb_service_mock.get_snapshots = MagicMock(return_value=[])

  def run_cmd(self, testargs, expected_exception=None):
    args = ['cli-test', 'delete_snapshots'] + testargs

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

  def test_debuggee_id_is_required(self):
    testargs = []

    # debuggee-id should be a required parameter, the argparse library should
    # enforce this and use SystemExit if it's not found.
    out, err = self.run_cmd(testargs, expected_exception=SystemExit)

    self.assertIn('error: the following arguments are required: --debuggee-id',
                  err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_validate_debuggee_id_called_as_expected(self):
    testargs = ['--debuggee-id=123']
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(
        side_effect=SilentlyExitError())

    self.run_cmd(testargs, expected_exception=SilentlyExitError)

    self.rtdb_service_mock.validate_debuggee_id.assert_called_once_with('123')
    self.rtdb_service_mock.delete_breakpoints.assert_not_called()

  def test_one_id_specified_and_exists_gets_deleted(self):
    testargs = ['--debuggee-id=123', 'b-1650000000']

    self.rtdb_service_mock.get_breakpoint = MagicMock(
        return_value=SNAPSHOT_ACTIVE)

    self.run_cmd(testargs)

    self.rtdb_service_mock.get_breakpoint.assert_called_once_with(
        '123', 'b-1650000000')
    self.rtdb_service_mock.delete_breakpoints.assert_called_once_with(
        '123', [SNAPSHOT_ACTIVE])

  def test_id_specified_matches_logpoint_and_not_snapshot(self):
    """Verifies users can't delete logpoints through this command.
    """
    testargs = ['--debuggee-id=123', 'b-1649962215']

    self.rtdb_service_mock.get_breakpoint = MagicMock(
        return_value=LOGPOINT_ACTIVE)

    out, err = self.run_cmd(testargs, expected_exception=SilentlyExitError)

    self.rtdb_service_mock.get_breakpoint.assert_called_once_with(
        '123', 'b-1649962215')
    self.rtdb_service_mock.delete_breakpoints.assert_not_called()
    self.assertEqual('Snapshot ID not found: b-1649962215\n', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_multiple_ids_specified_and_exist_get_deleted(self):
    testargs = [
        '--debuggee-id=123', 'b-1650000000', 'b-1650000001', 'b-1650000002'
    ]

    self.rtdb_service_mock.get_breakpoint = MagicMock(side_effect=[
        SNAPSHOT_ACTIVE, SNAPSHOT_WITH_CONDITION, SNAPSHOT_COMPLETED
    ])

    self.run_cmd(testargs)

    self.rtdb_service_mock.get_breakpoint.assert_has_calls([
        call('123', 'b-1650000000'),
        call('123', 'b-1650000001'),
        call('123', 'b-1650000002')
    ])

    self.rtdb_service_mock.delete_breakpoints.assert_called_once_with(
        '123', [SNAPSHOT_ACTIVE, SNAPSHOT_WITH_CONDITION, SNAPSHOT_COMPLETED])

  def test_one_id_specified_and_not_found(self):
    testargs = ['--debuggee-id=123', 'b-1650000000']

    self.rtdb_service_mock.get_breakpoint = MagicMock(return_value=None)

    out, err = self.run_cmd(testargs, expected_exception=SilentlyExitError)

    self.rtdb_service_mock.delete_breakpoints.assert_not_called()
    self.assertEqual('Snapshot ID not found: b-1650000000\n', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_multiple_ids_specified_and_some_not_found(self):
    testargs = [
        '--debuggee-id=123', 'b-1650000000', 'b-1650000001', 'b-1650000002'
    ]

    self.rtdb_service_mock.get_breakpoint = MagicMock(
        side_effect=[None, SNAPSHOT_WITH_CONDITION, None])

    out, err = self.run_cmd(testargs, expected_exception=SilentlyExitError)

    self.rtdb_service_mock.delete_breakpoints.assert_not_called()
    self.assertEqual('Snapshot ID not found: b-1650000000, b-1650000002\n',
                     err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_queried_snapshots_uses_correct_debuggee_id(self):
    testargs = ['--debuggee-id=123']

    self.run_cmd(testargs)

    self.rtdb_service_mock.get_snapshots.assert_called_once_with(
        '123', ANY, ANY)

  def test_queried_snapshots_uses_correct_include_inactive(self):
    testcases = [
        # (Test name, testargs, expected include_inactive)
        ('Default Active Only', ['--debuggee-id=123'], False),
        ('Incude Inactive', ['--debuggee-id=123', '--include-inactive'], True),
    ]

    for test_name, testargs, expected_include_inactive in testcases:
      with self.subTest(test_name):
        self.rtdb_service_mock.reset_mock()
        self.run_cmd(testargs)
        self.rtdb_service_mock.get_snapshots.assert_called_once_with(
            ANY, expected_include_inactive, ANY)

  def test_queried_snapshots_uses_correct_account(self):
    self.cli_services.account = 'cli-test@foo.com'

    testcases = [
        # (Test name, testargs, expected include_inactive)
        ('Default User Only', ['--debuggee-id=123'], 'cli-test@foo.com'),
        ('All Users', ['--debuggee-id=123', '--all-users'], None),
    ]

    for test_name, testargs, expected_user_email in testcases:
      with self.subTest(test_name):
        self.rtdb_service_mock.reset_mock()
        self.run_cmd(testargs)
        self.rtdb_service_mock.get_snapshots.assert_called_once_with(
            ANY, ANY, expected_user_email)

  def test_user_prompted_with_snapshot_summary_before_delete(self):
    testargs = ['--debuggee-id=123']

    snapshot_without_condition = SNAPSHOT_ACTIVE
    self.assertNotIn('condition', snapshot_without_condition)

    testcases = [
        ('Active', [SNAPSHOT_ACTIVE],
         [['ACTIVE', 'index.js:26', '', 'b-1650000000']]),
        ('Without Condition', [snapshot_without_condition],
         [['ACTIVE', 'index.js:26', '', 'b-1650000000']]),
        ('With Condition', [SNAPSHOT_WITH_CONDITION],
         [['ACTIVE', 'index.js:27', 'a == 3', 'b-1650000001']]),
        ('Completed', [SNAPSHOT_COMPLETED],
         [['COMPLETED', 'index.js:28', '', 'b-1650000002']]),
        ('Multiple',
         [SNAPSHOT_ACTIVE, SNAPSHOT_WITH_CONDITION, SNAPSHOT_COMPLETED
         ], [['ACTIVE', 'index.js:26', '', 'b-1650000000'],
             ['ACTIVE', 'index.js:27', 'a == 3', 'b-1650000001'],
             ['COMPLETED', 'index.js:28', '', 'b-1650000002']])
    ]

    for test_name, snapshots, expected_rows in testcases:
      with self.subTest(test_name):
        self.user_input_mock.reset_mock()
        self.user_output_mock.reset_mock()

        self.rtdb_service_mock.get_snapshots = MagicMock(return_value=snapshots)
        self.run_cmd(testargs)

        self.user_output_mock.normal.assert_any_call(
            'This command will delete the following snapshots:\n')
        self.user_output_mock.tabular.assert_called_with(
            ['Status', 'Location', 'Condition', 'ID'], expected_rows)

        self.user_input_mock.prompt_user_to_continue.assert_called_once()

  def test_user_prompted_before_delete_answers_no(self):
    testargs = ['--debuggee-id=123']
    self.rtdb_service_mock.get_snapshots = MagicMock(
        return_value=[SNAPSHOT_ACTIVE])

    # Returning False means user said no.
    self.user_input_mock.prompt_user_to_continue = MagicMock(return_value=False)

    self.run_cmd(testargs)

    self.rtdb_service_mock.delete_breakpoints.assert_not_called()
    self.user_input_mock.prompt_user_to_continue.assert_called_once()

  def test_user_prompted_before_delete_answers_yes(self):
    testargs = ['--debuggee-id=123']
    self.rtdb_service_mock.get_snapshots = MagicMock(
        return_value=[SNAPSHOT_ACTIVE])
    self.user_input_mock.prompt_user_to_continue = MagicMock(return_value=True)

    self.run_cmd(testargs)

    self.rtdb_service_mock.delete_breakpoints.assert_called_once()
    self.user_input_mock.prompt_user_to_continue.assert_called_once()

  def test_user_uses_quiet_mode_to_avoid_prompt(self):
    testargs = ['--debuggee-id=123', '--quiet']
    self.rtdb_service_mock.get_snapshots = MagicMock(
        return_value=[SNAPSHOT_ACTIVE])
    self.run_cmd(testargs)

    self.rtdb_service_mock.delete_breakpoints.assert_called_once()
    self.user_input_mock.prompt_user_to_continue.assert_not_called()

  def test_no_snapshots_found_delete_not_called(self):
    testargs = ['--debuggee-id=123', '--quiet']
    self.rtdb_service_mock.get_snapshots = MagicMock(return_value=[])
    self.run_cmd(testargs)

    self.rtdb_service_mock.delete_breakpoints.assert_not_called()
    self.rtdb_service_mock.get_snapshots.assert_called_once()

  def test_delete_results_output_format_default(self):
    testargs = ['--debuggee-id=123']

    testcases = [
        ('No Snapshots', [], 0), ('One Snapshot', [SNAPSHOT_ACTIVE], 1),
        ('Multiple Snapshots',
         [SNAPSHOT_ACTIVE, SNAPSHOT_WITH_CONDITION, SNAPSHOT_COMPLETED], 3)
    ]

    for test_name, snapshots, expected_deleted_count in testcases:
      with self.subTest(test_name):
        self.rtdb_service_mock.get_snapshots = MagicMock(return_value=snapshots)
        out, err = self.run_cmd(testargs)

        self.assertIn(f'Deleted {expected_deleted_count} snapshots',
                      err.getvalue())
        self.assertEqual('', out.getvalue())

  def test_delete_results_output_format_json(self):
    testargs = ['--debuggee-id=123', '--format=json']

    testcases = [
        ('No Snapshots', [], 0), ('One Snapshot', [SNAPSHOT_ACTIVE], 1),
        ('Multiple Snapshots',
         [SNAPSHOT_ACTIVE, SNAPSHOT_WITH_CONDITION, SNAPSHOT_COMPLETED], 3)
    ]

    for test_name, snapshots, expected_deleted_count in testcases:
      with self.subTest(test_name):
        self.user_output_mock.reset_mock()

        self.rtdb_service_mock.get_snapshots = MagicMock(return_value=snapshots)
        out, err = self.run_cmd(testargs)

        self.user_output_mock.json_format.assert_called_once_with(
            snapshots, pretty=False)
        self.assertIn(f'Deleted {expected_deleted_count} snapshots',
                      err.getvalue())
        self.assertEqual(snapshots, json.loads(out.getvalue()))

  def test_delete_results_output_format_pretty_json(self):
    testargs = ['--debuggee-id=123', '--format=pretty-json']

    testcases = [
        ('No Snapshots', [], 0), ('One Snapshot', [SNAPSHOT_ACTIVE], 1),
        ('Multiple Snapshots',
         [SNAPSHOT_ACTIVE, SNAPSHOT_WITH_CONDITION, SNAPSHOT_COMPLETED], 3)
    ]

    for test_name, snapshots, expected_deleted_count in testcases:
      with self.subTest(test_name):
        self.user_output_mock.reset_mock()

        self.rtdb_service_mock.get_snapshots = MagicMock(return_value=snapshots)
        out, err = self.run_cmd(testargs)

        self.user_output_mock.json_format.assert_called_once_with(
            snapshots, pretty=True)
        self.assertIn(f'Deleted {expected_deleted_count} snapshots',
                      err.getvalue())
        self.assertEqual(snapshots, json.loads(out.getvalue()))
