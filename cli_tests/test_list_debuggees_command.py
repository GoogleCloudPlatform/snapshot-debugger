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

import argparse
import unittest

from cli import cli_common_arguments
from cli import list_debuggees_command
from unittest.mock import MagicMock

# Below are the debuggees test data. They are setup as a tuple, the first field
# is the debuggee itself that will be returned from the rtdb query, and the 2nd
# element is the expected human readable tabular data for it. There is no third
# entry for the expected json data, as that is expected to match exactly the
# data returned from the rtdb query, so the first field is the expected json
# response data.

# If it is invalid if the id is missing, it will be suppressed, so the expected
# tabular data is simply an empty array.
debuggee_missing_id = (
    {
        'labels': {
            'module': 'missing id',
            'version': 'v1'
        },
        'description': 'desc missing id'
    },
    []  # It is invalid if the id is missing, it will be suppressed
)

# If the 'module' label is missing, 'default' should be used.
debuggee_missing_labels = ({
    'id': '123',
    'description': 'desc 1'
}, ['default - ', '123', 'desc 1'])

debuggee_missing_module = ({
    'id': '123',
    'labels': {
        'version': 'v1'
    },
    'description': 'desc 1'
}, ['default - v1', '123', 'desc 1'])

debuggee_missing_version = ({
    'id': '123',
    'labels': {
        'module': 'app123',
    },
    'description': 'desc 1'
}, ['app123 - ', '123', 'desc 1'])

debuggee_missing_description = ({
    'id': '123',
    'labels': {
        'module': 'app123',
        'version': 'v1'
    },
}, ['app123 - v1', '123', ''])

debuggee1 = ({
    'id': '123',
    'labels': {
        'module': 'app123',
        'version': 'v1'
    },
    'description': 'desc 1'
}, ['app123 - v1', '123', 'desc 1'])

debuggee2 = ({
    'id': '456',
    'labels': {
        'module': 'app456',
        'version': 'v2'
    },
    'description': 'desc 2'
}, ['app456 - v2', '456', 'desc 2'])

debuggee3 = ({
    'agentVersion': 'google.com/node-gcp/v6.0.0',
    'description': 'node index.js module:test-app version:v1',
    'id': '97b0090602ceb5a506f1cf7dff02524f',
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
    'project': 'unknown',
    'uniquifier': 'ecbb07aaba5ad405ad7667bf3eacbd874e23a2f5'
}, [
    'test-app - v1', '97b0090602ceb5a506f1cf7dff02524f',
    'node index.js module:test-app version:v1'
])


def debuggees_to_dict(debuggees):
  return dict((d['id'], d) for d in debuggees)


class ListDebuggeesCommandTests(unittest.TestCase):
  """ Contains the unit tests for the ListDebuggeesCommand class.
  """

  def setUp(self):
    common_parsers = cli_common_arguments.CommonArgumentParsers()
    required_parsers = cli_common_arguments.RequiredArgumentParsers().parsers

    self.args_parser = argparse.ArgumentParser()
    self.args_subparsers = self.args_parser.add_subparsers()
    self.list_debuggees = list_debuggees_command.ListDebuggeesCommand()
    self.list_debuggees.register(self.args_subparsers, required_parsers,
                                 common_parsers)
    self.cli_services = MagicMock()

    self.user_output_mock = MagicMock()
    self.cli_services.user_output = self.user_output_mock

    self.rtdb_service_mock = MagicMock()
    self.cli_services.get_snapshot_debugger_rtdb_service = MagicMock(
        return_value=self.rtdb_service_mock)

  def test_get_debuggees_called_once(self):
    args = self.args_parser.parse_args(['list_debuggees'])
    self.rtdb_service_mock.get_debuggees = MagicMock(return_value={})

    self.list_debuggees.cmd(args, self.cli_services)
    self.rtdb_service_mock.get_debuggees.assert_called_once()

  def test_output_format_default(self):
    expected_headers = ['Name', 'ID', 'Description']

    testcases = [
      ('No debuggees present', {}, []),
      (
        'Debuggee missing ID',
        {'1': debuggee_missing_id[0]},
        debuggee_missing_id[1]
      ),
      (
        'Debuggee missing labels',
         debuggees_to_dict([debuggee_missing_labels[0]]),
         [debuggee_missing_labels[1]]
      ),
      (
        'Debuggee missing module',
         debuggees_to_dict([debuggee_missing_module[0]]),
         [debuggee_missing_module[1]]
      ),
      (
        'Debuggee missing version',
         debuggees_to_dict([debuggee_missing_version[0]]),
         [debuggee_missing_version[1]]
      ),
      (
        'Debuggee missing description',
        debuggees_to_dict([debuggee_missing_description[0]]),
        [debuggee_missing_description[1]]
      ),
      (
        'One debuggee present',
        debuggees_to_dict([debuggee1[0]]),
        [debuggee1[1]]
      ),
      (
        'Two debuggees present',
        debuggees_to_dict([debuggee1[0], debuggee2[0]]),
        [debuggee1[1], debuggee2[1]]
      ),
      (
        'Three debuggees present',
         debuggees_to_dict([debuggee1[0], debuggee2[0], debuggee3[0]]),
         [debuggee1[1], debuggee2[1], debuggee3[1]]
      ),
    ] # yapf: disable (Subjectively, testcases more readable hand formatted)

    for test_name, debuggees_response, expected_tabular_data in testcases:
      with self.subTest(test_name):
        args = self.args_parser.parse_args(['list_debuggees'])
        self.user_output_mock.reset_mock()
        self.rtdb_service_mock.get_debuggees = MagicMock(
            return_value=debuggees_response)

        self.list_debuggees.cmd(args, self.cli_services)
        self.user_output_mock.tabular.assert_called_once_with(
            expected_headers, expected_tabular_data)

  def test_output_format_json(self):
    args = self.args_parser.parse_args(['list_debuggees'])

    testcases = [
      ('No debuggees present', {}, []),
      ('Debuggee missing ID', {'1': debuggee_missing_id[0]}, []),
      (
        'Debuggee missing labels',
         debuggees_to_dict([debuggee_missing_labels[0]]),
         [debuggee_missing_labels[0]]
      ),
      (
        'Debuggee missing module',
         debuggees_to_dict([debuggee_missing_module[0]]),
         [debuggee_missing_module[0]]
      ),
      (
        'Debuggee missing version',
         debuggees_to_dict([debuggee_missing_version[0]]),
         [debuggee_missing_version[0]]
      ),
      (
        'Debuggee missing description',
        debuggees_to_dict([debuggee_missing_description[0]]),
        [debuggee_missing_description[0]]
      ),
      (
        'One debuggee present',
        debuggees_to_dict([debuggee1[0]]),
        [debuggee1[0]]
      ),
      (
        'Two debuggees present',
        debuggees_to_dict([debuggee1[0], debuggee2[0]]),
        [debuggee1[0], debuggee2[0]]
      ),
      (
        'Three debuggees present',
         debuggees_to_dict([debuggee1[0], debuggee2[0], debuggee3[0]]),
         [debuggee1[0], debuggee2[0], debuggee3[0]]
      ),
    ] # yapf: disable (Subjectively, testcases more readable hand formatted)

    for test_name, debuggees_response, expected_json_data in testcases:
      for json_format in ['json', 'pretty-json']:
        with self.subTest(test_name):
          pretty = json_format == 'pretty-json'
          args = self.args_parser.parse_args(
              ['list_debuggees', f'--format={json_format}'])
          self.user_output_mock.reset_mock()
          self.rtdb_service_mock.get_debuggees = MagicMock(
              return_value=debuggees_response)

          self.list_debuggees.cmd(args, self.cli_services)
          self.user_output_mock.json_format.assert_called_once_with(
              expected_json_data, pretty=pretty)
