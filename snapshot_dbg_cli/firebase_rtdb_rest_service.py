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
"""Service for making Firebase RTDB REST requests.

This service is for making read/write requests to a Firebase RTDB instance
using the REST interface, which is documented at
https://firebase.google.com/docs/reference/rest/database.
"""

FULL_REQUEST_URL = "{database_url}/{db_path}.json"


class FirebaseRtdbRestService:
  """This class implements a service for making Firebase RTDB REST requests.

  This service is for making read/write requests to a Firebase RTDB instance
  using the REST interface which is documented at
  https://firebase.google.com/docs/reference/rest/database.
  """

  def __init__(self, http_service, database_url, user_output):
    self._http_service = http_service
    self._database_url = database_url
    self._user_output = user_output

  def get(self, db_path, shallow=None, extra_retry_codes=None):
    """Gets the value at the specified path.

    Args:
      db_path: The database path to retrieve the value on.
      shallow: If specified will just get the values at the top level of the
        node, nothing further down.
      extra_retry_codes: A list of extra HTTP error codes that will be retried
        if the request fails in addition to the default error codes that are
        retried.

    Returns:
      The value at the specified path if it exists, None otherwise.
    """
    url = self.build_rtdb_url(db_path)
    parameters = ["shallow=true"] if shallow else []
    return self._http_service.send_request(
        "GET", url, extra_retry_codes=extra_retry_codes, parameters=parameters)

  def set(self, db_path, data):
    url = self.build_rtdb_url(db_path)
    return self._http_service.send_request("PUT", url, data=data, max_retries=0)

  def delete(self, db_path):
    url = self.build_rtdb_url(db_path)

    # From
    # https://firebase.google.com/docs/reference/rest/database#section-delete
    #
    # A successful DELETE request is indicated by a 200 OK HTTP status code with
    # a response containing JSON null.
    # Based on experimentation, even if the node didn't exist, this will be the
    # response. It seems the response is success if after the call the specified
    # path does not exist, as long as the database the call referenced did
    # exist.
    return self._http_service.send_request("DELETE", url, max_retries=5)

  def build_rtdb_url(self, db_path):
    return FULL_REQUEST_URL.format(
        database_url=self._database_url, db_path=db_path)
