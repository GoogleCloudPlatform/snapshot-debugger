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
""" Unit test file for the status_message module.
"""

import unittest

from snapshot_dbg_cli.status_message import StatusMessage


class StatusMessageTests(unittest.TestCase):
  """ Contains the unit tests for the status_message module.
  """

  def test_is_error(self):
    testcases = [
        ('No status', {}, None),
        ('No isError', {
            'status': {}
        }, False),
        ('Explicit False', {
            'status': {
                'isError': False
            }
        }, False),
        ('Explicit True', {
            'status': {
                'isError': True
            }
        }, True),
    ]

    for test_name, parent, expected_is_error in testcases:
      with self.subTest(test_name):
        self.assertEqual(expected_is_error, StatusMessage(parent).is_error)

  def test_refers_to(self):
    testcases = [
        ('No status', {}, None),
        ('No refersTo', {
            'status': {}
        }, None),
        ('Value set', {
            'status': {
                'refersTo': 'BREAKPOINT_AGE'
            }
        }, 'BREAKPOINT_AGE'),
    ]

    for test_name, parent, expected_refers_to in testcases:
      with self.subTest(test_name):
        self.assertEqual(expected_refers_to, StatusMessage(parent).refers_to)

  def test_parsed_message_valid_input(self):
    testcases = [
        ('No Parameters', 'A simple message', [], 'A simple message'),
        ('One Parameter', 'Calc took $0 seconds', ['30'],
         'Calc took 30 seconds'),
        ('Multiple Parameters', 'A $0 $1 simple message $0', ['not', 'so'],
         'A not so simple message not'),
        ('Escaped message', 'A $$20 simple message$0', ['!'],
         'A $20 simple message!'),
        ("Format in '$' chars", 'A $0 $1 simple message $2',
         ['$1', 'weird', '$0'], 'A $1 weird simple message $0'),
        ("Allow trailing '$' chars", 'A simple message $', [],
         'A simple message $'),
        ("Ignore extra '$' chars", 'A simple $0 message', [],
         'A simple $0 message'),
        ('Parameters not set', 'A simple $0 message', None,
         'A simple $0 message'),
    ]

    for test_name, format_str, parameters, expected_parsed_message in testcases:
      with self.subTest(test_name):
        parent = {'status': {'description': {'format': format_str}}}

        if parameters is not None:
          parent['status']['description']['parameters'] = parameters

        self.assertEqual(expected_parsed_message,
                         StatusMessage(parent).parsed_message)

  def test_parsed_message_invalid_input(self):
    self.assertEqual(None, StatusMessage({}).parsed_message)
    self.assertEqual(None, StatusMessage({'status': {}}).parsed_message)
    testcases = [
        ('Missing status', {}),
        ('Missing description', {
            'status': {}
        }),
        ('Missing format', {
            'status': {
                'description': {}
            }
        }),
    ]

    for test_name, parent in testcases:
      with self.subTest(test_name):
        self.assertIsNone(StatusMessage(parent).parsed_message)
