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
"""This module provides the SnapshotParser utility class.

The SnapshotParser utility class provides support to the get_snapshot command
for parsing and printing snapshot data.
"""

from snapshot_dbg_cli import breakpoint_utils
from snapshot_dbg_cli.status_message import StatusMessage

MSG_VARIABLE_CYCLE = (
    'DBG_MSG: Cycle, refers to same instance as ancestor field '
    "'{ancestor_name}'.")

MSG_VARIABLE_CYCLE_ANCESTOR_UNKNOWN = (
    'DBG_MSG: Cycle, refers to same instance as an '
    'ancestor field.')

MSG_MAX_EXPANSION_LEVEL_HIT = (
    'DBG_MSG: Max expansion level of {0} hit. Specify'
    ' a larger value for --max-level to see more.')


class SnapshotParser:
  """This is a utility class that parses snapshot data.

  This class provides support to the get_snapshot command for parsing snapshot
  data so it can be presented to the user.

  Attributes:
    stack_frames: The stack_frames field from the snapshot message.
    status_message: An instance of StatusMessage, which is the status message
      for the snapshot, if one was present. If there was no status message the
      parsed_message field of the StatusMessage will be None.
  """

  def __init__(self, snapshot, max_expansion_level):
    self._variable_table = snapshot.get('variableTable', [])
    self._evaluated_expressions = snapshot.get('evaluatedExpressions', [])
    self.stack_frames = snapshot.get('stackFrames', [])
    self._max_expansion_level = max_expansion_level
    self.status_message = StatusMessage(snapshot)

  def parse_call_stack(self):
    call_stack = []

    for f in self.stack_frames:
      function = f['function'] if 'function' in f else 'unknown'
      location = breakpoint_utils.transform_location_to_file_line(
          f['location']) if 'location' in f else 'unknown'
      if location is None:
        location = 'unknown'

      call_stack.append([function, location])

    return call_stack

  def parse_expressions(self):
    return self._resolve_variables(self._evaluated_expressions)

  def parse_locals(self, stack_frame_index):
    local_variables = []

    if stack_frame_index < len(self.stack_frames):
      stack_frame = self.stack_frames[stack_frame_index]
      for p in ['arguments', 'locals']:
        local_variables.extend(stack_frame.get(p, []))

    return self._resolve_variables(local_variables)

  def _resolve_variables(self, variables):
    parsed_variables = []

    for v in variables:
      name, value, message = self._resolve_variable(v, 0, {})
      parsed_variables.append({name: value})
      if message is not None:
        parsed_variables.append({f'{name} - DBG_MSG': message})

    return parsed_variables

  def _resolve_variable(self, variable, current_level, parents):
    var_table_index = variable.get('varTableIndex', None)

    if current_level > self._max_expansion_level:
      name = variable.get('name', '')
      return name, MSG_MAX_EXPANSION_LEVEL_HIT.format(
          self._max_expansion_level), None

    if var_table_index is not None:
      if var_table_index in parents:
        ancestor_name = parents[var_table_index]
        value = MSG_VARIABLE_CYCLE.format(
            ancestor_name=parents[var_table_index]
        ) if ancestor_name else MSG_VARIABLE_CYCLE_ANCESTOR_UNKNOWN
        return variable.get('name', ''), value, None
      else:
        parents[var_table_index] = variable.get('name', '')
        table_var = self._variable_table[var_table_index]
        if table_var is not None:
          variable = {**variable, **table_var}

    members = variable.get('members', [])
    name = self.get_variable_name_and_type(variable, members)
    value = '' if var_table_index is None else None
    message = StatusMessage(variable).parsed_message

    if members:
      value = {}
      for m in members:
        m_name, m_value, m_message = self._resolve_variable(
            m, current_level + 1, parents)
        value[m_name] = m_value
        if m_message is not None:
          value[f'{m_name} - DBG_MSG'] = m_message
    else:
      if 'value' in variable:
        value = variable['value']

    if var_table_index is not None:
      del parents[var_table_index]

    return name, value, message

  def get_variable_name_and_type(self, variable, members):
    name_and_type = variable.get('name', '')

    if 'type' in variable:
      name_and_type += f" ({variable['type']})"
    elif 'value' in variable and members:
      # The Node.js agent seems to include the type as 'value'
      name_and_type += f" ({variable['value']})"

    return name_and_type
