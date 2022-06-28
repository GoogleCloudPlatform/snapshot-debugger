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
""" Unit test file for the snapshot_parser module.
"""

import unittest

from snapshot_dbg_cli.snapshot_parser import SnapshotParser


class SnapshotParserTests(unittest.TestCase):
  """ Contains the unit tests for the snapshot_parser module.
  """

  def test_parse_call_stack_works_as_expected(self):
    snapshot =  {
      'action': 'CAPTURE',
      'createTimeUnixMsec': 1649962215426,
      'condition': 'a == 3',
      'finalTimeUnixMsec': 1649962230637,
      'id': 'b-1649962215',
      'isFinalState': True,
      'userEmail': 'foo@bar.com',
      'location': {'line': 26, 'path': 'index.js'},
      'stackFrames': [
        {
          'function': 'func0',
          'location': {'line': 26, 'path': 'index.js'}
        },
        {
          'location': {'line': 30, 'path': 'index.js'}
        },
        {
          'function': 'func2',
        },
        {
          'function': 'func3',
          'location': {'path': 'index.js'}
        },
        {
          'function': 'func4',
          'location': {'line': 30}
        },
        {
          'function': 'func5',
          'location': {'line': 40, 'path': 'index.js'}
        },
      ],
    } # yapf: disable (Subjectively, more readable hand formatted)

    expected_parsed = [
        ['func0', 'index.js:26'],
        ['unknown', 'index.js:30'],
        ['func2', 'unknown'],
        ['func3', 'unknown'],
        ['func4', 'unknown'],
        ['func5', 'index.js:40'],
    ]

    parsed = SnapshotParser(snapshot, max_expansion_level=10).parse_call_stack()
    self.assertEqual(expected_parsed, parsed)

  def test_parse_call_stack_works_as_expected_with_no_stack_frames(self):
    snapshot =  {
      'action': 'CAPTURE',
      'createTimeUnixMsec': 1649962215426,
      'condition': 'a == 3',
      'finalTimeUnixMsec': 1649962230637,
      'id': 'b-1649962215',
      'isFinalState': True,
      'userEmail': 'foo@bar.com',
      'location': {'line': 26, 'path': 'index.js'},
    } # yapf: disable (Subjectively, more readable hand formatted)

    parsed = SnapshotParser(snapshot, max_expansion_level=10).parse_call_stack()
    self.assertEqual([], parsed)

  def test_parse_expressions_works_as_expected_with_expressions(self):
    snapshot =  {
      'action': 'CAPTURE',
      'createTimeUnixMsec': 1649962215426,
      'condition': 'a == 3',
      'finalTimeUnixMsec': 1649962230637,
      'id': 'b-1649962215',
      'isFinalState': True,
      'userEmail': 'foo@bar.com',
      'location': {'line': 26, 'path': 'index.js'},
      'expressions': ['a', 'b', 'a is None'],
      'evaluatedExpressions': [
        {'name': 'a', 'varTableIndex': 0},
        {'name': 'b', 'varTableIndex': 1},
        {'name': 'a is None', 'value': False}
      ],
      'variableTable': [
        {
          'members': [
             {'name': 'c', 'varTableIndex': 1},
             {'name': 'd',  'value': 99}
          ]
        },
        {
          'members': [
             {'name': 'e',  'value': 100}
          ]
        },
      ],
    } # yapf: disable (Subjectively, more readable hand formatted)

    expected_parsed = [
        {
            'a': {
                'c': {
                    'e': 100
                },
                'd': 99
            },
        },
        {
            'b': {
                'e': 100
            }
        },
        {
            'a is None': False
        },
    ]

    parsed = SnapshotParser(
        snapshot, max_expansion_level=10).parse_expressions()
    self.assertEqual(expected_parsed, parsed)

  def test_parse_expressions_works_as_expected_with_no_expressions(self):
    snapshot =  {
      'action': 'CAPTURE',
      'createTimeUnixMsec': 1649962215426,
      'condition': 'a == 3',
      'finalTimeUnixMsec': 1649962230637,
      'id': 'b-1649962215',
      'isFinalState': True,
      'userEmail': 'foo@bar.com',
      'location': {'line': 26, 'path': 'index.js'},
    } # yapf: disable (Subjectively, more readable hand formatted)

    parsed = SnapshotParser(
        snapshot, max_expansion_level=10).parse_expressions()
    self.assertEqual([], parsed)

  def test_parse_locals_works_as_expected(self):
    snapshot =  {
      'action': 'CAPTURE',
      'createTimeUnixMsec': 1649962215426,
      'condition': 'a == 3',
      'finalTimeUnixMsec': 1649962230637,
      'id': 'b-1649962215',
      'isFinalState': True,
      'userEmail': 'foo@bar.com',
      'location': {'line': 26, 'path': 'index.js'},
      'expressions': ['a', 'b', 'a is None'],
      'stackFrames': [
        {
          'function': 'func0',
          'locals': [
            {'name': 'a', 'value': 'aaa'},
            {'name': 'b', 'varTableIndex': 0}
          ],
          'location': {'line': 26, 'path': 'index.js'}
        },
        {
          'function': 'func1',
          'locals': [
            {'name': 'c', 'varTableIndex': 1}
          ],
          'location': {'line': 30, 'path': 'index.js'}
        },
        {
          'function': 'func2',
          'locals': [],
          'location': {'line': 35, 'path': 'index.js'}
        },
        {
          'function': 'func3',
          'location': {'line': 40, 'path': 'index.js'}
        },
      ],
      'variableTable': [
        {
          'members': [
             {'name': 'd', 'varTableIndex': 1},
             {'name': 'e',  'value': 99}
          ]
        },
        {
          'members': [
             {'name': 'f',  'value': 100}
          ]
        },
      ],
    } # yapf: disable (Subjectively, more readable hand formatted)

    expected_parsed_frame0 = [
        {
            'a': 'aaa'
        },
        {
            'b': {
                'd': {
                    'f': 100
                },
                'e': 99
            },
        },
    ]

    expected_parsed_frame1 = [
        {
            'c': {
                'f': 100
            },
        },
    ]

    expected_parsed_frame2 = []
    expected_parsed_frame3 = []
    expected_parsed_frame100 = []  # Out of range check

    parsed_frame0 = SnapshotParser(
        snapshot, max_expansion_level=10).parse_locals(stack_frame_index=0)
    parsed_frame1 = SnapshotParser(
        snapshot, max_expansion_level=10).parse_locals(stack_frame_index=1)
    parsed_frame2 = SnapshotParser(
        snapshot, max_expansion_level=10).parse_locals(stack_frame_index=2)
    parsed_frame3 = SnapshotParser(
        snapshot, max_expansion_level=10).parse_locals(stack_frame_index=3)
    parsed_frame100 = SnapshotParser(
        snapshot, max_expansion_level=10).parse_locals(stack_frame_index=100)

    self.assertEqual(expected_parsed_frame0, parsed_frame0)
    self.assertEqual(expected_parsed_frame1, parsed_frame1)
    self.assertEqual(expected_parsed_frame2, parsed_frame2)
    self.assertEqual(expected_parsed_frame3, parsed_frame3)
    self.assertEqual(expected_parsed_frame100, parsed_frame100)

  def test_parse_locals_works_as_expected_with_no_stack_frames(self):
    snapshot =  {
      'action': 'CAPTURE',
      'createTimeUnixMsec': 1649962215426,
      'condition': 'a == 3',
      'finalTimeUnixMsec': 1649962230637,
      'id': 'b-1649962215',
      'isFinalState': True,
      'userEmail': 'foo@bar.com',
      'location': {'line': 26, 'path': 'index.js'},
    } # yapf: disable (Subjectively, more readable hand formatted)

    parsed = SnapshotParser(snapshot, max_expansion_level=10).parse_locals(0)
    self.assertEqual([], parsed)

  def test_handles_cycle(self):
    snapshot =  {
      'action': 'CAPTURE',
      'createTimeUnixMsec': 1649962215426,
      'condition': 'a == 3',
      'finalTimeUnixMsec': 1649962230637,
      'id': 'b-1649962215',
      'isFinalState': True,
      'userEmail': 'foo@bar.com',
      'location': {'line': 26, 'path': 'index.js'},
      'stackFrames': [
        {
          'function': 'func1',
          'locals': [
            {'name': 'root', 'varTableIndex': 0},
          ],
          'location': {'line': 30, 'path': 'index.js' }
        }
      ],
      'variableTable': [
        {
          'members': [
             {'name': 'a0', 'varTableIndex': 1},
             {'name': 'b0',  'value': 0}
          ]
        },
        {
          'members': [
             {'name': 'a1', 'varTableIndex': 2},
             {'name': 'b1',  'value': 1}
          ]
        },
        {
          'members': [
            {'name': 'a2', 'varTableIndex': 0},
            {'name': 'b2',  'value': 2}
          ]
        }
      ],
    } # yapf: disable (Subjectively, more readable hand formatted)

    expected_parsed = [{
        'root': {
            'a0': {
                'a1': {
                    'a2': ('DBG_MSG: Cycle, refers to same instance as '
                           "ancestor field 'root'."),
                    'b2': 2
                },
                'b1': 1
            },
            'b0': 0
        }
    }]

    parsed = SnapshotParser(
        snapshot, max_expansion_level=10).parse_locals(stack_frame_index=0)

    self.assertEqual(expected_parsed, parsed)

  def test_handles_truncation(self):
    snapshot =  {
      'action': 'CAPTURE',
      'createTimeUnixMsec': 1649962215426,
      'condition': 'a == 3',
      'finalTimeUnixMsec': 1649962230637,
      'id': 'b-1649962215',
      'isFinalState': True,
      'userEmail': 'foo@bar.com',
      'location': {'line': 26, 'path': 'index.js'},
      'stackFrames': [
        {
          'function': 'func1',
          'locals': [
            {'name': 'root', 'varTableIndex': 0},
          ],
          'location': {'line': 30, 'path': 'index.js' }
        }
      ],
      'variableTable': [
        {
          'members': [
             {'name': 'a0', 'varTableIndex': 1},
             {'name': 'b0',  'value': 0}
          ]
        },
        {
          'members': [
             {'name': 'a1', 'varTableIndex': 2},
             {'name': 'b1',  'value': 1}
          ]
        },
        {
          'members': [
            {'name': 'a2', 'varTableIndex': 3},
            {'name': 'b2',  'value': 2}
          ]
        },
        {
          'members': [
            {'name': 'a3', 'varTableIndex': 4},
            {'name': 'b3',  'value': 3}
          ]
        },
        {
          'members': [
            {'name': 'b4',  'value': 4}
          ]
        }
      ],
    } # yapf: disable (Subjectively, more readable hand formatted)

    expected_not_truncated = [{
        'root': {
            'a0': {
                'a1': {
                    'a2': {
                        'a3': {
                            'b4': 4
                        },
                        'b3': 3
                    },
                    'b2': 2
                },
                'b1': 1
            },
            'b0': 0
        }
    }]

    expected_truncated_level4 = [{
        'root': {
            'a0': {
                'a1': {
                    'a2': {
                        'a3': {
                            'b4': ('DBG_MSG: Max expansion level of 4 hit. '
                                   'Specify a larger value for --max-level to '
                                   'see more.')
                        },
                        'b3': 3
                    },
                    'b2': 2
                },
                'b1': 1
            },
            'b0': 0
        }
    }]

    expected_truncated_level3 = [{
        'root': {
            'a0': {
                'a1': {
                    'a2': {
                        'a3': ('DBG_MSG: Max expansion level of 3 hit. '
                               'Specify a larger value for --max-level to see '
                               'more.'),
                        'b3': ('DBG_MSG: Max expansion level of 3 hit. '
                               'Specify a larger value for --max-level to see '
                               'more.'),
                    },
                    'b2': 2
                },
                'b1': 1
            },
            'b0': 0
        }
    }]

    parsed_level10 = SnapshotParser(
        snapshot, max_expansion_level=10).parse_locals(stack_frame_index=0)

    parsed_level4 = SnapshotParser(
        snapshot, max_expansion_level=4).parse_locals(stack_frame_index=0)

    parsed_level3 = SnapshotParser(
        snapshot, max_expansion_level=3).parse_locals(stack_frame_index=0)

    self.assertEqual(expected_not_truncated, parsed_level10)
    self.assertEqual(expected_truncated_level4, parsed_level4)
    self.assertEqual(expected_truncated_level3, parsed_level3)

  def test_handles_type_information(self):
    """Verifies the parsed variables have expected type information.

    The type information is expected to be included with the variable name in
    the parsed output, e.g. 'var1 (Var1Type)'.
    """
    snapshot =  {
      'action': 'CAPTURE',
      'createTimeUnixMsec': 1649962215426,
      'finalTimeUnixMsec': 1649962230637,
      'id': 'b-1649962215',
      'isFinalState': True,
      'location': {'line': 26, 'path': 'index.js'},
      'stackFrames': [
        {
          'function': 'func0',
          'locals': [
              {'name': 'a', 'value': '3', 'type': 'string'},
              {'name': 'b', 'varTableIndex': 0},
              {'name': 'c', 'varTableIndex': 1},
          ],
          'location': {'line': 26, 'path': 'index.js'}
        },
      ],
      'variableTable': [
        {
          'type': 'FooType',
          'members': [
             {'name': 'd', 'value': 1, 'type': 'int'},
          ]
        },
        {
          # Special case, the Node.js agents includes the 'type' as value
          'value': 'FooTypeInValueField',
          'members': [
            {'name': 'e', 'value': False, 'type': 'bool'},
          ]
        }
      ],
      'userEmail': 'foo@bar.com',
    } # yapf: disable (Subjectively, more readable hand formatted)

    expected_parsed = [
        {
            'a (string)': '3'
        },
        {
            'b (FooType)': {
                'd (int)': 1
            }
        },
        {
            'c (FooTypeInValueField)': {
                'e (bool)': False
            }
        },
    ]

    parsed = SnapshotParser(
        snapshot, max_expansion_level=10).parse_locals(stack_frame_index=0)
    self.assertEqual(expected_parsed, parsed)

  def test_parsed_variable_has_message(self):
    """Verifies the parsed variables have included variable messages.

    In some cases, the agent will include a status message with a captured
    variable. These messages help provide the user with information, such saying
    a captured string was truncated, and how to capture the complete
    information. This information is provided to the user by adding an extra
    variable to the parsed data, with a name of 'var_name DBG_MSG', and it is
    mapped to the information string provided by the agent. This way when the
    data is displayed the user will notice the message.
    """

    # Note, setting this up based on a message out of Node.js
    # agent, though in the real case the confgured value was 100,
    # using 5 here for simplicity.
    msg = ('Only first `config.capture.maxStringLength=5` chars were captured '
           'for string of length 105. Use in an expression to see the full '
           'string.')

    status = {
        'description': {
            'format': msg
        },
        'isError': False,
        'refersTo': 'VARIABLE_VALUE'
    }

    snapshot = {
      'action': 'CAPTURE',
      'createTimeUnixMsec': 1649962215426,
      'finalTimeUnixMsec': 1649962230637,
      'id': 'b-1649962215',
      'isFinalState': True,
      'location': {'line': 26, 'path': 'index.js'},
      'stackFrames': [
        {
          # Note, we include a status message for a top level variable, and
          # nested as a member, the code handles these as two different
          # scenarios.
          'function': 'func0',
          'locals': [
            {'name': 'a', 'value': 'abcde', 'status': status},
            {
              'name': 'b',
              'members': [
                  {'name': 'c', 'value': '12345', 'status': status}
              ]
           },
          ],
        },
      ],
      'userEmail': 'foo@bar.com',
    } # yapf: disable (Subjectively, more readable hand formatted)

    expected_parsed = [{
        'a': 'abcde'
    }, {
        'a - DBG_MSG': msg
    }, {
        'b': {
            'c': '12345',
            'c - DBG_MSG': msg
        }
    }]

    parsed = SnapshotParser(
        snapshot, max_expansion_level=10).parse_locals(stack_frame_index=0)
    self.assertEqual(expected_parsed, parsed)
