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
""" Unit test file for the test_cli_common_arguments module.
"""

import argparse
import sys
import unittest

from snapshot_dbg_cli.cli_common_arguments import CommonArgumentParsers
from snapshot_dbg_cli.cli_common_arguments import OutputFormat

from io import StringIO
from unittest.mock import patch


class OutputFormatTests(unittest.TestCase):
  """Contains the unit tests for the OutputFormat class.
  """

  def test_is_a_json_value_works_as_expected(self):
    self.assertFalse(OutputFormat.DEFAULT.is_a_json_value())
    self.assertTrue(OutputFormat.JSON.is_a_json_value())
    self.assertTrue(OutputFormat.PRETTY_JSON.is_a_json_value())

  def test_is_pretty_json_works_as_expected(self):
    self.assertFalse(OutputFormat.DEFAULT.is_pretty_json())
    self.assertFalse(OutputFormat.JSON.is_pretty_json())
    self.assertTrue(OutputFormat.PRETTY_JSON.is_pretty_json())

  def test_parse_arg_works_as_expected_on_success(self):
    self.assertIs(OutputFormat.parse_arg('default'), OutputFormat.DEFAULT)
    self.assertIs(OutputFormat.parse_arg('json'), OutputFormat.JSON)
    self.assertIs(
        OutputFormat.parse_arg('pretty-json'), OutputFormat.PRETTY_JSON)

  def test_parse_arg_raises_on_error(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      OutputFormat.parse_arg('foo-invalid')


class CommonArgumentParsersTests(unittest.TestCase):
  """Contains the unit tests for the CommonArgumentParsers class.
  """

  def parse_args(self, parser, testargs):
    args_parser = argparse.ArgumentParser(parents=[parser])
    argv = ['prog'] + testargs

    with patch.object(sys, 'argv', argv):
      return args_parser.parse_args()

  def test_format_arg_works_as_expected(self):
    testcases = [
        # (test_name, testargs, expected_format)
        ('Not Set', [], OutputFormat.DEFAULT),
        ('Set Default', ['--format', 'default'], OutputFormat.DEFAULT),
        ('Set JSON', ['--format', 'json'], OutputFormat.JSON),
        ('Set Pretty JSON', ['--format',
                             'pretty-json'], OutputFormat.PRETTY_JSON),
    ]

    for test_name, testargs, expected_format in testcases:
      with self.subTest(test_name):
        args = self.parse_args(CommonArgumentParsers().format, testargs)
        self.assertEqual(expected_format, args.format)

  def test_format_arg_raises_system_exit_on_bad_format(self):
    with self.assertRaises(SystemExit), \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.parse_args(
          CommonArgumentParsers().format, testargs=['--format', 'foo-invalid'])

    self.assertIn(
        'argument --format: Invalid format argument provided: foo-invalid',
        err.getvalue())
