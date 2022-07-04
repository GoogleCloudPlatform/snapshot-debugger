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
"""This module provides utilities for formatting text.

The DataFormatter class provides utility functions such as formatting tabular
data and json data.
"""

import json


class DataFormatter:
  """Provides utilities for formatting text.

  The DataFormatter class provides utility functions such as formatting tabular
  data and json data.
  """

  def build_table(self, headers, values):
    """Builds a human friendly string of the data in table form.

    Args:
      headers: Array of strings to be used as the top row of the table,
        representing the column names.
      values: Array of tuples containing one row of output (1 value for each
        column). Each tuple must have the same number of elements, which much
        also match the length of the headers tuple.
    """
    widths = [
        max(len(headers[i]), max((len(v[i])
                                  for v in values), default=0))
        for i in range(len(headers))
    ]

    separator_row = list(map(lambda w: '-' * w, widths))

    rows = []
    rows.append(headers)
    rows.append(separator_row)
    rows += values

    field_buffer = '  '
    table = ''

    for i in range(len(rows)):
      fields = [f'{rows[i][j]:{widths[j]}}' for j in range(len(rows[i]))]
      table += field_buffer.join(fields)
      table += '\n'

    return table

  def to_json_string(self, data, pretty):
    """Transforms the data to a JSON string representation.

    Args:
      data: The data to convert to a JSON string. It is expected to be a Python
        object representation of the data.
      pretty: Boolean flag that when True will be cause the json string to be
        human readable, otherwise it will be in a compact representation.
    """
    if pretty:
      return json.dumps(data, indent=2)
    else:
      return json.dumps(data)
