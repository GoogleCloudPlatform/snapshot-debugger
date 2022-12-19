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

import os
import sys
import json
import unittest
from enum import Enum
from io import StringIO

from snapshot_dbg_cli import cli_run
from snapshot_dbg_cli import data_formatter
from snapshot_dbg_cli.cli_services import CliServices
from snapshot_dbg_cli.snapshot_debugger_rtdb_service import SnapshotDebuggerRtdbService
from snapshot_dbg_cli.user_output import UserOutput

from snapshot_dbg_cli.exceptions import SilentlyExitError

from unittest.mock import MagicMock
from unittest.mock import patch

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

SNAPSHOT_COMPLETE =  {
  'action': 'CAPTURE',
  'createTimeUnixMsec': 1649962215426,
  'condition': 'a == 3',
  'expressions': ['a', 'b', 'a+b'],
  'finalTimeUnixMsec': 1649962230637,
  'id': 'b-1649962215',
  'isFinalState': True,
  'location': {'line': 26, 'path': 'index.js'},
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
      'location': {'line': 26, 'path': 'index.js'}
    },
    {
      'function': 'func1',
      'locals': [
        {'name': 'c', 'varTableIndex': 0},
        {'name': 'd', 'varTableIndex': 1}
      ],
      'location': {'line': 30, 'path': 'index.js' }
    }
  ],
  'variableTable': [
    {
      'members': [
         {'name': 'c1', 'value': '1'},
         {'name': 'c2',  'value': '2'}
      ]
    },
    {
      'members': [
        {'name': 'd1', 'value': '11'},
        {'name': 'd2',  'value': '22'}
      ]
    }
  ],
  'userEmail': 'foo@bar.com',
  'createTime': '2022-04-14T18:50:15Z',
  'finalTime': '2022-04-14T18:50:31Z',
} # yapf: disable (Subjectively, more readable hand formatted)

SNAPSHOT_EXPIRED =  {
  'action': 'CAPTURE',
  'createTimeUnixMsec': 1649962215426,
  'condition': 'a == 3',
  'expressions': ['a', 'b', 'a+b'],
  'id': 'b-1649962215',
  'isFinalState': True,
  'location': {'line': 26, 'path': 'index.js'},
  'userEmail': 'foo@bar.com',
  'createTime': '2022-04-14T18:50:15Z',
  'finalTime': '2022-04-14T18:50:31Z',
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
  'createTimeUnixMsec': 1649962215426,
  'condition': 'a == 3',
  'expressions': ['a', 'b', 'a+b'],
  'id': 'b-1649962215',
  'isFinalState': True,
  'location': {'line': 100, 'path': 'index.js'},
  'userEmail': 'foo@bar.com',
  'createTime': '2022-04-14T18:50:15Z',
  'finalTime': '2022-04-14T18:50:31Z',
  'status': {
    'description': {
        'format': 'Invalid snapshot position: index.js:100.'
    },
    'isError': True,
    'refersTo': 'BREAKPOINT_SOURCE_LOCATION'
  },
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

class GetSnapshotTests(unittest.TestCase):
  """ Contains the unit tests for the GetSnapshot class.
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
    args = ['cli-test', 'get_snapshot'] + testargs

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
    self.rtdb_service_mock.get_snapshot_detailed.assert_not_called()

  def test_get_snapshot_detailed_called_as_expected(self):
    testargs = ['b-111', '--debuggee-id=123']
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)
    self.rtdb_service_mock.get_snapshot_detailed = MagicMock(
        return_value=SNAPSHOT_ACTIVE)

    self.run_cmd(testargs)

    self.rtdb_service_mock.get_snapshot_detailed.assert_called_once_with(
        '123', 'b-111')

  def test_snapshot_not_found_works_as_expected(self):
    testargs = ['b-111', '--debuggee-id=123']
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)
    self.rtdb_service_mock.get_snapshot_detailed = MagicMock(return_value=None)

    out, err = self.run_cmd(testargs, expected_exception=SilentlyExitError)

    self.user_output_mock.error.assert_called_once()
    self.assertEqual('Snapshot ID not found: b-111\n', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_id_matches_a_logpoint_not_a_snapshot(self):
    testargs = ['b-111', '--debuggee-id=123']
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)
    self.rtdb_service_mock.get_snapshot_detailed = MagicMock(
        return_value=LOGPOINT_ACTIVE)

    out, err = self.run_cmd(testargs, expected_exception=SilentlyExitError)

    self.user_output_mock.error.assert_called_once()
    self.assertEqual('Snapshot ID not found: b-111\n', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_output_format_json(self):
    testargs = [SNAPSHOT_COMPLETE['id'], '--debuggee-id=123', '--format=json']
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)
    self.rtdb_service_mock.get_snapshot_detailed = MagicMock(
        return_value=SNAPSHOT_COMPLETE)

    out, err = self.run_cmd(testargs)

    self.user_output_mock.json_format.assert_called_once_with(
        SNAPSHOT_COMPLETE, pretty=False)
    self.assertEqual('', err.getvalue())
    self.assertEqual(SNAPSHOT_COMPLETE, json.loads(out.getvalue()))

  def test_output_format_pretty_json(self):
    testargs = [
        SNAPSHOT_COMPLETE['id'], '--debuggee-id=123', '--format=pretty-json'
    ]
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)
    self.rtdb_service_mock.get_snapshot_detailed = MagicMock(
        return_value=SNAPSHOT_COMPLETE)

    out, err = self.run_cmd(testargs)

    self.user_output_mock.json_format.assert_called_once_with(
        SNAPSHOT_COMPLETE, pretty=True)

    self.assertEqual('', err.getvalue())
    self.assertEqual(SNAPSHOT_COMPLETE, json.loads(out.getvalue()))

  def test_summary_section(self):
    snapshot_active = SNAPSHOT_ACTIVE

    snapshot_with_condition = SNAPSHOT_ACTIVE
    self.assertGreater(len(snapshot_with_condition['condition']), 0)

    snapshot_without_condition = SNAPSHOT_ACTIVE.copy()
    del snapshot_without_condition['condition']

    snapshot_condition_empty = SNAPSHOT_ACTIVE.copy()
    snapshot_condition_empty['condition'] = ''

    snapshot_with_expressions = SNAPSHOT_ACTIVE
    self.assertGreater(len(snapshot_with_expressions['expressions']), 0)

    snapshot_without_expressions = SNAPSHOT_ACTIVE.copy()
    del snapshot_without_expressions['expressions']

    snapshot_expressions_empty = SNAPSHOT_ACTIVE.copy()
    snapshot_expressions_empty['expressions'] = []

    snapshot_complete = SNAPSHOT_COMPLETE
    snapshot_expired = SNAPSHOT_EXPIRED
    snapshot_failed = SNAPSHOT_FAILED

    expected_header = ''.join(
        ['\n', '-' * 80, '\n', '| Summary\n', '-' * 80, '\n\n'])

    expected_summary_active = (
        expected_header + 'Location:    index.js:26\n'
        'Condition:   a == 3\n'
        "Expressions: ['a', 'b', 'a+b']\n"
        'Status:      Active\n'
        'Create Time: 2022-04-14T18:50:15Z\n'
        'Final Time:  \n')

    expected_summary_with_condition = expected_summary_active

    expected_summary_without_condition = (
        expected_header + 'Location:    index.js:26\n'
        'Condition:   No condition set\n'
        "Expressions: ['a', 'b', 'a+b']\n"
        'Status:      Active\n'
        'Create Time: 2022-04-14T18:50:15Z\n'
        'Final Time:  \n')

    expected_summary_condition_empty = expected_summary_without_condition

    expected_summary_with_expressions = expected_summary_active

    expected_summary_without_expressions = (
        expected_header + 'Location:    index.js:26\n'
        'Condition:   a == 3\n'
        'Expressions: No expressions set\n'
        'Status:      Active\n'
        'Create Time: 2022-04-14T18:50:15Z\n'
        'Final Time:  \n')

    expected_summary_expressions_empty = expected_summary_without_expressions

    expected_summary_complete = (
        expected_header + 'Location:    index.js:26\n'
        'Condition:   a == 3\n'
        "Expressions: ['a', 'b', 'a+b']\n"
        'Status:      Complete\n'
        'Create Time: 2022-04-14T18:50:15Z\n'
        'Final Time:  2022-04-14T18:50:31Z\n')

    expected_summary_expired = (
        expected_header + 'Location:    index.js:26\n'
        'Condition:   a == 3\n'
        "Expressions: ['a', 'b', 'a+b']\n"
        'Status:      The snapshot has expired\n'
        'Create Time: 2022-04-14T18:50:15Z\n'
        'Final Time:  2022-04-14T18:50:31Z\n')

    expected_summary_failed = (
        expected_header + 'Location:    index.js:100\n'
        'Condition:   a == 3\n'
        "Expressions: ['a', 'b', 'a+b']\n"
        'Status:      ERROR: Invalid snapshot position: index.js:100. '
        '(refers to: BREAKPOINT_SOURCE_LOCATION)\n'
        'Create Time: 2022-04-14T18:50:15Z\n'
        'Final Time:  2022-04-14T18:50:31Z\n')

    # We tag each testcase with information on wether the summary section is the
    # only expected output from the test. Since the condition/expressions tests
    # are using an active snaphsot, they will all be tagged as FULL.
    class OutputType(Enum):
      PARTIAL = 1
      FULL = 2

    testcases = [
        ('Active', snapshot_active, expected_summary_active, OutputType.FULL),
        ('With Condition', snapshot_with_condition,
         expected_summary_with_condition, OutputType.FULL),
        ('Without Condition', snapshot_without_condition,
         expected_summary_without_condition, OutputType.FULL),
        ('Condition Empty', snapshot_condition_empty,
         expected_summary_condition_empty, OutputType.FULL),
        ('With Expressions', snapshot_with_expressions,
         expected_summary_with_expressions, OutputType.FULL),
        ('Without Expressions', snapshot_without_expressions,
         expected_summary_without_expressions, OutputType.FULL),
        ('Expressions Empty', snapshot_expressions_empty,
         expected_summary_expressions_empty, OutputType.FULL),
        ('Complete', snapshot_complete, expected_summary_complete,
         OutputType.PARTIAL),
        ('Expired', snapshot_expired, expected_summary_expired,
         OutputType.FULL),
        ('Failed', snapshot_failed, expected_summary_failed, OutputType.FULL),
    ]

    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)

    for test_name, snapshot, expected_summary, output_type in testcases:
      with self.subTest(test_name):
        self.rtdb_service_mock.get_snapshot_detailed = MagicMock(
            return_value=snapshot)

        testargs = [snapshot['id'], '--debuggee-id=123']
        out, err = self.run_cmd(testargs)

        if output_type == OutputType.PARTIAL:
          self.assertIn(expected_summary, err.getvalue())
        else:
          self.assertEqual(expected_summary, err.getvalue())

        self.assertEqual('', out.getvalue())

  def test_evaluated_expressions_section(self):
    snapshot_with_expressions = SNAPSHOT_COMPLETE
    snapshot_without_expressions = SNAPSHOT_COMPLETE.copy()
    del snapshot_without_expressions['expressions']
    del snapshot_without_expressions['evaluatedExpressions']

    expected_header = ''.join(
        ['-' * 80, '\n', '| Evaluated Expressions\n', '-' * 80, '\n\n'])

    expressions_data = [{'a': '3'}, {'b': '7'}, {'a+b': '10'}]

    expected_with_expressions = ''.join([
        expected_header,
        self.data_formatter.to_json_string(expressions_data, pretty=True)
    ])

    expected_without_expressions = (
        expected_header + 'There were no expressions specified.\n')

    testcases = [
        ('With Expressions', snapshot_with_expressions,
         expected_with_expressions),
        ('Without Expressions', snapshot_without_expressions,
         expected_without_expressions),
    ]

    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)

    for test_name, snapshot, expected_expressions_section in testcases:
      with self.subTest(test_name):
        self.rtdb_service_mock.get_snapshot_detailed = MagicMock(
            return_value=snapshot)

        testargs = [snapshot['id'], '--debuggee-id=123']
        out, err = self.run_cmd(testargs)

        self.assertIn(expected_expressions_section, err.getvalue())
        self.assertEqual('', out.getvalue())

  def test_selected_index_out_of_range(self):
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)

    self.rtdb_service_mock.get_snapshot_detailed = MagicMock(
        return_value=SNAPSHOT_COMPLETE)

    testargs = [SNAPSHOT_COMPLETE['id'], '--debuggee-id=123', '--frame-index=2']
    out = None
    err = None

    out, err = self.run_cmd(testargs, SilentlyExitError)

    self.assertEqual(
        'Stack frame index 2 too big, there are only 2 stack frames.\n',
        err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_local_variables_default_frame_index(self):
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)

    self.rtdb_service_mock.get_snapshot_detailed = MagicMock(
        return_value=SNAPSHOT_COMPLETE)

    expected_header = ''.join([
        '-' * 80, '\n', '| Local Variables For Stack Frame Index 0:\n',
        '-' * 80, '\n\n'
    ])

    locals_data = [{'a': '3'}, {'b': '7'}]

    expected_locals = self.data_formatter.to_json_string(
        locals_data, pretty=True)

    expected_output = ''.join([expected_header, expected_locals])

    # By not specifying a frame index in the args, it defaults to 0.
    testargs = [SNAPSHOT_COMPLETE['id'], '--debuggee-id=123']
    out, err = self.run_cmd(testargs)

    self.assertIn(expected_output, err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_selected_index_non_zero(self):
    """Tests the case of the selecting a different frame than the first one.

    In this case only the local variables for the frame in question are
    displayed, no other sections.
    """
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)

    self.rtdb_service_mock.get_snapshot_detailed = MagicMock(
        return_value=SNAPSHOT_COMPLETE)

    expected_header = ''.join([
        '\n', '-' * 80, '\n', '| Local Variables For Stack Frame Index 1:\n',
        '-' * 80, '\n\n'
    ])

    locals_data = [
        {'c': {'c1': '1', 'c2': '2'}},
        {'d': {'d1': '11', 'd2': '22'}}
    ] # yapf: disable

    expected_locals = self.data_formatter.to_json_string(
        locals_data, pretty=True)

    expected_output = ''.join([expected_header, expected_locals, '\n'])

    testargs = [SNAPSHOT_ACTIVE['id'], '--debuggee-id=123', '--frame-index=1']
    out, err = self.run_cmd(testargs)

    # Use 'assertEqual', ensure the entire output is only the local variables
    # for frame 1.
    self.assertEqual(expected_output, err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_callstack(self):
    self.rtdb_service_mock.validate_debuggee_id = MagicMock(return_value=None)

    self.rtdb_service_mock.get_snapshot_detailed = MagicMock(
        return_value=SNAPSHOT_COMPLETE)

    expected_header = ''.join(
        ['-' * 80, '\n', '| CallStack:\n', '-' * 80, '\n\n'])

    expected_callstack = data_formatter.DataFormatter().build_table(
        ['Function', 'Location'], [('func0', 'index.js:26'),
                                   ('func1', 'index.js:30')])

    expected_output = ''.join([expected_header, expected_callstack])

    testargs = [SNAPSHOT_ACTIVE['id'], '--debuggee-id=123']
    out, err = self.run_cmd(testargs)

    self.assertIn(expected_output, err.getvalue())
    self.assertEqual('', out.getvalue())
