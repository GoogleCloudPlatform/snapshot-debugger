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
import os
import sys
import unittest

from snapshot_dbg_cli.cli_common_arguments import CommonArgumentParsers
from snapshot_dbg_cli.cli_common_arguments import RequiredArgumentParsers
from snapshot_dbg_cli.cli_common_arguments import OutputFormat

from io import StringIO
from unittest.mock import patch

def parse_args(parsers, testargs):
  args_parser = argparse.ArgumentParser(parents=parsers)
  argv = ['prog'] + testargs

  with patch.object(sys, 'argv', argv):
    return args_parser.parse_args()

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

  def test_database_url_arg_works_as_expected(self):
    testcases = [
        # (test_name, testargs, env vars, expected_database_url)
        ('Not set', [], {}, None),
        ('Arg Set', ['--database-url', 'argv-url'], {}, 'argv-url'),
        ('Env Var Set', [], {
            'SNAPSHOT_DEBUGGER_DATABASE_URL': 'envp-url'
        }, 'envp-url'),
        ('Both Set Argv Wins', ['--database-url', 'argv-url'], {
            'SNAPSHOT_DEBUGGER_DATABASE_URL': 'envp-url'
        }, 'argv-url'),
    ]

    for test_name, testargs, envp, expected_database_url in testcases:
      with self.subTest(test_name), patch.dict(os.environ, envp, clear=True):
        args = parse_args([CommonArgumentParsers().database_url], testargs)
        self.assertEqual(expected_database_url, args.database_url)

  def test_debuggee_id_arg_works_as_expected(self):
    testcases = [
        # (test_name, testargs, env vars, expected_debuggee_id)
        ('Arg Set', ['--debuggee-id', 'argv-id'], {}, 'argv-id'),
        ('Env Var Set', [], {
            'SNAPSHOT_DEBUGGER_DEBUGGEE_ID': 'envp-id'
        }, 'envp-id'),
        ('Both Set Argv Wins', ['--debuggee-id', 'argv-id'], {
            'SNAPSHOT_DEBUGGER_DEBUGEE_ID': 'envp-id'
        }, 'argv-id'),
    ]

    for test_name, testargs, envp, expected_debuggee_id in testcases:
      with self.subTest(test_name), patch.dict(os.environ, envp, clear=True):
        args = parse_args([CommonArgumentParsers().debuggee_id], testargs)
        self.assertEqual(expected_debuggee_id, args.debuggee_id)

  def test_debuggee_id_is_required(self):
    with self.assertRaises(SystemExit), \
         patch.dict(os.environ, {}, clear=True), \
         patch('sys.stderr', new_callable=StringIO) as err:
      parse_args([CommonArgumentParsers().debuggee_id], testargs=[])

    self.assertIn('error: the following arguments are required: --debuggee-id',
                  err.getvalue())

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
        args = parse_args([CommonArgumentParsers().format], testargs)
        self.assertEqual(expected_format, args.format)

  def test_format_arg_raises_system_exit_on_bad_format(self):
    with self.assertRaises(SystemExit), \
         patch('sys.stderr', new_callable=StringIO) as err:
      parse_args([CommonArgumentParsers().format], ['--format', 'foo-invalid'])

    self.assertIn(
        'argument --format: Invalid format argument provided: foo-invalid',
        err.getvalue())

class RequiredArgumentParsersTests(unittest.TestCase):
  """Contains the unit tests for the RequiredArgumentParsers class.
  """
  def test_debug_arg_works_as_expected(self):
    parsers = RequiredArgumentParsers().parsers

    self.assertEqual(False, parse_args(parsers, []).debug)
    self.assertEqual(True, parse_args(parsers, ['--debug']).debug)

