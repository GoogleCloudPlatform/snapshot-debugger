# Copyright 2023 Google LLC
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
""" Unit test file for the firebase_types module.
"""

import unittest
from snapshot_dbg_cli.firebase_types import DatabaseInstance


class DatabaseInstanceTests(unittest.TestCase):
  """ Contains the unit tests for the DatabaseInstance class.
  """

  def test_location_success(self):
    locations = ['us-central1', 'europe-west1']
    for location in locations:
      with self.subTest(location):
        db_instance = DatabaseInstance({
            'name':
                f'projects/1111111111/locations/{location}/instances/foo-cdbg',
            'project':
                'projects/1111111111',
            'databaseUrl':
                'https://foo-cdbg.firebaseio.com',
            'type':
                'USER_DATABASE',
            'state':
                'ACTIVE'
        })
        self.assertEqual(location, db_instance.location)

  def test_location_could_not_be_found(self):
    invalid_names = [
        '',
        'foo',
        # missing the /locations/
        'projects/1111111111/us-central1/instances/foo-cdbg',
        'projects/1111111111/locations',
        'projects/1111111111/locations/'
    ]

    for full_db_name in invalid_names:
      with self.subTest(full_db_name):
        with self.assertRaises(ValueError) as ctxt:
          DatabaseInstance({
              'name': full_db_name,
              'project': 'projects/1111111111',
              'databaseUrl': 'https://foo-cdbg.firebaseio.com',
              'type': 'USER_DATABASE',
              'state': 'ACTIVE'
          })
        self.assertEqual(
            f"Failed to extract location from project name '{full_db_name}'",
            str(ctxt.exception))
