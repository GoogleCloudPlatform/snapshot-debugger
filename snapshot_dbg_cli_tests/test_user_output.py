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
""" Unit test file for the user_output module.
"""

import unittest

from snapshot_dbg_cli.data_formatter import DataFormatter
from snapshot_dbg_cli.user_output import UserOutput
from io import StringIO
from unittest.mock import MagicMock
from unittest.mock import patch


class SnapshotDebuggerSchemaTests(unittest.TestCase):
  """Contains the unit tests for the user_output module.

  As a general note, all output is expected to go to stderr, except for the
  explicit json output, which goes to stdout and is meant for programmatic
  consumption.
  """

  def setUp(self):
    self.formatter_mock = MagicMock(spec=DataFormatter)
    self.user_output = UserOutput(
        is_debug_enabled=False, data_formatter=self.formatter_mock)

  def test_debug_output_works_as_expected_when_debug_disabled(self):
    self.user_output = UserOutput(
        is_debug_enabled=False, data_formatter=self.formatter_mock)

    with patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.user_output.debug('debug', 'a', 'b', sep='|', end='*')
      self.user_output.debug('c', 'd', sep='|', end='*')

    self.assertEqual('', out.getvalue())
    self.assertEqual('', err.getvalue())

  def test_debug_output_works_as_expected_when_debug_enbled(self):
    self.user_output = UserOutput(
        is_debug_enabled=True, data_formatter=self.formatter_mock)

    with patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.user_output.debug('debug', 'a', 'b', sep='|', end='*')
      self.user_output.debug('c', 'd', sep='|', end='*')

    self.assertEqual('', out.getvalue())
    self.assertEqual('debug|a|b*c|d*', err.getvalue())

  def test_normal_output_works_as_expected(self):
    with patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.user_output.normal('normal', 'a', 'b', sep='|', end='*')
      self.user_output.normal('c', 'd', sep='|', end='*')

    self.assertEqual('', out.getvalue())
    self.assertEqual('normal|a|b*c|d*', err.getvalue())

  def test_error_output_works_as_expected(self):
    with patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.user_output.error('error', 'a', 'b', sep='|', end='*')
      self.user_output.error('c', 'd', sep='|', end='*')

    self.assertEqual('', out.getvalue())
    self.assertEqual('error|a|b*c|d*', err.getvalue())

  def test_json_format_works_as_expected_pretty_is_false(self):
    self.formatter_mock.to_json_string = MagicMock(
        return_value='Json Return Data')

    with patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.user_output.json_format('Foo', pretty=False)

    self.assertEqual('Json Return Data\n', out.getvalue())
    self.assertEqual('', err.getvalue())
    self.formatter_mock.to_json_string.assert_called_once_with('Foo', False)

  def test_json_format_works_as_expected_pretty_is_true(self):
    self.formatter_mock.to_json_string = MagicMock(
        return_value='Json Return Data')

    with patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.user_output.json_format('Foo', pretty=True)

    self.assertEqual('Json Return Data\n', out.getvalue())
    self.assertEqual('', err.getvalue())
    self.formatter_mock.to_json_string.assert_called_once_with('Foo', True)

  def test_tabular_works_as_expected_pretty_is_true(self):
    self.formatter_mock.build_table = MagicMock(return_value='Built Table')

    with patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.user_output.tabular(['H1'], [['v1']])

    self.assertEqual('', out.getvalue())
    self.assertEqual('Built Table\n', err.getvalue())
    self.formatter_mock.build_table.assert_called_once_with(['H1'], [['v1']])
