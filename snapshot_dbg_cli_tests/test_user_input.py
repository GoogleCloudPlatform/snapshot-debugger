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
""" Unit test file for the user_input module.
"""

import unittest

from snapshot_dbg_cli.user_input import UserInput
from unittest.mock import MagicMock
from unittest.mock import call
from unittest.mock import patch


class SnapshotDebuggerSchemaTests(unittest.TestCase):
  """Contains the unit tests for the user_input module.
  """

  def test_prompt_user_to_continue(self):
    testcases = [
        ([''], True),
        (['o', ''], True),
        (['foo', ''], True),
        (['o', 'f', ''], True),
        (['y'], True),
        (['o', 'y'], True),
        (['Y'], True),
        (['foo', 'n'], False),
        (['n'], False),
        (['o', 'n'], False),
        (['N'], False),
        (['o', 'N'], False),
    ]

    for input_sequence, expected_response in testcases:
      with self.subTest(input_sequence):
        with patch('builtins.input',
                   MagicMock(side_effect=input_sequence)) as input_mock:
          expected_calls = [call('Do you want to continue (Y/n)? ')]
          for _ in range(0, len(input_sequence) - 1):
            expected_calls.append(call("Please enter 'y' or 'n': "))

          self.assertEqual(expected_response,
                           UserInput().prompt_user_to_continue())
          self.assertEqual(expected_calls, input_mock.mock_calls)
