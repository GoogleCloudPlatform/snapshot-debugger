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
""" Unit test file for the SnapshotDebuggerSchema class.
"""

import copy
import json
import os
import sys
import unittest

from snapshot_dbg_cli import cli_run
from snapshot_dbg_cli import data_formatter
from snapshot_dbg_cli.cli_services import CliServices
from snapshot_dbg_cli.user_output import UserOutput

from io import StringIO
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import patch

# Below are the debuggees test data. They are setup as a tuple, the first field
# is the debuggee itself that will be returned from the rtdb query, and the 2nd
# element is the expected human readable tabular data for it. There is no third
# entry for the expected json data, as that is expected to match exactly the
# data returned from the rtdb query, so the first field is the expected json
# response data.

debuggee1 = ({
    'id': '123',
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
    'lastUpdateTimeUnixMsec': 1670000000001,
    'registrationTime': '2022-04-14T18:50:15.426000Z',
    'lastUpdateTime': '2022-12-02T16:53:20.001000Z',
}, ['app123 - v1', '123', 'desc 1'])

debuggee2 = ({
    'id': '456',
    'labels': {
        'module': 'app456',
        'version': 'v2'
    },
    'description': 'desc 2',
    'displayName': 'app456 - v2',
    'activeDebuggeeEnabled': True,
    'isActive': True,
    'isStale': False,
    'registrationTimeUnixMsec': 1649962215426,
    'lastUpdateTimeUnixMsec': 1670000000002,
    'registrationTime': '2022-04-14T18:50:15.426000Z',
    'lastUpdateTime': '2022-12-02T16:53:20.002000Z',
}, ['app456 - v2', '456', 'desc 2'])

debuggee3 = ({
    'agentVersion': 'google.com/node-gcp/v6.0.0',
    'description': 'node index.js module:test-app version:v1',
    'id': 'd-ff02524f',
    'labels': {
        'V8_version': '7.8.279.23-node.56',
        'agent_name': '@google-cloud/debug-agent',
        'agent_version': '6.0.0',
        'main_script': 'index.js',
        'module': 'test-app',
        'node_version': '12.22.5',
        'platform': 'default',
        'process_title': 'node',
        'projectid': 'unknown',
        'version': 'v1'
    },
    'displayName': 'test-app - v1',
    'project': 'unknown',
    'uniquifier': 'ecbb07aaba5ad405ad7667bf3eacbd874e23a2f5',
    'activeDebuggeeEnabled': True,
    'isActive': True,
    'isStale': False,
    'registrationTimeUnixMsec': 1649962215426,
    'lastUpdateTimeUnixMsec': 1670000000003,
    'registrationTime': '2022-04-14T18:50:15.426000Z',
    'lastUpdateTime': '2022-12-02T16:53:20.003000Z',
}, ['test-app - v1', 'd-ff02524f', 'node index.js module:test-app version:v1'])


class ListDebuggeesCommandTests(unittest.TestCase):
  """ Contains the unit tests for the ListDebuggeesCommand class.
  """

  def setUp(self):
    self.cli_services = MagicMock(spec=CliServices)

    self.user_output_mock = MagicMock(
        wraps=UserOutput(
            is_debug_enabled=False,
            data_formatter=data_formatter.DataFormatter()))
    self.cli_services.user_output = self.user_output_mock

    self.rtdb_service_mock = MagicMock()
    self.cli_services.get_snapshot_debugger_rtdb_service = MagicMock(
        return_value=self.rtdb_service_mock)

  def run_cmd(self, testargs, expected_exception=None):
    args = ['cli-test', 'list_debuggees'] + testargs

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

  def test_get_debuggees_called_once(self):
    testargs = []

    self.rtdb_service_mock.get_debuggees = MagicMock(return_value={})
    self.run_cmd(testargs)

    self.rtdb_service_mock.get_debuggees.assert_called_once()

  def test_output_format_default(self):
    expected_headers = ['Name', 'ID', 'Description']

    testcases = [
      ('No debuggees present', {}, []),
      (
        'One debuggee present',
        [debuggee1[0]],
        [debuggee1[1]]
      ),
      (
        'Two debuggees present',
        [debuggee1[0], debuggee2[0]],
        [debuggee2[1], debuggee1[1]]
      ),
      (
        'Three debuggees present',
         [debuggee1[0], debuggee2[0], debuggee3[0]],
         [debuggee1[1], debuggee2[1], debuggee3[1]]
      ),
    ] # yapf: disable (Subjectively, testcases more readable hand formatted)

    for test_name, debuggees_response, expected_tabular_data in testcases:
      with self.subTest(test_name):
        testargs = []
        self.user_output_mock.reset_mock()
        self.rtdb_service_mock.get_debuggees = MagicMock(
            return_value=debuggees_response)

        self.run_cmd(testargs)
        self.user_output_mock.tabular.assert_called_once_with(
            expected_headers, ANY)
        self.assertCountEqual(expected_tabular_data,
                              self.user_output_mock.tabular.call_args.args[1])

  def test_output_format_json(self):
    testcases = [
      ('No debuggees present', [], []),
      (
        'One debuggee present',
        [debuggee1[0]],
        [debuggee1[0]]
      ),
      (
        'Two debuggees present',
        [debuggee1[0], debuggee2[0]],
        [debuggee2[0], debuggee1[0]]
      ),
      (
        'Three debuggees present',
         [debuggee1[0], debuggee2[0], debuggee3[0]],
         [debuggee3[0], debuggee2[0], debuggee1[0]]
      ),
    ] # yapf: disable (Subjectively, testcases more readable hand formatted)

    for test_name, debuggees_response, expected_json_data in testcases:
      for json_format in ['json', 'pretty-json']:
        with self.subTest(test_name):
          pretty = json_format == 'pretty-json'
          testargs = [f'--format={json_format}']
          self.user_output_mock.reset_mock()
          self.rtdb_service_mock.get_debuggees = MagicMock(
              return_value=debuggees_response)

          out, _ = self.run_cmd(testargs)
          self.user_output_mock.json_format.assert_called_once_with(
              ANY, pretty=pretty)
          self.assertCountEqual(expected_json_data, json.loads(out.getvalue()))

  def test_include_inactive_false_by_default(self):
    debuggee_active1 = copy.deepcopy(debuggee1[0])
    debuggee_active2 = copy.deepcopy(debuggee2[0])
    self.assertTrue(debuggee_active1['isActive'])
    self.assertTrue(debuggee_active2['isActive'])

    # No need to adjust the lastUpdateTime here, simply adjusting the flag value
    # achieves the purpose of the test.
    debuggee_inactive1 = copy.deepcopy(debuggee_active1)
    debuggee_inactive2 = copy.deepcopy(debuggee_active2)
    debuggee_inactive1['id'] = 'd-1'
    debuggee_inactive2['id'] = 'd-2'
    debuggee_inactive1['activeDebuggeeEnabled'] = True
    debuggee_inactive2['activeDebuggeeEnabled'] = True
    debuggee_inactive1['isActive'] = False
    debuggee_inactive2['isActive'] = False

    testargs = ['--format=json']
    self.user_output_mock.reset_mock()
    self.rtdb_service_mock.get_debuggees = MagicMock(return_value=[
        debuggee_active1, debuggee_inactive1, debuggee_inactive2,
        debuggee_active2
    ])

    out, _ = self.run_cmd(testargs)
    self.user_output_mock.json_format.assert_called_once()
    self.assertCountEqual([debuggee_active1, debuggee_active2],
                          json.loads(out.getvalue()))

  def test_debuggees_without_active_debuggee_support_filtered_out(self):
    debuggee_active1 = copy.deepcopy(debuggee1[0])
    debuggee_active2 = copy.deepcopy(debuggee2[0])
    self.assertTrue(debuggee_active1['isActive'])
    self.assertTrue(debuggee_active2['isActive'])

    # Setting activeDebuggeeEnabled to False means it's an old debuggee that
    # does not set the last update time. Since there are newer debuggees present
    # these should not be shown.
    debuggee_filter1 = copy.deepcopy(debuggee_active1)
    debuggee_filter2 = copy.deepcopy(debuggee_active2)
    debuggee_filter1['id'] = 'd-1'
    debuggee_filter2['id'] = 'd-2'
    debuggee_filter1['activeDebuggeeEnabled'] = False
    debuggee_filter2['activeDebuggeeEnabled'] = False
    debuggee_filter1['isActive'] = False
    debuggee_filter2['isActive'] = False

    testargs = ['--format=json']
    self.user_output_mock.reset_mock()
    self.rtdb_service_mock.get_debuggees = MagicMock(return_value=[
        debuggee_active1, debuggee_active2, debuggee_filter1, debuggee_filter2
    ])

    out, _ = self.run_cmd(testargs)
    self.user_output_mock.json_format.assert_called_once()
    self.assertCountEqual([debuggee_active1, debuggee_active2],
                          json.loads(out.getvalue()))

  def test_debuggees_without_active_debuggee_support_included(self):
    # Setting activeDebuggeeEnabled to False means it's an old debuggee that
    # does not set the last update time. Since there are no newer debuggees
    # present these should not be shown.
    debuggee_include1 = copy.deepcopy(debuggee1[0])
    debuggee_include2 = copy.deepcopy(debuggee2[0])
    debuggee_include1['activeDebuggeeEnabled'] = False
    debuggee_include2['activeDebuggeeEnabled'] = False
    debuggee_include1['isActive'] = False
    debuggee_include2['isActive'] = False

    testargs = ['--format=json']
    self.user_output_mock.reset_mock()
    self.rtdb_service_mock.get_debuggees = MagicMock(
        return_value=[debuggee_include1, debuggee_include2])

    out, _ = self.run_cmd(testargs)
    self.user_output_mock.json_format.assert_called_once()
    self.assertCountEqual([debuggee_include1, debuggee_include2],
                          json.loads(out.getvalue()))

  def test_include_inactive_works_as_expected(self):
    debuggee_active1 = copy.deepcopy(debuggee1[0])
    debuggee_active2 = copy.deepcopy(debuggee2[0])
    self.assertTrue(debuggee_active1['isActive'])
    self.assertTrue(debuggee_active2['isActive'])

    # No need to adjust the lastUpdateTime here, simply adjusting the flag value
    # achieves the purpose of the test.
    debuggee_inactive1 = copy.deepcopy(debuggee_active1)
    debuggee_inactive2 = copy.deepcopy(debuggee_active2)
    debuggee_inactive1['id'] = 'd-1'
    debuggee_inactive2['id'] = 'd-2'
    debuggee_inactive1['isActive'] = False
    debuggee_inactive2['isActive'] = False

    testargs = ['--format=json', '--include-inactive']
    self.user_output_mock.reset_mock()
    self.rtdb_service_mock.get_debuggees = MagicMock(return_value=[
        debuggee_active1, debuggee_inactive1, debuggee_inactive2,
        debuggee_active2
    ])

    out, _ = self.run_cmd(testargs)
    self.user_output_mock.json_format.assert_called_once()
    self.assertCountEqual([
        debuggee_active1, debuggee_active2, debuggee_inactive1,
        debuggee_inactive2
    ], json.loads(out.getvalue()))

  def test_output_ordering_works_as_expected(self):
    # The ordering is expected to be descending order based on the last update
    # time, ie the most recently heard from debuggee will be first. A seconddary
    # ordering field is the dispalyName. For older debuggees that don't support
    # the active debuggee feature, this field will come into play.
    d1 = copy.deepcopy(debuggee1[0])
    d1['lastUpdateTimeUnixMsec'] = 10
    d1['displayName'] = 'cc'

    d2 = copy.deepcopy(debuggee1[0])
    d2['lastUpdateTimeUnixMsec'] = 11
    d2['displayName'] = 'aa'

    d3 = copy.deepcopy(debuggee1[0])
    d3['lastUpdateTimeUnixMsec'] = 12
    d3['displayName'] = 'bb'

    d4 = copy.deepcopy(debuggee1[0])
    d4['lastUpdateTimeUnixMsec'] = 11
    d4['displayName'] = 'ac'

    d5 = copy.deepcopy(debuggee1[0])
    d5['lastUpdateTimeUnixMsec'] = 11
    d5['displayName'] = 'ab'

    # We aren't setting the include-inactive flag here, so this verifies the
    # debuggees should be shown
    self.assertTrue(debuggee1[0]['isActive'])

    testargs = ['--format=json']
    self.user_output_mock.reset_mock()
    self.rtdb_service_mock.get_debuggees = MagicMock(
        return_value=[d1, d2, d3, d4, d5])

    out, _ = self.run_cmd(testargs)
    self.user_output_mock.json_format.assert_called_once()

    # Note the order here, build based on descending order of the last update
    # time, followed by the display name when the time is equal.
    self.assertEqual([d3, d4, d5, d2, d1], json.loads(out.getvalue()))
