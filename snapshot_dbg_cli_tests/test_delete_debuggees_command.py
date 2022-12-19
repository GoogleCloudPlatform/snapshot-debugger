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
""" Unit test file for the DeleteDebuggeesCommand class.
"""

import copy
import json
import os
import sys
import unittest

from snapshot_dbg_cli import cli_run
from snapshot_dbg_cli import data_formatter
from snapshot_dbg_cli.cli_services import CliServices
from snapshot_dbg_cli.snapshot_debugger_rtdb_service import SnapshotDebuggerRtdbService
from snapshot_dbg_cli.user_input import UserInput
from snapshot_dbg_cli.user_output import UserOutput

from io import StringIO
from unittest.mock import ANY
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch

DEBUGGEE_ACTIVE = {
    'id': 'd-123',
    'labels': {
        'module': 'app123',
        'version': 'v1'
    },
    'description': 'desc 1',
    'displayName': 'app123 - v1',
    'activeDebuggeeEnabled': True,
    'isActive': True,
    'isStale': False,
    'registrationTimeUnixMsec': 1649962215426,
    'lastUpdateTimeUnixMsec': 1670000000000,
    'registrationTime': '2022-04-14T18:50:15Z',
    'lastUpdateTime': '2022-12-02T16:53:20Z',
}

DEBUGGEE_INACTIVE = {
    'id': 'd-456',
    'labels': {
        'module': 'app456',
        'version': 'v2'
    },
    'description': 'desc 2',
    'displayName': 'app456 - v2',
    'activeDebuggeeEnabled': True,
    'isActive': False,
    'isStale': False,
    'registrationTimeUnixMsec': 1649962215426,
    'lastUpdateTimeUnixMsec': 1669913600000,
    'registrationTime': '2022-04-14T18:50:15Z',
    'lastUpdateTime': '2022-12-01T16:53:20Z',
}

DEBUGGEE_STALE = {
    'id': 'd-789',
    'labels': {
        'module': 'app789',
        'version': 'v3'
    },
    'description': 'desc 3',
    'displayName': 'app789 - v3',
    'activeDebuggeeEnabled': True,
    'isActive': False,
    'isStale': True,
    'registrationTimeUnixMsec': 1649962215426,
    'lastUpdateTimeUnixMsec': 1669308800000,
    'registrationTime': '2022-04-14T18:50:15Z',
    'lastUpdateTime': '2022-11-24T16:53:20Z',
}

DEBUGGEE_UNKNOWN_ACTIVITY = {
    'id': 'd-100',
    'labels': {
        'module': 'app100',
        'version': 'v3'
    },
    'description': 'desc 3',
    'displayName': 'app100 - v3',
    'activeDebuggeeEnabled': False,
    'isActive': False,
    'isStale': True,
    'registrationTimeUnixMsec': 0,
    'lastUpdateTimeUnixMsec': 0,
    'registrationTime': 'not set',
    'lastUpdateTime': 'not set',
}


class DeleteDebuggeesCommandTests(unittest.TestCase):
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
    self.user_input_mock.prompt_user_to_continue = MagicMock(return_value=True)
    self.rtdb_service_mock.get_debuggee = MagicMock(return_value=None)
    self.rtdb_service_mock.get_debuggees = MagicMock(return_value=[])

  def run_cmd(self, testargs, expected_exception=None):
    args = ['cli-test', 'delete_debuggees'] + testargs

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

  def test_one_id_specified_and_exists_gets_deleted(self):
    debuggee = DEBUGGEE_ACTIVE
    testargs = [debuggee['id']]

    self.rtdb_service_mock.get_debuggee = MagicMock(return_value=debuggee)

    self.run_cmd(testargs)

    self.rtdb_service_mock.get_debuggee.assert_called_once_with(
        debuggee['id'], ANY)
    self.rtdb_service_mock.delete_debuggees.assert_called_once_with([debuggee])

  def test_multiple_ids_specified_and_exist_get_deleted(self):
    d1 = DEBUGGEE_ACTIVE
    d2 = DEBUGGEE_INACTIVE
    d3 = DEBUGGEE_STALE

    testargs = [d1['id'], d2['id'], d3['id']]

    self.rtdb_service_mock.get_debuggee = MagicMock(side_effect=[d1, d2, d3])

    self.run_cmd(testargs)

    self.assertCountEqual(
        [call(d1['id'], ANY),
         call(d2['id'], ANY),
         call(d3['id'], ANY)], self.rtdb_service_mock.get_debuggee.mock_calls)

    self.rtdb_service_mock.delete_debuggees.assert_called_once()
    self.assertCountEqual(
        [d1, d2, d3], self.rtdb_service_mock.delete_debuggees.call_args.args[0])

  def test_by_default_only_stale_debuggees_deleted(self):
    testargs = []

    self.rtdb_service_mock.get_debuggees = MagicMock(
        return_value=[DEBUGGEE_ACTIVE, DEBUGGEE_INACTIVE, DEBUGGEE_STALE])

    self.run_cmd(testargs)

    self.rtdb_service_mock.get_debuggees.assert_called_once_with(ANY)
    self.rtdb_service_mock.delete_debuggees.assert_called_once_with(
        [DEBUGGEE_STALE])

  def test_include_inactive_flag_deletes_inactive_and_stale_debuggees(self):
    testargs = ['--include-inactive']

    self.rtdb_service_mock.get_debuggees = MagicMock(
        return_value=[DEBUGGEE_ACTIVE, DEBUGGEE_INACTIVE, DEBUGGEE_STALE])

    self.run_cmd(testargs)

    self.rtdb_service_mock.get_debuggees.assert_called_once_with(ANY)
    self.assertCountEqual(
        [DEBUGGEE_INACTIVE, DEBUGGEE_STALE],
        self.rtdb_service_mock.delete_debuggees.call_args.args[0])

  def test_include_all_flag_deletes_inactive_stale_and_acitve_debuggees(self):
    testargs = ['--include-all']

    self.rtdb_service_mock.get_debuggees = MagicMock(
        return_value=[DEBUGGEE_ACTIVE, DEBUGGEE_INACTIVE, DEBUGGEE_STALE])

    self.run_cmd(testargs)

    self.rtdb_service_mock.get_debuggees.assert_called_once_with(ANY)
    self.assertCountEqual(
        [DEBUGGEE_ACTIVE, DEBUGGEE_INACTIVE, DEBUGGEE_STALE],
        self.rtdb_service_mock.delete_debuggees.call_args.args[0])

  def test_user_prompted_with_debuggee_summary_before_delete(self):
    expected_headers = ['Name', 'ID', 'Last Active', 'Status']
    expected_active_row = [
        'app123 - v1', 'd-123', '2022-12-02T16:53:20Z', 'ACTIVE'
    ]
    expected_inactive_row = [
        'app456 - v2', 'd-456', '2022-12-01T16:53:20Z', 'INACTIVE'
    ]
    expected_stale_row = [
        'app789 - v3', 'd-789', '2022-11-24T16:53:20Z', 'STALE'
    ]
    expected_unknown_activity_row = [
        'app100 - v3', 'd-100', 'not set', 'UNKNOWN'
    ]

    # Setting this flag will ensure all returned debuggees are presented for
    # deletion
    testargs = ['--include-all']

    testcases = [('Active', [DEBUGGEE_ACTIVE], [expected_active_row]),
                 ('Inactive', [DEBUGGEE_INACTIVE], [expected_inactive_row]),
                 ('Stale', [DEBUGGEE_STALE], [expected_stale_row]),
                 ('Unknown Activity', [DEBUGGEE_UNKNOWN_ACTIVITY],
                  [expected_unknown_activity_row]),
                 ('Multiple', [
                     DEBUGGEE_ACTIVE, DEBUGGEE_INACTIVE, DEBUGGEE_STALE,
                     DEBUGGEE_UNKNOWN_ACTIVITY
                 ], [
                     expected_active_row, expected_inactive_row,
                     expected_stale_row, expected_unknown_activity_row
                 ])]

    for test_name, debuggees, expected_rows in testcases:
      with self.subTest(test_name):
        self.user_input_mock.reset_mock()
        self.user_output_mock.reset_mock()

        self.rtdb_service_mock.get_debuggees = MagicMock(return_value=debuggees)
        self.run_cmd(testargs)

        self.user_output_mock.normal.assert_any_call(
            'This command will delete the following debuggees:\n')

        self.user_output_mock.tabular.assert_called_once_with(
            expected_headers, ANY)
        self.assertCountEqual(expected_rows,
                              self.user_output_mock.tabular.call_args.args[1])

        self.user_input_mock.prompt_user_to_continue.assert_called_once()

  def test_warning_emitted_when_unknown_debuggees_present(self):
    testargs = []
    self.rtdb_service_mock.get_debuggees = MagicMock(
        return_value=[DEBUGGEE_UNKNOWN_ACTIVITY])

    _, err = self.run_cmd(testargs)

    # Just check enough of the message to ensure it's emitted as expected.
    self.assertIn('WARNING, some debuggee entries do not have a last activity',
                  err.getvalue())

  def test_user_prompted_before_delete_answers_no(self):
    testargs = []
    self.rtdb_service_mock.get_debuggees = MagicMock(
        return_value=[DEBUGGEE_STALE])

    # Returning False means user said no.
    self.user_input_mock.prompt_user_to_continue = MagicMock(return_value=False)

    self.run_cmd(testargs)

    self.rtdb_service_mock.delete_debuggees.assert_not_called()
    self.user_input_mock.prompt_user_to_continue.assert_called_once()

  def test_user_prompted_before_delete_answers_yes(self):
    testargs = []
    self.rtdb_service_mock.get_debuggees = MagicMock(
        return_value=[DEBUGGEE_STALE])
    self.user_input_mock.prompt_user_to_continue = MagicMock(return_value=True)

    self.run_cmd(testargs)

    self.rtdb_service_mock.delete_debuggees.assert_called_once()
    self.user_input_mock.prompt_user_to_continue.assert_called_once()

  def test_user_uses_quiet_mode_to_avoid_prompt(self):
    testargs = ['--quiet']
    self.rtdb_service_mock.get_debuggees = MagicMock(
        return_value=[DEBUGGEE_STALE])
    self.run_cmd(testargs)

    self.rtdb_service_mock.delete_debuggees.assert_called_once()
    self.user_input_mock.prompt_user_to_continue.assert_not_called()

  def test_quiet_mode_aborted_when_unknown_debuggees_present(self):
    testargs = ['--quiet']
    self.rtdb_service_mock.get_debuggees = MagicMock(
        return_value=[DEBUGGEE_UNKNOWN_ACTIVITY])

    out, err = self.run_cmd(testargs)

    self.rtdb_service_mock.delete_debuggees.assert_not_called()

    # Just check enough of the message to ensure it's emitted as expected.
    self.assertIn('Delete aborted. Run the command again without the --quiet',
                  err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_no_debuggees_found_delete_not_called(self):
    testargs = ['--quiet']
    self.rtdb_service_mock.get_debuggees = MagicMock(return_value=[])
    self.run_cmd(testargs)

    self.user_input_mock.prompt_user_to_continue.assert_not_called()
    self.rtdb_service_mock.delete_debuggees.assert_not_called()
    self.rtdb_service_mock.get_debuggees.assert_called_once()

  def test_delete_results_output_format_default(self):
    # Ensures all returned debuggees will be deleted
    testargs = ['--include-all']

    testcases = [('No Debuggees', [], 0),
                 ('One Debuggee', [DEBUGGEE_ACTIVE], 1),
                 ('Multiple Debuggees',
                  [DEBUGGEE_ACTIVE, DEBUGGEE_INACTIVE, DEBUGGEE_STALE], 3)]

    for test_name, debuggees, expected_deleted_count in testcases:
      with self.subTest(test_name):
        self.rtdb_service_mock.get_debuggees = MagicMock(return_value=debuggees)
        out, err = self.run_cmd(testargs)

        self.assertIn(f'Deleted {expected_deleted_count} debuggees',
                      err.getvalue())
        self.assertEqual('', out.getvalue())

  def test_delete_results_output_format_json(self):
    testargs = ['--include-all', '--format=json']

    testcases = [('No Debuggees', [], 0),
                 ('One Debuggee', [DEBUGGEE_ACTIVE], 1),
                 ('Multiple Debuggees',
                  [DEBUGGEE_ACTIVE, DEBUGGEE_INACTIVE, DEBUGGEE_STALE], 3)]

    for test_name, debuggees, expected_deleted_count in testcases:
      with self.subTest(test_name):
        self.user_output_mock.reset_mock()

        self.rtdb_service_mock.get_debuggees = MagicMock(return_value=debuggees)
        out, err = self.run_cmd(testargs)

        self.user_output_mock.json_format.assert_called_once_with(
            debuggees, pretty=False)
        self.assertIn(f'Deleted {expected_deleted_count} debuggees',
                      err.getvalue())
        self.assertCountEqual(debuggees, json.loads(out.getvalue()))

  def test_delete_results_output_format_pretty_json(self):
    testargs = ['--include-all', '--format=pretty-json']

    testcases = [('No Debuggees', [], 0),
                 ('One Debuggee', [DEBUGGEE_ACTIVE], 1),
                 ('Multiple Debuggees',
                  [DEBUGGEE_ACTIVE, DEBUGGEE_INACTIVE, DEBUGGEE_STALE], 3)]

    for test_name, debuggees, expected_deleted_count in testcases:
      with self.subTest(test_name):
        self.user_output_mock.reset_mock()

        self.rtdb_service_mock.get_debuggees = MagicMock(return_value=debuggees)
        out, err = self.run_cmd(testargs)

        self.user_output_mock.json_format.assert_called_once_with(
            debuggees, pretty=True)
        self.assertIn(f'Deleted {expected_deleted_count} debuggees',
                      err.getvalue())
        self.assertCountEqual(debuggees, json.loads(out.getvalue()))

  def test_output_ordering_works_as_expected(self):
    # The ordering is expected to be descending order based on the last update
    # time, ie the most recently heard from debuggee will be first. A seconddary
    # ordering field is the dispalyName. For older debuggees that don't support
    # the active debuggee feature, this field will come into play.
    d1 = copy.deepcopy(DEBUGGEE_ACTIVE)
    d1['lastUpdateTimeUnixMsec'] = 10
    d1['displayName'] = 'cc'

    d2 = copy.deepcopy(DEBUGGEE_ACTIVE)
    d2['lastUpdateTimeUnixMsec'] = 11
    d2['displayName'] = 'aa'

    d3 = copy.deepcopy(DEBUGGEE_ACTIVE)
    d3['lastUpdateTimeUnixMsec'] = 12
    d3['displayName'] = 'bb'

    d4 = copy.deepcopy(DEBUGGEE_ACTIVE)
    d4['lastUpdateTimeUnixMsec'] = 11
    d4['displayName'] = 'ac'

    d5 = copy.deepcopy(DEBUGGEE_ACTIVE)
    d5['lastUpdateTimeUnixMsec'] = 11
    d5['displayName'] = 'ab'

    testargs = ['--format=json', '--include-all']
    self.user_output_mock.reset_mock()
    self.rtdb_service_mock.get_debuggees = MagicMock(
        return_value=[d1, d2, d3, d4, d5])

    out, _ = self.run_cmd(testargs)
    self.user_output_mock.json_format.assert_called_once()

    # Note the order here, build based on descending order of the last update
    # time, followed by the display name when the time is equal.
    self.assertEqual([d3, d4, d5, d2, d1], json.loads(out.getvalue()))
