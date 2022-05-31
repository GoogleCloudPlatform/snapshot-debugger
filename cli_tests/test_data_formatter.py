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
from cli import data_formatter


class SnapshotDebuggerSchemaTests(unittest.TestCase):
  """ Contains the unit tests for the SnapshotDebuggerSchema class.
  """

  def setUp(self):
    self.formatter = data_formatter.DataFormatter()

  def test_build_table_works_as_expected(self):
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

    headers3 = ['C1', 'C22', 'C333', 'C4444']
    values3 = [
        ('V1_1', 'V2_1', 'V3_1', 'V4_1'),
        ('V1_2', 'V2_2', 'V3_2', 'V4_2'),
        ('V1_3', 'V2_3', 'V3_3', 'V4_3'),
        ('V1_4', 'V2_4', 'V3_4', 'V4_4'),
    ]
    # There's two spaces between each column, and the widest field
    # in the column (header or row value) dictates width.
    output3 = ('C1    C22   C333  C4444\n'
               '----  ----  ----  -----\n'
               'V1_1  V2_1  V3_1  V4_1 \n'
               'V1_2  V2_2  V3_2  V4_2 \n'
               'V1_3  V2_3  V3_3  V4_3 \n'
               'V1_4  V2_4  V3_4  V4_4 \n')

    testcases = [((headers1, values1), output1), ((headers2, values2), output2),
                 ((headers3, values3), output3)]

    for args, expected_output in testcases:
      with self.subTest():
        actual_output = self.formatter.build_table(args[0], args[1])
        self.assertEqual(actual_output, expected_output)


if __name__ == '__main__':
  unittest.main()
