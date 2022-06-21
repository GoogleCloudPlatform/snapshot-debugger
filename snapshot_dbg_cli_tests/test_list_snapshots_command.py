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
""" Unit test file for the GetSnapshot class.
"""

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

SNAPSHOT_ACTIVE =  {
  'action': 'CAPTURE',
  'createTimeUnixMsec': 1649962215426,
  'condition': '',
  'expressions': ['a', 'b', 'a+b'],
  'id': 'b-1649962215',
  'isFinalState': False,
  'location': {'line': 26, 'path': 'index.js'},
  'userEmail': 'user@foo.com',
  'createTime': '2022-04-14T18:50:15.852000Z',
} # yapf: disable (Subjectively, more readable hand formatted)

SNAPSHOT_COMPLETE =  {
  'action': 'CAPTURE',
  'createTimeUnixMsec': 1649962216426,
  'condition': '',
  'expressions': ['a', 'b', 'a+b'],
  'finalTimeUnixMsec': 1649962230637,
  'id': 'b-1649962216',
  'isFinalState': True,
  'location': {'line': 27, 'path': 'index.js'},
  'evaluatedExpressions': [
    {'name': 'a', 'value': '3'},
    {'name': 'b', 'value': '7'},
    {'name': 'a+b', 'value': '10'}
  ],
  'stackFrames': [
    {
      'function': 'func0',
      'locals': [
        {'name': 'a', 'value': '3'},
        {'name': 'b', 'value': '7'}
      ],
      'location': {'line': 27, 'path': 'index.js'}
    },
  ],
  'userEmail': 'user@foo.com',
  'createTime': '2022-04-14T18:50:16.852000Z',
  'finalTime': '2022-04-14T18:50:31.274000Z',
} # yapf: disable (Subjectively, more readable hand formatted)

SNAPSHOT_EXPIRED =  {
  'action': 'CAPTURE',
  'createTimeUnixMsec': 1649962217426,
  'condition': '',
  'expressions': ['a', 'b', 'a+b'],
  'id': 'b-1649962217',
  'isFinalState': True,
  'location': {'line': 28, 'path': 'index.js'},
  'userEmail': 'user@foo.com',
  'createTime': '2022-04-14T18:50:17.852000Z',
  'finalTime': '2022-04-14T18:50:31.274000Z',
  'status': {
    'description': {
      'format': 'The snapshot has expired'
    },
    'isError': True,
    'refersTo': 'BREAKPOINT_AGE'
  },
} # yapf: disable (Subjectively, more readable hand formatted)

SNAPSHOT_FAILED =  {
  'action': 'CAPTURE',
  'createTimeUnixMsec': 1649962218426,
  'condition': '',
  'expressions': ['a', 'b', 'a+b'],
  'id': 'b-1649962218',
  'isFinalState': True,
  'location': {'line': 29, 'path': 'index.js'},
  'userEmail': 'user@foo.com',
  'createTime': '2022-04-14T18:50:18.852000Z',
  'finalTime': '2022-04-14T18:50:31.274000Z',
  'status': {
    'description': {
        'format': 'Invalid snapshot position: index.js:100.'
    },
    'isError': True,
    'refersTo': 'BREAKPOINT_SOURCE_LOCATION'
  },
} # yapf: disable (Subjectively, more readable hand formatted)

SNAPSHOT_WITH_CONDITION =  {
  'action': 'CAPTURE',
  'createTimeUnixMsec': 1649962219426,
  'condition': 'a == 3',
  'expressions': ['a', 'b', 'a+b'],
  'id': 'b-1649962219',
  'isFinalState': False,
  'location': {'line': 30, 'path': 'index.js'},
  'userEmail': 'user@foo.com',
  'createTime': '2022-04-14T18:50:19.852000Z',
} # yapf: disable (Subjectively, more readable hand formatted)

class ListSnapshotTests(unittest.TestCase):
  """ Contains the unit tests for the ListSnapshots class.
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
    args = ['cli-test', 'list_snapshots'] + testargs

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
    self.rtdb_service_mock.get_snapshots.assert_not_called()

  def test_get_snapshot_called_as_expected(self):
    testcases = [
        (
            'Defaults',
            ['--debuggee-id=123'],
            {
                'debuggee_id': '123',
                'include_inactive': False,
                'user_email': TEST_ACCOUNT
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
            'Include Inactive Specified',
            ['--debuggee-id=123', '--include-inactive'],
            {
                'debuggee_id': '123',
                'include_inactive': True,
                'user_email': TEST_ACCOUNT
            }
        )
    ] # yapf: disable

    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)
    self.rtdb_service_mock.get_snapshots = MagicMock(return_value=[])

    for test_name, testargs, expected_params in testcases:
      with self.subTest(test_name):
        self.rtdb_service_mock.reset_mock()
        self.run_cmd(testargs)

        self.rtdb_service_mock.get_snapshots.assert_called_once_with(
            **expected_params)

  def test_output_format_json(self):
    testcases = [
        ('No Snapshots', []),
        ('One Snapshot', [SNAPSHOT_ACTIVE]),
        ('Multi Snapshots', [
            SNAPSHOT_ACTIVE, SNAPSHOT_COMPLETE, SNAPSHOT_EXPIRED,
            SNAPSHOT_FAILED
        ]),
    ]

    for test_name, snapshots in testcases:
      with self.subTest(test_name):
        self.user_output_mock.reset_mock()

        testargs = ['--debuggee-id=123', '--format=json']
        self.rtdb_service_mock.get_snapshots = MagicMock(return_value=snapshots)

        out, err = self.run_cmd(testargs)

        self.user_output_mock.json_format.assert_called_once_with(
            snapshots, pretty=False)
        self.assertEqual('', err.getvalue())
        self.assertEqual(snapshots, json.loads(out.getvalue()))

  def test_output_format_json_pretty(self):
    testcases = [
        ('No Snapshots', []),
        ('One Snapshot', [SNAPSHOT_ACTIVE]),
        ('Multi Snapshots', [
            SNAPSHOT_ACTIVE, SNAPSHOT_COMPLETE, SNAPSHOT_EXPIRED,
            SNAPSHOT_FAILED
        ]),
    ]

    for test_name, snapshots in testcases:
      with self.subTest(test_name):
        self.user_output_mock.reset_mock()

        testargs = ['--debuggee-id=123', '--format=pretty-json']
        self.rtdb_service_mock.get_snapshots = MagicMock(return_value=snapshots)

        out, err = self.run_cmd(testargs)

        self.user_output_mock.json_format.assert_called_once_with(
            snapshots, pretty=True)
        self.assertEqual('', err.getvalue())
        self.assertEqual(snapshots, json.loads(out.getvalue()))

  def test_output_default(self):
    expected_active_row = ('ACTIVE', 'index.js:26', '', '', 'b-1649962215')
    expected_completed_row = ('COMPLETED', 'index.js:27', '',
                              '2022-04-14T18:50:31.274000Z', 'b-1649962216')
    expected_expired_row = ('EXPIRED', 'index.js:28', '',
                            '2022-04-14T18:50:31.274000Z', 'b-1649962217')
    expected_failed_row = ('FAILED', 'index.js:29', '',
                           '2022-04-14T18:50:31.274000Z', 'b-1649962218')
    expected_with_condition_row = ('ACTIVE', 'index.js:30', 'a == 3', '',
                                   'b-1649962219')

    testcases = [
        ('No Snapshots', [], []),
        ('Active', [SNAPSHOT_ACTIVE], [expected_active_row]),
        ('Completed', [SNAPSHOT_COMPLETE], [expected_completed_row]),
        ('Expired', [SNAPSHOT_EXPIRED], [expected_expired_row]),
        ('Failed', [SNAPSHOT_FAILED], [expected_failed_row]),
        ('With Condition', [SNAPSHOT_WITH_CONDITION],
         [expected_with_condition_row]),
        ('Multi', [
            SNAPSHOT_ACTIVE, SNAPSHOT_COMPLETE, SNAPSHOT_EXPIRED,
            SNAPSHOT_FAILED, SNAPSHOT_WITH_CONDITION
        ], [
            expected_active_row, expected_completed_row, expected_expired_row,
            expected_failed_row, expected_with_condition_row
        ]),
    ]

    for test_name, snapshots, expected_rows in testcases:
      with self.subTest(test_name):
        testargs = ['--debuggee-id=123']
        self.rtdb_service_mock.get_snapshots = MagicMock(return_value=snapshots)
        expected_header = [
            'Status', 'Location', 'Condition', 'CompletedTime', 'ID'
        ]
        expected_output = self.data_formatter.build_table(
            expected_header, expected_rows) + '\n'

        out, err = self.run_cmd(testargs)

        self.assertEqual(expected_output, err.getvalue())
        self.assertEqual('', out.getvalue())
