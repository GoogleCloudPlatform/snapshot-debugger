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
""" Unit test file for the cli_run module.
"""

import io
import sys
import unittest

import snapshot_dbg_cli.cli_run
import snapshot_dbg_cli.cli_services
import snapshot_dbg_cli.exceptions

from unittest.mock import MagicMock
from unittest.mock import patch


class CliRunTests(unittest.TestCase):
  """ Contains the unit tests for the cli_run module.
  """

  def setUp(self):
    self.cli_services_mock = MagicMock(
        spec=snapshot_dbg_cli.cli_services.CliServices)

  def test_expected_commands_are_registered(self):
    testcases = [
        ('delete_snapshots', 'Used to delete snapshots'),
        ('get_snapshot', 'Used to retrieve a debug snapshot'),
        ('init', 'Initializes a GCP project with the required'),
        ('list_debuggees', 'Used to display a list of the debug targets'),
        ('list_logpoints', 'Used to display the debug logpoints'),
        ('list_snapshots', 'Used to display the debug snapshots'),
        ('set_logpoint', 'Adds a debug logpoint to a debug target'),
        ('set_snapshot', 'Creates a snapshot on a debug target'),
    ]

    for command, expected_description_substring in testcases:
      with self.subTest(command):
        argv = ['prog', command, '--help']
        with self.assertRaises(SystemExit), \
             patch.object(sys, 'argv', argv), \
             patch('sys.stdout', new_callable=io.StringIO) as out:
          snapshot_dbg_cli.cli_run.run(self.cli_services_mock)

        self.assertIn(expected_description_substring, out.getvalue())

  def test_command_missing_works_as_expected(self):
    argv = ['prog']
    with self.assertRaises(snapshot_dbg_cli.exceptions.SilentlyExitError), \
         patch.object(sys, 'argv', argv), \
         patch('sys.stderr', new_callable=io.StringIO) as err:
      snapshot_dbg_cli.cli_run.run(self.cli_services_mock)

    self.assertIn(
        'Missing required argument, please specify --help for more '
        'information', err.getvalue())
