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
"""This module provides utilities for formatting and output text.

It provides utility functions such as formatting and outputting tabular data and
formatting and outputting json data.
"""

import json


def print_table(user_output, headers, values):
  widths = [0] * len(headers)

  for i in range(len(headers)):
    widths[i] = max(widths[i], len(headers[i]))
    for j in range(len(values)):
      widths[i] = max(widths[i], len(values[j][i]))

  separator_row = list(map(lambda w: '-' * w, widths))

  rows = []
  rows.append(headers)
  rows.append(separator_row)
  rows += values

  field_buffer = '  '
  table = ''

  for i in range(len(rows)):
    for j in range(len(rows[i])):
      table += f'{rows[i][j]:{widths[j]}}'
      table += field_buffer
    table = table[:-len(field_buffer)]
    table += '\n'

  user_output.normal(table)


def print_json(user_output, json_doc, pretty=False):
  if pretty:
    user_output.normal(json.dumps(json_doc, indent=2))
  else:
    user_output.normal(json.dumps(json_doc))
