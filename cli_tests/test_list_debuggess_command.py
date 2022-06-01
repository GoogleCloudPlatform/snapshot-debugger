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

    self.missing_id = {
        'labels': {
            'module': 'missing id',
            'version': 'v1'
        },
        'description': 'desc missing id'
    }
    # If the id is missing that is considering invalid and it will be suppressed
    self.missing_id_table_values = []
    self.missing_id_json_value = []

    self.missing_labels = {'id': '123', 'description': 'desc 1'}
    # If the 'module' label is missing, 'default' should be used.
    self.missing_labels_table_values = ['default - ', '123', 'desc 1']
    self.missing_labels_json_value = self.missing_labels

    self.missing_description = {
        'id': '123',
        'labels': {
            'module': 'app123',
            'version': 'v1'
        },
    }
    self.missing_description_table_values = ['app123 - v1', '123', '']
    self.missing_description_json_value = self.missing_description

    self.debuggee1 = {
        'id': '123',
        'labels': {
            'module': 'app123',
            'version': 'v1'
        },
        'description': 'desc 1'
    }
    self.debuggee1_table_values = ['app123 - v1', '123', 'desc 1']
    self.debuggee1_json_value = self.debuggee1

    self.debuggee2 = {
        'id': '456',
        'labels': {
            'module': 'app456',
            'version': 'v2'
        },
        'description': 'desc 2'
    }
    self.debuggee2_table_values = ['app456 - v2', '456', 'desc 2']
    self.debuggee2_json_value = self.debuggee2

    self.debuggee3 = {
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
    }

    self.debuggee3_table_values = [
        'test-app - v1', '97b0090602ceb5a506f1cf7dff02524f',
        'node index.js module:test-app version:v1'
    ]
    self.debuggee3_json_value = self.debuggee3

  def test_get_debuggees_called_once(self):
    args = self.args_parser.parse_args(['list_debuggees'])
    self.rtdb_service_mock.get_debuggees = MagicMock(return_value={})

    self.list_debuggees.cmd(args, self.cli_services)
    self.rtdb_service_mock.get_debuggees.assert_called_once()

  def test_output_format_default(self):
    expected_headers = ['Name', 'ID', 'Description']

    testcases = [({}, []), ({
        '1': self.missing_id
    }, self.missing_id_table_values),
                 ({
                     self.missing_labels['id']: self.missing_labels
                 }, [self.missing_labels_table_values]),
                 ({
                     self.missing_description['id']: self.missing_description
                 }, [self.missing_description_table_values]),
                 ({
                     self.debuggee1['id']: self.debuggee1
                 }, [self.debuggee1_table_values]),
                 ({
                     self.debuggee1['id']: self.debuggee1,
                     self.debuggee2['id']: self.debuggee2,
                 }, [
                     self.debuggee1_table_values, self.debuggee2_table_values
                 ]),
                 ({
                     self.debuggee1['id']: self.debuggee1,
                     self.debuggee2['id']: self.debuggee2,
                     self.debuggee3['id']: self.debuggee3
                 }, [
                     self.debuggee1_table_values, self.debuggee2_table_values,
                     self.debuggee3_table_values
                 ])]

    for in_data, out_data in testcases:
      with self.subTest():
        args = self.args_parser.parse_args(['list_debuggees'])
        self.user_output_mock.reset_mock()
        self.rtdb_service_mock.get_debuggees = MagicMock(return_value=in_data)

        self.list_debuggees.cmd(args, self.cli_services)
        self.user_output_mock.tabular.assert_called_once_with(
            expected_headers, out_data)

  def test_output_format_json(self):
    args = self.args_parser.parse_args(['list_debuggees'])

    testcases = [({}, []), ({
        '1': self.missing_id
    }, self.missing_id_json_value),
                 ({
                     self.missing_labels['id']: self.missing_labels
                 }, [self.missing_labels_json_value]),
                 ({
                     self.missing_description['id']: self.missing_description
                 }, [self.missing_description_json_value]),
                 ({
                     self.debuggee1['id']: self.debuggee1
                 }, [self.debuggee1_json_value]),
                 ({
                     self.debuggee1['id']: self.debuggee1,
                     self.debuggee2['id']: self.debuggee2
                 }, [self.debuggee1_json_value, self.debuggee2_json_value]),
                 ({
                     self.debuggee1['id']: self.debuggee1,
                     self.debuggee2['id']: self.debuggee2,
                     self.debuggee3['id']: self.debuggee3
                 }, [
                     self.debuggee1_json_value, self.debuggee2_json_value,
                     self.debuggee3_json_value
                 ])]

    for in_data, out_data in testcases:
      for json_format in ['json', 'pretty-json']:
        with self.subTest():
          pretty = json_format == 'pretty-json'
          args = self.args_parser.parse_args(
              ['list_debuggees', f'--format={json_format}'])
          self.user_output_mock.reset_mock()
          self.rtdb_service_mock.get_debuggees = MagicMock(return_value=in_data)

          self.list_debuggees.cmd(args, self.cli_services)
          self.user_output_mock.json_format.assert_called_once_with(
              out_data, pretty=pretty)
