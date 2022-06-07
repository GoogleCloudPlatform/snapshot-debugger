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
""" Unit test file for the DataFormatter class.
"""

import unittest
from snapshot_dbg_cli import data_formatter
import json


class SnapshotDebuggerSchemaTests(unittest.TestCase):
  """ Contains the unit tests for the DataFormatter class.

  To note, tne to_json_string tests are not exhaustive as we are simply wrapping
  the json python library, they are simply enough to ensure the method is doing
  what it is supposed to.
  """

  def setUp(self):
    self.formatter = data_formatter.DataFormatter()

  def test_build_table_works_as_expected(self):
    headers_values_empty = ['Co11', 'Col2']
    values_empty = []
    output_values_empty = ('Co11  Col2\n'
                           '----  ----\n')

    headers1 = ['Col1']
    values1 = [('Val1',)]
    output1 = ('Col1\n'
               '----\n'
               'Val1\n')

    headers2 = ['Col1']
    values2 = [('Val1',), ('Val22',)]
    output2 = ('Col1 \n'
               '-----\n'
               'Val1 \n'
               'Val22\n')

    headers3 = ['C1', 'C22', 'C333', 'C4444', 'C55555*']
    values3 = [
        ('V1_1*', 'V2_1', 'V3_1', 'V4_1', 'V5_1'),
        ('V1_2', 'V2_2*', 'V3_2', 'V4_2', 'V5_2'),
        ('V1_3', 'V2_3', 'V3_3*', 'V4_3', 'V5_3'),
        ('V1_4', 'V2_4', 'V3_4', 'V4_4**', 'V5_4'),
    ]
    # There should be two spaces between each column, and the widest field in
    # the column (header or row value) dictates width. The * here is the field
    # that dictates the width.
    output3 = ('C1     C22    C333   C4444   C55555*\n'
               '-----  -----  -----  ------  -------\n'
               'V1_1*  V2_1   V3_1   V4_1    V5_1   \n'
               'V1_2   V2_2*  V3_2   V4_2    V5_2   \n'
               'V1_3   V2_3   V3_3*  V4_3    V5_3   \n'
               'V1_4   V2_4   V3_4   V4_4**  V5_4   \n')

    testcases = [('Values empty', (headers_values_empty, values_empty),
                  output_values_empty),
                 ('One Col, One Val', (headers1, values1), output1),
                 ('One Col, Two Val', (headers2, values2), output2),
                 ('Multi Col Multi Val', (headers3, values3), output3)]

    for test_name, args, expected_output in testcases:
      with self.subTest(test_name):
        actual_output = self.formatter.build_table(args[0], args[1])
        self.assertEqual(actual_output, expected_output)

  def test_to_json_string_pretty_false_produces_valid_json(self):
    test_data = {'k1': 'v1', 'k2': {'k3': 'v3'}, 'k4': [1, 2, 3, 4]}
    json_string = self.formatter.to_json_string(test_data, pretty=False)
    json_parse = json.loads(json_string)
    self.assertEqual(json_parse, test_data)

  def test_to_json_string_pretty_false_is_compact(self):
    test_data = {'k1': 'v1', 'k2': {'k3': 'v3'}, 'k4': [1, 2, 3, 4]}
    json_string = self.formatter.to_json_string(test_data, pretty=False)

    # When setting pretty to False the representation is expected to be compact
    # and not formatted for human readability.
    self.assertEqual(json_string.count('\n'), 0)

  def test_to_json_string_pretty_true_produces_valid_json(self):
    test_data = {'k1': 'v1', 'k2': {'k3': 'v3'}, 'k4': [1, 2, 3, 4]}
    json_string = self.formatter.to_json_string(test_data, pretty=True)
    json_parse = json.loads(json_string)
    self.assertEqual(json_parse, test_data)

  def test_to_json_string_pretty_true_is_human_readable(self):
    test_data = {'k1': 'v1', 'k2': {'k3': 'v3'}, 'k4': [1, 2, 3, 4]}
    json_string = self.formatter.to_json_string(test_data, pretty=True)

    # Just a simple heuristic to check that setting pretty to True causes some
    # newlines indicating it's human readable.
    self.assertGreater(json_string.count('\n'), 10)


if __name__ == '__main__':
  unittest.main()
