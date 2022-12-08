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
""" Unit test file for the snapshot_debugger_rtdb_service module.
"""

import unittest

from snapshot_dbg_cli import data_formatter
from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli.firebase_rtdb_rest_service import FirebaseRtdbRestService
from snapshot_dbg_cli.snapshot_debugger_rtdb_service import SnapshotDebuggerRtdbService
from snapshot_dbg_cli.snapshot_debugger_schema import SnapshotDebuggerSchema
from snapshot_dbg_cli.user_output import UserOutput

from io import StringIO
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch

DEBUGGEE_1 = {
    'id': '123',
    'labels': {
        'module': 'app123',
        'version': 'v1'
    },
    'description': 'desc 1'
}

DEBUGGEE_2 = {
    'id': '456',
    'labels': {
        'module': 'app456',
        'version': 'v2'
    },
    'description': 'desc 2'
}


def debuggees_to_dict(debuggees):
  return dict((d['id'], d) for d in debuggees)

SNAPSHOT_ACTIVE =  {
  'action': 'CAPTURE',
  'createTimeUnixMsec': 1649962215426,
  'id': 'b-1650000000',
  'isFinalState': False,
  'location': {'line': 26, 'path': 'index.js'},
  'userEmail': 'user@foo.com',
  'createTime': '2022-04-14T18:50:15.852000Z',
} # yapf: disable (Subjectively, more readable hand formatted)

SNAPSHOT_COMPLETED =  {
  'action': 'CAPTURE',
  'createTimeUnixMsec': 1649962215426,
  'id': 'b-1650000001',
  'isFinalState': True,
  'location': {'line': 28, 'path': 'index.js'},
  'userEmail': 'user@foo.com',
  'createTime': '2022-04-14T18:50:15.852000Z',
} # yapf: disable (Subjectively, more readable hand formatted)

LOGPOINT_ACTIVE =  {
  'action': 'LOG',
  'createTimeUnixMsec': 1649962215426,
  'id': 'b-1650000002',
  'isFinalState': False,
  'location': {'line': 26, 'path': 'index.js'},
  'userEmail': 'user@foo.com',
  'createTime': '2022-04-14T18:50:15.852000Z',
  'logMessageFormat': 'Message 1',
} # yapf: disable (Subjectively, more readable hand formatted)

LOGPOINT_COMPLETED =  {
  'action': 'LOG',
  'createTimeUnixMsec': 1649962215426,
  'id': 'b-1650000003',
  'isFinalState': True,
  'location': {'line': 28, 'path': 'index.js'},
  'userEmail': 'user@foo.com',
  'createTime': '2022-04-14T18:50:15.852000Z',
  'logMessageFormat': 'Message 2',
} # yapf: disable (Subjectively, more readable hand formatted)


class SnapshotDebuggerRtdbServiceTests(unittest.TestCase):
  """ Contains the unit tests for the DeleteSnapshotsCommand class.
  """

  def setUp(self):
    self.firebase_rtdb_service_mock = MagicMock(spec=FirebaseRtdbRestService)

    self.schema = SnapshotDebuggerSchema()

    self.user_output_mock = MagicMock(
        wraps=UserOutput(
            is_debug_enabled=False,
            data_formatter=data_formatter.DataFormatter()))

    self.debugger_rtdb_service = SnapshotDebuggerRtdbService(
        self.firebase_rtdb_service_mock, self.schema, self.user_output_mock)

  def test_get_schema_version_works_as_expected(self):
    self.firebase_rtdb_service_mock.get = MagicMock(return_value='1')

    version = self.debugger_rtdb_service.get_schema_version()

    self.assertEqual('1', version)
    self.firebase_rtdb_service_mock.get.assert_called_once_with(
        self.schema.get_path_schema_version())

  def test_set_schema_version_works_as_expected(self):
    self.firebase_rtdb_service_mock.set = MagicMock(return_value='1')

    version = self.debugger_rtdb_service.set_schema_version('1')

    self.firebase_rtdb_service_mock.set.assert_called_once_with(
        self.schema.get_path_schema_version(), '1')

    self.assertEqual('1', version)

  def test_get_debuggees_works_as_expected(self):
    current_time = 1649962215000888

    self.firebase_rtdb_service_mock.get = MagicMock(
        return_value=debuggees_to_dict([DEBUGGEE_1, DEBUGGEE_2]))

    debuggees = self.debugger_rtdb_service.get_debuggees(current_time)

    self.assertEqual([DEBUGGEE_1, DEBUGGEE_2], debuggees)
    self.firebase_rtdb_service_mock.get.assert_called_once_with(
        self.schema.get_path_debuggees())

  def test_validate_debuggee_id_returns_normally_when_id_found(self):
    self.firebase_rtdb_service_mock.get = MagicMock(return_value=DEBUGGEE_1)

    self.debugger_rtdb_service.validate_debuggee_id('123')

    expected_path = self.schema.get_path_debuggees_for_id('123')
    self.firebase_rtdb_service_mock.get.assert_called_once_with(expected_path)

  def test_validate_debuggee_id_raises_and_emits_error_when_id_not_found(self):
    self.firebase_rtdb_service_mock.get = MagicMock(return_value=None)

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.debugger_rtdb_service.validate_debuggee_id('123')

    expected_path = self.schema.get_path_debuggees_for_id('123')
    self.firebase_rtdb_service_mock.get.assert_called_once_with(expected_path)
    self.assertEqual(
        'Debuggee ID 123 was not found.  Specify a debuggee ID found in the '
        'result of the list_debuggees command.\n', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_get_new_breakpoint_id_works_as_expected_when_id_is_free(self):
    # The method will test the active and final breakpoints paths to see if the
    # ID exists. Returning None indicates they don't and so the ID is free.
    self.firebase_rtdb_service_mock.get = MagicMock(return_value=None)

    with patch('time.time', MagicMock(return_value='1650000000')):
      obtained_id = self.debugger_rtdb_service.get_new_breakpoint_id('123')

    self.assertEqual('b-1650000000', obtained_id)

  def test_get_new_breakpoint_id_retries_on_active_id_conflict(self):
    # For context, the active and final paths are of the form:
    # cdbg/breakpoints/123/active/b-1650000000
    # cdbg/breakpoints/123/final/b-1650000000
    def get_response(path, shallow):
      del shallow  # Unused
      if 'active' in path and 'b-1650000000' in path:
        # Just need to return a snapshot to indicate the ID is not available.
        return SNAPSHOT_ACTIVE
      else:
        return None

    self.firebase_rtdb_service_mock.get = MagicMock(side_effect=get_response)

    with patch('time.time', MagicMock(return_value='1650000000')):
      obtained_id = self.debugger_rtdb_service.get_new_breakpoint_id('123')

    self.assertEqual('b-1650000001', obtained_id)
    self.assertEqual([
        call(
            self.schema.get_path_breakpoints_active_for_id(
                '123', 'b-1650000000'),
            shallow=True),
        call(
            self.schema.get_path_breakpoints_active_for_id(
                '123', 'b-1650000001'),
            shallow=True),
        call(
            self.schema.get_path_breakpoints_final_for_id(
                '123', 'b-1650000001'),
            shallow=True),
    ], self.firebase_rtdb_service_mock.get.mock_calls)

  def test_get_new_breakpoint_id_retries_on_final_id_conflict(self):
    # For context, the active and final paths are of the form:
    # cdbg/breakpoints/123/active/b-1650000000
    # cdbg/breakpoints/123/final/b-1650000000
    def get_response(path, shallow):
      del shallow  # Unused
      if 'final' in path and 'b-1650000000' in path:
        # Just need to return a snapshot to indicate the ID is not available.
        return SNAPSHOT_ACTIVE
      else:
        return None

    self.firebase_rtdb_service_mock.get = MagicMock(side_effect=get_response)

    with patch('time.time', MagicMock(return_value='1650000000')):
      obtained_id = self.debugger_rtdb_service.get_new_breakpoint_id('123')

    self.assertEqual('b-1650000001', obtained_id)
    self.assertEqual([
        call(
            self.schema.get_path_breakpoints_active_for_id(
                '123', 'b-1650000000'),
            shallow=True),
        call(
            self.schema.get_path_breakpoints_final_for_id(
                '123', 'b-1650000000'),
            shallow=True),
        call(
            self.schema.get_path_breakpoints_active_for_id(
                '123', 'b-1650000001'),
            shallow=True),
        call(
            self.schema.get_path_breakpoints_final_for_id(
                '123', 'b-1650000001'),
            shallow=True),
    ], self.firebase_rtdb_service_mock.get.mock_calls)

  def test_get_new_breakpoint_id_eventually_raises_and_emits_error(self):
    # Just need to return a snapshot to indicate the ID is not available.
    self.firebase_rtdb_service_mock.get = MagicMock(
        return_value=SNAPSHOT_ACTIVE)

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err, \
         patch('time.time', MagicMock(return_value = '1650000000')):

      self.debugger_rtdb_service.get_new_breakpoint_id('123')

    bp_id = 1650000000
    expected_calls = []
    for i in range(0, 10):
      expected_calls.append(
          call(
              self.schema.get_path_breakpoints_active_for_id(
                  '123', f'b-{bp_id+i}'),
              shallow=True))

    self.assertEqual(expected_calls,
                     self.firebase_rtdb_service_mock.get.mock_calls)
    self.assertEqual(
        'ERROR Failed to determine a new breakpoint ID, please try again\n',
        err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_delete_breakpoints_works_ask_expected(self):
    testcases = [
        # (Test name, breakpoints, expected delete paths)
        (
            'Snapshot Active',
            [SNAPSHOT_ACTIVE],
            [
                # For active snapshots, all three paths are expected to be
                # attempted.
                call(self.schema.get_path_breakpoints_active_for_id(
                    '123', SNAPSHOT_ACTIVE['id'])),
                call(self.schema.get_path_breakpoints_final_for_id(
                    '123', SNAPSHOT_ACTIVE['id'])),
                call(self.schema.get_path_breakpoints_snapshot_for_id(
                    '123', SNAPSHOT_ACTIVE['id'])),
            ]
        ),
        (
            'Snapshot Completed',
            [SNAPSHOT_COMPLETED],
            [
                # Since it's already complete, the active path should not be
                # attempted.
                call(self.schema.get_path_breakpoints_final_for_id(
                    '123', SNAPSHOT_COMPLETED['id'])),
                call(self.schema.get_path_breakpoints_snapshot_for_id(
                    '123', SNAPSHOT_COMPLETED['id'])),
            ]
        ),
        (
            'Logpoint Active',
            [LOGPOINT_ACTIVE],
            [
                # Since it's not a snapshot, the snpashot path should not be
                # attempted.
                call(self.schema.get_path_breakpoints_active_for_id(
                    '123', LOGPOINT_ACTIVE['id'])),
                call(self.schema.get_path_breakpoints_final_for_id(
                    '123', LOGPOINT_ACTIVE['id'])),
            ]
        ),
        (
            'Logpoint Completed',
            [LOGPOINT_COMPLETED],
            [
                # Since it's complete and not a snapshot, only the final path
                # should be attempted.
                call(self.schema.get_path_breakpoints_final_for_id(
                    '123', LOGPOINT_COMPLETED['id'])),
            ]
        ),
        (
            'Multiple breakpoints',
            [SNAPSHOT_ACTIVE, SNAPSHOT_COMPLETED],
            [
                call(self.schema.get_path_breakpoints_active_for_id(
                    '123', SNAPSHOT_ACTIVE['id'])),
                call(self.schema.get_path_breakpoints_final_for_id(
                    '123', SNAPSHOT_ACTIVE['id'])),
                call(self.schema.get_path_breakpoints_snapshot_for_id(
                    '123', SNAPSHOT_ACTIVE['id'])),
                call(self.schema.get_path_breakpoints_final_for_id(
                    '123', SNAPSHOT_COMPLETED['id'])),
                call(self.schema.get_path_breakpoints_snapshot_for_id(
                    '123', SNAPSHOT_COMPLETED['id'])),
            ]
        ),
    ] # yapf: disable (Subjectively, more readable hand formatted)

    for test_name, breakpoints, expected_delete_paths in testcases:
      with self.subTest(test_name):
        self.firebase_rtdb_service_mock.reset_mock()

        self.debugger_rtdb_service.delete_breakpoints('123', breakpoints)

        self.assertEqual(expected_delete_paths,
                         self.firebase_rtdb_service_mock.delete.mock_calls)

  def test_get_breakpoint_works_as_expected(self):
    testcases = [
        # (Test name, Get side_effects, Expected Snapshot, Expected get calls)
        (
          'Breakpoint Active',
          [SNAPSHOT_ACTIVE],
          SNAPSHOT_ACTIVE,
          [call(self.schema.get_path_breakpoints_active_for_id(
              '123', 'b-1650000000'), shallow=False)]
        ),
        (
          'Breakpoint Completed',
          # First call to get should return None, that's the active path
          # lookup failure which should prompted the final path lookup.
          [None, SNAPSHOT_COMPLETED],
          SNAPSHOT_COMPLETED,
          [call(self.schema.get_path_breakpoints_active_for_id(
              '123', 'b-1650000000'), shallow=False),
           call(self.schema.get_path_breakpoints_final_for_id(
              '123', 'b-1650000000'), shallow=False)]
        ),
        (
          'Breakpoint Not Found',
          # Both the active and final path lookups should return None,
          # indicating the breakpoint does not exist.
          [None, None],
          None,
          [call(self.schema.get_path_breakpoints_active_for_id(
              '123', 'b-1650000000'), shallow=False),
           call(self.schema.get_path_breakpoints_final_for_id(
              '123', 'b-1650000000'), shallow=False)]
        ),
    ] # yapf: disable (Subjectively, more readable hand formatted)

    for test_name, side_effect, expected_snapshot, expected_calls in testcases:
      with self.subTest(test_name):
        self.firebase_rtdb_service_mock.get = MagicMock(side_effect=side_effect)

        obtained_snapshot = self.debugger_rtdb_service.get_breakpoint(
            '123', 'b-1650000000')

        self.assertEqual(expected_snapshot, obtained_snapshot)

        self.assertEqual(expected_calls,
                         self.firebase_rtdb_service_mock.get.mock_calls)

  def test_get_breakpoint_normalizes_bp(self):
    """This test focuses solely on ensuring the breakpoint gets normalized.

    The breakpoint returned by get_breakpoint() should have the
    breakpoint_utils.normalize_breakpoint function applied to it. This
    ensures all expected fields are set and calling code can assume they exist.
    """

    bp = SNAPSHOT_ACTIVE.copy()

    # If we don't populate the action, the normalize_breakpoint call will
    # default it to 'CAPTURE' and populate it.
    # 'action': 'CAPTURE',
    del bp['action']
    self.assertNotIn('action', bp)

    self.firebase_rtdb_service_mock.get = MagicMock(return_value=bp)

    obtained_snapshot = self.debugger_rtdb_service.get_breakpoint(
        '123', 'b-123')

    # This field will have been set by the call to normalize_breakpoint which
    # ensures it was called as expected.
    self.assertIn('action', obtained_snapshot)
    self.assertEqual('CAPTURE', obtained_snapshot['action'])

  def test_get_snapshot_detailed_works_as_expected(self):
    testcases = [
        # (Test name, Get side_effects, Expected Snapshot, Expected get calls)
        (
          'Snapshot Active',
          [SNAPSHOT_ACTIVE],
          SNAPSHOT_ACTIVE,
          [call(self.schema.get_path_breakpoints_active_for_id(
              '123', 'b-1650000000'))]
        ),
        (
          'Snapshot Completed',
          # First call to get should return None, that's the active path
          # lookup failure which should prompted the snapshot path lookup.
          [None, SNAPSHOT_COMPLETED],
          SNAPSHOT_COMPLETED,
          [call(self.schema.get_path_breakpoints_active_for_id(
              '123', 'b-1650000000')),
           call(self.schema.get_path_breakpoints_snapshot_for_id(
              '123', 'b-1650000000'))]
        ),
        (
          'Snapshot Not Found',
          # Both the active and snapshot path lookups should return None,
          # indicating the snapshot does not exist.
          [None, None],
          None,
          [call(self.schema.get_path_breakpoints_active_for_id(
              '123', 'b-1650000000')),
           call(self.schema.get_path_breakpoints_snapshot_for_id(
              '123', 'b-1650000000'))]
        ),
    ] # yapf: disable (Subjectively, more readable hand formatted)

    for test_name, side_effect, expected_snapshot, expected_calls in testcases:
      with self.subTest(test_name):
        self.firebase_rtdb_service_mock.get = MagicMock(side_effect=side_effect)

        obtained_snapshot = self.debugger_rtdb_service.get_snapshot_detailed(
            '123', 'b-1650000000')

        self.assertEqual(expected_snapshot, obtained_snapshot)

        self.assertEqual(expected_calls,
                         self.firebase_rtdb_service_mock.get.mock_calls)

  def test_get_snapshot_detailed_normalizes_bp(self):
    """This test focuses solely on ensuring the snapshot gets normalized.

    The snapshot returned by get_snapshot_detailed() should have the
    breakpoint_utils.normalize_breakpoint function applied to it. This
    ensures all expected fields are set and calling code can assume they exist.
    """

    bp = SNAPSHOT_ACTIVE.copy()

    # If we don't populate the action, the normalize_breakpoint call will
    # default it to 'CAPTURE' and populate it.
    # 'action': 'CAPTURE',
    del bp['action']
    self.assertNotIn('action', bp)

    self.firebase_rtdb_service_mock.get = MagicMock(return_value=bp)

    obtained_snapshot = self.debugger_rtdb_service.get_snapshot_detailed(
        '123', 'b-123')

    # This field will have been set by the call to normalize_breakpoint which
    # ensures it was called as expected.
    self.assertIn('action', obtained_snapshot)
    self.assertEqual('CAPTURE', obtained_snapshot['action'])

  def test_get_logpoints_works_as_expected(self):
    snapshot_active_user1 = SNAPSHOT_ACTIVE.copy()
    snapshot_active_user1['id'] = 'b-1650000000'
    snapshot_active_user1['userEmail'] = 'user1@foo.com'

    snapshot_active_user2 = SNAPSHOT_ACTIVE.copy()
    snapshot_active_user2['id'] = 'b-1650000001'
    snapshot_active_user2['userEmail'] = 'user2@foo.com'

    snapshot_completed_user1 = SNAPSHOT_COMPLETED.copy()
    snapshot_completed_user1['id'] = 'b-1650000002'
    snapshot_completed_user1['userEmail'] = 'user1@foo.com'

    snapshot_completed_user2 = SNAPSHOT_COMPLETED.copy()
    snapshot_completed_user2['id'] = 'b-1650000003'
    snapshot_completed_user2['userEmail'] = 'user2@foo.com'

    logpoint_active_user1 = LOGPOINT_ACTIVE.copy()
    logpoint_active_user1['id'] = 'b-1650000004'
    logpoint_active_user1['userEmail'] = 'user1@foo.com'

    logpoint_active_user2 = LOGPOINT_ACTIVE.copy()
    logpoint_active_user2['id'] = 'b-1650000005'
    logpoint_active_user2['userEmail'] = 'user2@foo.com'

    logpoint_completed_user1 = LOGPOINT_COMPLETED.copy()
    logpoint_completed_user1['id'] = 'b-1650000006'
    logpoint_completed_user1['userEmail'] = 'user1@foo.com'

    logpoint_completed_user2 = LOGPOINT_COMPLETED.copy()
    logpoint_completed_user2['id'] = 'b-1650000007'
    logpoint_completed_user2['userEmail'] = 'user2@foo.com'

    # To note, snapshots are included, this ensures only logpoitns are returned
    # by the get_logpoints call.
    all_active_breakpoints = [
        snapshot_active_user1,
        snapshot_active_user2,
        logpoint_active_user1,
        logpoint_active_user2,
    ]

    all_final_breakpoints = [
        snapshot_completed_user1,
        snapshot_completed_user2,
        logpoint_completed_user1,
        logpoint_completed_user2,
    ]

    # Queries for a list of breakpoints from the Firebase Rest interface will
    # come back in dict form. So we convert array of breakpoints to this form.
    def convert_breakpoints(breakpoints):
      return {bp['id']: bp for bp in breakpoints}

    all_active_breakpoints = convert_breakpoints(all_active_breakpoints)
    all_final_breakpoints = convert_breakpoints(all_final_breakpoints)

    testcases = [
        # (Test name, include_inactive, user_email, active bps query,
        #  final bps query, expected logpoints, expected get calls)
        (
            'Active Only - Individual User',
            False, # include_inactive
            'user1@foo.com',
            all_active_breakpoints,
            None, # Doesn't matter, final path should not be queried
            [logpoint_active_user1],
            [call(self.schema.get_path_breakpoints_active('123'))]
        ),
        (
            'Final Included - Individual User',
            True, # include_inactive
            'user1@foo.com',
            all_active_breakpoints,
            all_final_breakpoints,
            [logpoint_active_user1, logpoint_completed_user1],
            [call(self.schema.get_path_breakpoints_active('123')),
             call(self.schema.get_path_breakpoints_final('123'))]
        ),
        (
            'Active Only - All Users',
            False, # include_inactive
            None, # user email of None means don't filter on email.
            all_active_breakpoints,
            None, # Doesn't matter, final path should not be queried
            [logpoint_active_user1, logpoint_active_user2],
            [call(self.schema.get_path_breakpoints_active('123'))]
        ),
        (
            'Final Included - Individual User',
            True, # include_inactive
            None, # user email of None means don't filter on email.
            all_active_breakpoints,
            all_final_breakpoints,
            [logpoint_active_user1, logpoint_active_user2,
             logpoint_completed_user1, logpoint_completed_user2],
            [call(self.schema.get_path_breakpoints_active('123')),
             call(self.schema.get_path_breakpoints_final('123'))]
        ),
        (
            'User Not Found',
            False, # include_inactive
            'user-not-found@foo.com',
            all_active_breakpoints,
            None, # Doesn't matter, final path should not be queried
            [],
            [call(self.schema.get_path_breakpoints_active('123'))]
        ),
        (
            # To note in practise this scenario may not be possible. If a
            # debuggee has no active breakpoints, e.g. the last one was deleted,
            # the path would cease to exist and so queries to it would instead
            # return None, which is its own test scenario one. That said the
            # code should be able to handle an empty response and so we check
            # for it.
            'Empty responses on path queries',
            True, # include_inactive
            'user1@foo.com',
            {}, # No active breakpoints at all.
            {}, # No final breakpoints at all.
            [], # Expected to get empty array from get_logpoints()
            [call(self.schema.get_path_breakpoints_active('123')),
             call(self.schema.get_path_breakpoints_final('123'))]
        ),
        (
            # This scenario happens if the debuggee has no breakpoints and the
            # path doesn't actually exist. None will be returned for the get
            # query on the path in this case.
            'None responses on path queries',
            True, # include_inactive
            'user1@foo.com',
            None, # No active breakpoints at all.
            None, # No final breakpoints at all.
            [], # Expected to get empty array from get_logpoints()
            [call(self.schema.get_path_breakpoints_active('123')),
             call(self.schema.get_path_breakpoints_final('123'))]
        ),
    ] # yapf: disable (Subjectively, more readable hand formatted)

    for (test_name, include_inactive, user_email, active_breakpoints,
         final_breakpoints, expected_logpoints, expected_calls) in testcases:
      with self.subTest(test_name):
        # The first call to get will be for the active, path, and the second (if
        # it occurs) will be for the final path. Set the array order based on
        # this.
        self.firebase_rtdb_service_mock.get = MagicMock(
            side_effect=[active_breakpoints, final_breakpoints])

        obtained_logpoints = self.debugger_rtdb_service.get_logpoints(
            '123', include_inactive, user_email)

        self.assertEqual(expected_logpoints, obtained_logpoints)
        self.assertEqual(expected_calls,
                         self.firebase_rtdb_service_mock.get.mock_calls)

  def test_get_logpoints_normalizes_bp(self):
    """This test focuses solely on ensuring the logpoints gets normalized.

    The logpoints returned by get_logpoints() should have the
    breakpoint_utils.normalize_breakpoint function applied to them.  This
    ensures all expected fields are set and calling code can assume they exist.
    """

    bp = LOGPOINT_ACTIVE.copy()

    # The logMessageFormatString will get filled in with the user legible
    # version of the log message.
    bp['logMessageFormat'] = 'a: $0'
    bp['expressions'] = ['a']
    self.assertNotIn('logMessageFormatString', bp)

    get_response = {bp['id']: bp}
    self.firebase_rtdb_service_mock.get = MagicMock(return_value=get_response)

    obtained_logpoints = self.debugger_rtdb_service.get_logpoints(
        '123', include_inactive=False)

    # This field will have been set by the call to normalize_breakpoint which
    # ensures it was called as expected.
    self.assertIn('logMessageFormatString', obtained_logpoints[0])
    self.assertEqual('a: {a}', obtained_logpoints[0]['logMessageFormatString'])

  def test_get_snapshots_works_as_expected(self):
    snapshot_active_user1 = SNAPSHOT_ACTIVE.copy()
    snapshot_active_user1['id'] = 'b-1650000000'
    snapshot_active_user1['userEmail'] = 'user1@foo.com'

    snapshot_active_user2 = SNAPSHOT_ACTIVE.copy()
    snapshot_active_user2['id'] = 'b-1650000001'
    snapshot_active_user2['userEmail'] = 'user2@foo.com'

    snapshot_completed_user1 = SNAPSHOT_COMPLETED.copy()
    snapshot_completed_user1['id'] = 'b-1650000002'
    snapshot_completed_user1['userEmail'] = 'user1@foo.com'

    snapshot_completed_user2 = SNAPSHOT_COMPLETED.copy()
    snapshot_completed_user2['id'] = 'b-1650000003'
    snapshot_completed_user2['userEmail'] = 'user2@foo.com'

    logpoint_active_user1 = LOGPOINT_ACTIVE.copy()
    logpoint_active_user1['id'] = 'b-1650000004'
    logpoint_active_user1['userEmail'] = 'user1@foo.com'

    logpoint_active_user2 = LOGPOINT_ACTIVE.copy()
    logpoint_active_user2['id'] = 'b-1650000005'
    logpoint_active_user2['userEmail'] = 'user2@foo.com'

    logpoint_completed_user1 = LOGPOINT_COMPLETED.copy()
    logpoint_completed_user1['id'] = 'b-1650000006'
    logpoint_completed_user1['userEmail'] = 'user1@foo.com'

    logpoint_completed_user2 = LOGPOINT_COMPLETED.copy()
    logpoint_completed_user2['id'] = 'b-1650000007'
    logpoint_completed_user2['userEmail'] = 'user2@foo.com'

    # To note, logpoints are included, this ensures only snapshots are returned
    # by the get_snapshots call.
    all_active_breakpoints = [
        snapshot_active_user1,
        snapshot_active_user2,
        logpoint_active_user1,
        logpoint_active_user2,
    ]

    all_final_breakpoints = [
        snapshot_completed_user1,
        snapshot_completed_user2,
        logpoint_completed_user1,
        logpoint_completed_user2,
    ]

    # Queries for a list of breakpoints from the Firebase Rest interface will
    # come back in dict form. So we convert array of breakpoints to this form.
    def convert_breakpoints(breakpoints):
      return {bp['id']: bp for bp in breakpoints}

    all_active_breakpoints = convert_breakpoints(all_active_breakpoints)
    all_final_breakpoints = convert_breakpoints(all_final_breakpoints)

    testcases = [
        # (Test name, include_inactive, user_email, active bps query,
        #  final bps query, expected snapshots, expected get calls)
        (
            'Active Only - Individual User',
            False, # include_inactive
            'user1@foo.com',
            all_active_breakpoints,
            None, # Doesn't matter, final path should not be queried
            [snapshot_active_user1],
            [call(self.schema.get_path_breakpoints_active('123'))]
        ),
        (
            'Final Included - Individual User',
            True, # include_inactive
            'user1@foo.com',
            all_active_breakpoints,
            all_final_breakpoints,
            [snapshot_active_user1, snapshot_completed_user1],
            [call(self.schema.get_path_breakpoints_active('123')),
             call(self.schema.get_path_breakpoints_final('123'))]
        ),
        (
            'Active Only - All Users',
            False, # include_inactive
            None, # user email of None means don't filter on email.
            all_active_breakpoints,
            None, # Doesn't matter, final path should not be queried
            [snapshot_active_user1, snapshot_active_user2],
            [call(self.schema.get_path_breakpoints_active('123'))]
        ),
        (
            'Final Included - Individual User',
            True, # include_inactive
            None, # user email of None means don't filter on email.
            all_active_breakpoints,
            all_final_breakpoints,
            [snapshot_active_user1, snapshot_active_user2,
             snapshot_completed_user1, snapshot_completed_user2],
            [call(self.schema.get_path_breakpoints_active('123')),
             call(self.schema.get_path_breakpoints_final('123'))]
        ),
        (
            'User Not Found',
            False, # include_inactive
            'user-not-found@foo.com',
            all_active_breakpoints,
            None, # Doesn't matter, final path should not be queried
            [],
            [call(self.schema.get_path_breakpoints_active('123'))]
        ),
        (
            # To note in practise this scenario may not be possible. If a
            # debuggee has no active breakpoints, e.g. the last one was deleted,
            # the path would cease to exist and so queries to it would instead
            # return None, which is its own test scenario one. That said the
            # code should be able to handle an empty response and so we check
            # for it.
            'Empty responses on path queries',
            True, # include_inactive
            'user1@foo.com',
            {}, # No active breakpoints at all.
            {}, # No final breakpoints at all.
            [], # Expected to get empty array from get_snapshots()
            [call(self.schema.get_path_breakpoints_active('123')),
             call(self.schema.get_path_breakpoints_final('123'))]
        ),
        (
            # This scenario happens if the debuggee has no breakpoints and the
            # path doesn't actually exist. None will be returned for the get
            # query on the path in this case.
            'None responses on path queries',
            True, # include_inactive
            'user1@foo.com',
            None, # No active breakpoints at all.
            None, # No final breakpoints at all.
            [], # Expected to get empty array from get_snapshots()
            [call(self.schema.get_path_breakpoints_active('123')),
             call(self.schema.get_path_breakpoints_final('123'))]
        ),
    ] # yapf: disable (Subjectively, more readable hand formatted)

    for (test_name, include_inactive, user_email, active_breakpoints,
         final_breakpoints, expected_snapshots, expected_calls) in testcases:
      with self.subTest(test_name):
        # The first call to get will be for the active, path, and the second (if
        # it occurs) will be for the final path. Set the array order based on
        # this.
        self.firebase_rtdb_service_mock.get = MagicMock(
            side_effect=[active_breakpoints, final_breakpoints])

        obtained_snapshots = self.debugger_rtdb_service.get_snapshots(
            '123', include_inactive, user_email)

        self.assertEqual(expected_snapshots, obtained_snapshots)
        self.assertEqual(expected_calls,
                         self.firebase_rtdb_service_mock.get.mock_calls)

  def test_get_snapshots_normalizes_bp(self):
    """This test focuses solely on ensuring the snapshots gets normalized.

    The snapshots returned by get_snapshots() should have the
    breakpoint_utils.normalize_breakpoint function applied to them.  This
    ensures all expected fields are set and calling code can assume they exist.
    """

    bp = SNAPSHOT_ACTIVE.copy()

    # If we don't populate the action, the normalize_breakpoint call will
    # default it to 'CAPTURE' and populate it.
    # 'action': 'CAPTURE',
    del bp['action']
    self.assertNotIn('action', bp)

    get_response = {bp['id']: bp}
    self.firebase_rtdb_service_mock.get = MagicMock(return_value=get_response)

    obtained_snapshots = self.debugger_rtdb_service.get_snapshots(
        '123', include_inactive=False)

    # This field will have been set by the call to normalize_breakpoint which
    # ensures it was called as expected.
    self.assertIn('action', obtained_snapshots[0])
    self.assertEqual('CAPTURE', obtained_snapshots[0]['action'])

  def test_set_breakpoint_works_as_expected(self):
    bp = {
        'action': 'CAPTURE',
        'createTimeUnixMsec': {
            '.sv': 'timestamp'
        },
        'id': 'b-1650000000',
        'location': {
            'line': 26,
            'path': 'index.js'
        },
        'userEmail': 'user@foo.com',
        # We simply populate this with something, since set_breakpoint calls
        # normalize_breakpoint and if this is not set, it will populate this
        # field. For this purposes of this test, we don't want
        # normalize_breakpoint to modifiy the breakpoint.
        'createTime': 'placeholder-set'
    }

    expected_path = self.schema.get_path_breakpoints_active_for_id(
        '123', bp['id'])

    set_response = bp.copy()
    # Here we just mimic what happens, when the RTDB gets the magic {'.sv':
    # 'timestamp'} it will substitue in the time and return the data written. We
    # want to ensure the function will return the data the RTDB sent back.
    set_response['createTimeUnixMsec'] = 1649962215426

    self.firebase_rtdb_service_mock.set = MagicMock(return_value=set_response)

    obtained_breakpoint = self.debugger_rtdb_service.set_breakpoint('123', bp)

    self.assertEqual(obtained_breakpoint, set_response)
    self.firebase_rtdb_service_mock.set.assert_called_once_with(
        expected_path, data=bp)

  def test_set_breakpoint_normalizes_bp(self):
    """This test focuses solely on ensuring the breakpoint gets normalized.

    The set_breakpoint function should call normalize_breakpoint on the
    breakpoint returned by the RTDB. This ensures all expected fields are set
    and calling code can assume they exist.
    """

    bp = {
        'action': 'CAPTURE',
        'createTimeUnixMsec': {
            '.sv': 'timestamp'
        },
        'id': 'b-1650000000',
        'location': {
            'line': 26,
            'path': 'index.js'
        },
        'userEmail': 'user@foo.com',
    }

    set_response = bp.copy()

    # Here we just mimic what happens, when the RTDB gets the magic {'.sv':
    # 'timestamp'} it will substitue in the time and return the data written. We
    # want to ensure the function will return the data the RTDB sent back.
    set_response['createTimeUnixMsec'] = 1649962215426

    self.firebase_rtdb_service_mock.set = MagicMock(return_value=set_response)

    obtained_breakpoint = self.debugger_rtdb_service.set_breakpoint('123', bp)

    # This field will have been set by the call to normalize_breakpoint which
    # ensures set_breakpoint normalizes the breakpoint.
    self.assertIn('createTime', obtained_breakpoint)
