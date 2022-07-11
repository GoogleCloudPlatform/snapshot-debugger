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
""" Unit test file for the http_service module.
"""

import json
import unittest
import subprocess

from io import StringIO
from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli import data_formatter
from snapshot_dbg_cli.gcloud_cli_service import GcloudCliService
from snapshot_dbg_cli.user_output import UserOutput
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import patch


class GcloudCliServiceTests(unittest.TestCase):
  """ Unit tests for the gcloud_cli_service module.
  """

  def setUp(self):
    self.user_output_mock = MagicMock(
        wraps=UserOutput(
            is_debug_enabled=False,
            data_formatter=data_formatter.DataFormatter()))

    self.gcloud_service = GcloudCliService(self.user_output_mock)

    # Setup patching of the 'urllib.request.urlopen' function, which the
    # HttpService class depends on.
    self.subprocess_run_patcher = patch('subprocess.run', autospec=True)
    self.subprocess_run_mock = self.subprocess_run_patcher.start()
    self.addCleanup(self.subprocess_run_patcher.stop)

    # Install a default happy response, tests that care will override.
    return_value = subprocess.CompletedProcess(args=ANY, returncode=0)
    return_value.stdout = '"Valid JSON"'
    self.subprocess_run_mock.return_value = return_value

  def test_run_calls_subprocess_run_with_expected_arguments(self):
    self.gcloud_service.run(['fake', 'cmd'])

    # The run command will prepend the 'gcloud', and append the '--format=json'.
    # It also expressly uses stdout, stderr and universal_newlines arguments as
    # a python 3.6 compatible way to capture stdout and stderr in text mode.
    self.subprocess_run_mock.assert_called_once_with(
        ['gcloud', 'fake', 'cmd', '--format=json'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        check=False)

  def test_run_returns_decoded_json_as_expected(self):
    # Just run it through a few basic test cases, ensure it's decoding the json
    # data as expected and returning it.
    testcases = [
        {},
        [],
        [{
            'foo': 'bar'
        }],
        'foo',
        {
            'p1': 'v1',
            'p2': {
                'p3': 'v3'
            }
        },
    ]

    for data in testcases:
      with self.subTest(data):
        return_value = subprocess.CompletedProcess(
            args=['gcloud', 'fake', 'cmd', '--format=json'], returncode=0)
        return_value.stdout = json.dumps(data)
        self.subprocess_run_mock.return_value = return_value

        obtained_return_value = self.gcloud_service.run(['fake', 'cmd'])
        self.assertEqual(data, obtained_return_value)

  def test_run_handles_gcloud_command_not_found_as_expected(self):
    self.subprocess_run_mock.side_effect = FileNotFoundError()

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.gcloud_service.run(['fake', 'cmd'])

    self.assertIn(
        "A file not found error occured attempting to run the 'gcloud' cli "
        'command. Please ensure gcloud is installed and that the command is in '
        'the PATH and then try again.', ' '.join(err.getvalue().split()))
    self.assertEqual('', out.getvalue())

  def test_run_handles_oserror_as_expected(self):
    self.subprocess_run_mock.side_effect = OSError()

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.gcloud_service.run(['fake', 'cmd'])

    self.assertIn(
        "The following error occured attempting to run the 'gcloud' cli "
        'command', ' '.join(err.getvalue().split()))
    self.assertEqual('', out.getvalue())

  def test_run_handles_failed_gcloud_execution_as_expected(self):
    return_value = subprocess.CompletedProcess(args=ANY, returncode=1)
    return_value.stdout = 'Stdout data'
    return_value.stderr = 'Stderr data'
    self.subprocess_run_mock.return_value = return_value

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.gcloud_service.run(['fake', 'cmd'])

    self.assertIn("Command 'gcloud fake cmd --format=json' failed.",
                  err.getvalue())
    self.assertIn('stdout: Stdout data', err.getvalue())
    self.assertIn('stderr: Stderr data', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_run_handles_jsondecode_error_as_expected(self):
    return_value = subprocess.CompletedProcess(args=ANY, returncode=0)
    # Will cause internal json.loads() to fail.
    return_value.stdout = 'Bad json {'
    self.subprocess_run_mock.return_value = return_value

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.gcloud_service.run(['fake', 'cmd'])

    self.assertIn('Failure occured parsing gcloud output as json.',
                  err.getvalue())
    self.assertIn("Command: 'gcloud fake cmd --format=json'", err.getvalue())
    self.assertIn("Data To Parse: 'Bad json {'", err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_run_handles_unexpected_errors_as_expected(self):
    testcases = [
        subprocess.SubprocessError('SubprocessError'),
        ValueError('Bad Value')
    ]

    for exception in testcases:
      with self.subTest(f'{exception}'):
        self.subprocess_run_mock.side_effect = exception

        with self.assertRaises(SilentlyExitError), \
             patch('sys.stdout', new_callable=StringIO) as out, \
             patch('sys.stderr', new_callable=StringIO) as err:
          self.gcloud_service.run(['fake', 'cmd'])

        self.assertIn(
            'The following unexpected error occured attempting to run the '
            "'gcloud' cli command", ' '.join(err.getvalue().split()))
        self.assertEqual('', out.getvalue())

  def ttest_config_get_account_works_as_expected_on_success(self):
    return_value = subprocess.CompletedProcess(args=ANY, returncode=0)
    return_value.stdout = '"foo-user@bar.com"'
    self.subprocess_run_mock.return_value = return_value

    obtained_account = self.gcloud_service.config_get_account()

    self.assertEqual('foo-user@bar.com', obtained_account)
    self.subprocess_run_mock.assert_called_once_with(
        ['gcloud', 'config', 'get-value', 'account', '--format=json'],
        stdout=ANY,
        stderr=ANY,
        universal_newlines=ANY,
        check=ANY)

  def ttest_config_get_account_raises_as_expected_on_gcloud_failure(self):
    self.subprocess_run_mock.return_value = \
      subprocess.CompletedProcess(args=ANY, returncode=1)

    # Simply patching stderr to suppress output to terminal.
    with self.assertRaises(SilentlyExitError), \
         patch('sys.stderr'):
      self.gcloud_service.config_get_account()

  def test_config_get_account_raises_on_unexpectd_gcloud_output(self):
    # A single non empty string response is expected, so the following
    # will cause it to fail.
    testcases = [
        ('Not a string', '[]'),
        ('Empty string', '""'),
    ]

    for test_name, data in testcases:
      with self.subTest(test_name):
        return_value = subprocess.CompletedProcess(args=ANY, returncode=0)
        return_value.stdout = data
        self.subprocess_run_mock.return_value = return_value

        with self.assertRaises(SilentlyExitError), \
             patch('sys.stdout', new_callable=StringIO) as out, \
             patch('sys.stderr', new_callable=StringIO) as err:
          self.gcloud_service.config_get_account()

        self.assertIn(
            'An error occured attempting to parse the account obtained from '
            'gcloud', err.getvalue())
        self.assertIn(f'Gcloud output: {json.loads(data)}', err.getvalue())
        self.assertEqual('', out.getvalue())

  def test_config_get_project_works_as_expected(self):
    return_value = subprocess.CompletedProcess(args=ANY, returncode=0)
    return_value.stdout = '"cli-test-project"'
    self.subprocess_run_mock.return_value = return_value

    obtained_project = self.gcloud_service.config_get_project()

    self.assertEqual('cli-test-project', obtained_project)
    self.subprocess_run_mock.assert_called_once_with(
        ['gcloud', 'config', 'get-value', 'project', '--format=json'],
        stdout=ANY,
        stderr=ANY,
        universal_newlines=ANY,
        check=ANY)

  def test_config_get_project_raises_as_expected_on_gcloud_failure(self):
    self.subprocess_run_mock.return_value = \
      subprocess.CompletedProcess(args=ANY, returncode=1)

    # Simply patching stderr to suppress output to terminal.
    with self.assertRaises(SilentlyExitError), \
         patch('sys.stderr'):
      self.gcloud_service.config_get_project()

  def test_config_get_project_raises_on_unexpectd_gcloud_output(self):
    # A single non empty string response is expected, so the following
    # will cause it to fail.
    testcases = [
        ('Not a string', '[]'),
        ('Empty string', '""'),
    ]

    for test_name, data in testcases:
      with self.subTest(test_name):
        return_value = subprocess.CompletedProcess(args=ANY, returncode=0)
        return_value.stdout = data
        self.subprocess_run_mock.return_value = return_value

        with self.assertRaises(SilentlyExitError), \
             patch('sys.stdout', new_callable=StringIO) as out, \
             patch('sys.stderr', new_callable=StringIO) as err:
          self.gcloud_service.config_get_project()

        self.assertIn(
            'An error occured attempting to parse the project ID obtained from '
            'gcloud', err.getvalue())
        self.assertIn(f'Gcloud output: {json.loads(data)}', err.getvalue())
        self.assertEqual('', out.getvalue())

  def test_get_access_token_works_as_expected(self):
    return_value = subprocess.CompletedProcess(args=ANY, returncode=0)
    return_value.stdout = '{"token": "fake-token"}'
    self.subprocess_run_mock.return_value = return_value

    obtained_token = self.gcloud_service.get_access_token()

    self.assertEqual('fake-token', obtained_token)
    self.subprocess_run_mock.assert_called_once_with(
        ['gcloud', 'auth', 'print-access-token', '--format=json'],
        stdout=ANY,
        stderr=ANY,
        universal_newlines=ANY,
        check=ANY)

  def test_get_access_token_raises_as_expected_on_gcloud_failure(self):
    self.subprocess_run_mock.return_value = \
      subprocess.CompletedProcess(args=ANY, returncode=1)

    # Simply patching stderr to suppress output to terminal.
    with self.assertRaises(SilentlyExitError), \
         patch('sys.stderr'):
      self.gcloud_service.get_access_token()

  def test_get_access_token_raises_on_unexpectd_gcloud_output(self):
    # It requires a dict of the form: {'token': '<value>'}
    testcases = [
        ('Not a dict 1', '[]'),
        ('Not a dict 2', '"foo"'),
        ('Missing token key', '{}'),
        ('Token Not A String', '{"token": []}'),
        ('Token Is Empty String', '{"token": ""}'),
    ]

    for test_name, data in testcases:
      with self.subTest(test_name):
        return_value = subprocess.CompletedProcess(args=ANY, returncode=0)
        return_value.stdout = data
        self.subprocess_run_mock.return_value = return_value

        with self.assertRaises(SilentlyExitError), \
             patch('sys.stdout', new_callable=StringIO) as out, \
             patch('sys.stderr', new_callable=StringIO) as err:
          self.gcloud_service.get_access_token()

        self.assertIn(
            'An error occured attempting to parse the access token obtained '
            'from gcloud', err.getvalue())
        self.assertIn(f'Gcloud output: {json.loads(data)}', err.getvalue())
        self.assertEqual('', out.getvalue())

  def test_is_api_enabled_works_as_expected(self):
    testcases = [
        # (Test name, gcloud response, expected_is_enabled)
        ('Enabled', '["Just need non empty array to indicate enabled"]', True),
        ('Not Enabled', '[]', False),
    ]

    for test_name, gcloud_response, expected_is_enabled in testcases:
      with self.subTest(test_name):
        self.subprocess_run_mock.reset_mock()
        return_value = subprocess.CompletedProcess(args=ANY, returncode=0)
        return_value.stdout = gcloud_response
        self.subprocess_run_mock.return_value = return_value

        obtained_is_enabled = self.gcloud_service.is_api_enabled(
            'test-api-name')

        self.assertEqual(expected_is_enabled, obtained_is_enabled)
        self.subprocess_run_mock.assert_called_once_with(
            [
                'gcloud', 'services', 'list', '--enabled',
                '--filter=config.name=test-api-name', '--format=json'
            ],
            stdout=ANY,
            stderr=ANY,
            universal_newlines=ANY,
            check=ANY)  # yapf: disabled (Hand formatting more readable here.)

  def test_is_api_enabled_raises_as_expected_on_gcloud_failure(self):
    self.subprocess_run_mock.return_value = \
      subprocess.CompletedProcess(args=ANY, returncode=1)

    # Simply patching stderr to suppress output to terminal.
    with self.assertRaises(SilentlyExitError), \
         patch('sys.stderr'):
      self.gcloud_service.is_api_enabled('test-api-name')

  def test_is_api_enabled_raises_on_unexpectd_gcloud_output(self):
    # The is_api_enabled method simply needs a list, and it will check if it's
    # empty or not.
    testcases = [
        ('Not a list 1', '{}'),
        ('Not a list 2', '"foo"'),
    ]

    for test_name, data in testcases:
      with self.subTest(test_name):
        return_value = subprocess.CompletedProcess(args=ANY, returncode=0)
        return_value.stdout = data
        self.subprocess_run_mock.return_value = return_value

        with self.assertRaises(SilentlyExitError), \
             patch('sys.stdout', new_callable=StringIO) as out, \
             patch('sys.stderr', new_callable=StringIO) as err:
          self.gcloud_service.is_api_enabled('foo-api')

        self.assertIn(
            'An error occured attempting to parse the gcloud services output '
            'from gcloud', err.getvalue())
        self.assertIn(f'Gcloud output: {json.loads(data)}', err.getvalue())
        self.assertEqual('', out.getvalue())

  def test_enable_api_works_as_expected(self):
    self.gcloud_service.enable_api('test-api')

    self.subprocess_run_mock.assert_called_once_with(
        ['gcloud', 'services', 'enable', 'test-api', '--format=json'],
        stdout=ANY,
        stderr=ANY,
        universal_newlines=ANY,
        check=ANY)

  def test_enable_api_raises_as_expected_on_gcloud_failure(self):
    self.subprocess_run_mock.return_value = \
      subprocess.CompletedProcess(args=ANY, returncode=1)

    # Simply patching stderr to suppress output to terminal.
    with self.assertRaises(SilentlyExitError), \
         patch('sys.stderr'):
      self.gcloud_service.enable_api('test-api-name')
