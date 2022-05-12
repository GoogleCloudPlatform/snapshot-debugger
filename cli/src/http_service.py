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
"""Provides utilities and a service class for making HTTP requests.
"""

import json
import time
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen

from exceptions import SilentlyExitError

REST_ERROR_MSG = """
ERROR the following REST request failed:

  Method:  {method}
  URL:     {url}
  Data:    {data}
  Headers: {headers}
  Error:   {http_error}
  Backend Msg: {error_message}
"""

SENDING_REST_MSG = """
Sending the following REST request (attempt {attempt_count}):
{{
  Method:  {method}
  URL:     {url}
  Data:    {data}
  Headers: {headers}
}}
"""

RETRIABLE_HTTP_CODES = [429, 500, 502, 503, 504]


def get_scrubbed_headers(headers):
  scrubbed_headers = headers.copy()
  # Avoid dumping the access token.
  if "Authorization" in scrubbed_headers:
    scrubbed_headers["Authorization"] = "*******"

  return scrubbed_headers


def print_http_error(user_output,
                     request,
                     http_error,
                     is_debug_message=False,
                     error_message=None):
  if error_message is None:
    error_message = http_error.read().decode()

  log_msg = REST_ERROR_MSG.format(
      method=request.get_method(),
      url=request.get_full_url(),
      data=request.data,
      headers=get_scrubbed_headers(request.headers),
      http_error=http_error,
      error_message=error_message)

  if is_debug_message:
    user_output.debug(log_msg)
  else:
    user_output.error(log_msg)


class HttpService:
  """Service class for making HTTP requests.

  This class is built on top of urllib and provides a convenient interface for
  the needs of the CLI for making HTTP requsts to the Google and Firebase REST
  APIs.
  """

  def __init__(self, project_id, access_token, user_output):
    self.project_id = project_id
    self.access_token = access_token
    self.user_output = user_output

  def send_request(self,
                   method,
                   url,
                   parameters=None,
                   data=None,
                   include_project_header=False,
                   max_retries=3,
                   handle_http_error=True):

    request = self.build_request(
        method=method,
        url=url,
        parameters=parameters,
        data=data,
        include_project_header=include_project_header)

    return self.send(
        request, max_retries=max_retries, handle_http_error=handle_http_error)

  def build_request(self,
                    method,
                    url,
                    parameters=None,
                    data=None,
                    include_project_header=False):

    if parameters is not None:
      first_param = True
      for p in parameters:
        url += f"{'?' if first_param else '&'}{p}"
        first_param = False

    headers = {"Authorization": f"Bearer {self.access_token}"}

    if include_project_header:
      headers["X-Goog-User-Project"] = self.project_id

    data_json = None

    if data is not None:
      data_json = json.dumps(data).encode("utf-8")
      headers["Content-Type"] = "application/json"

    request = Request(url, data=data_json, headers=headers, method=method)

    return request

  def send(self, request, max_retries=4, handle_http_error=True):
    retry_count = 0

    while True:
      send_msg = SENDING_REST_MSG.format(
          attempt_count=(retry_count + 1),
          method=request.method,
          url=request.full_url,
          data=request.data,
          headers=get_scrubbed_headers(request.headers))

      self.user_output.debug(send_msg)

      try:
        with urlopen(request, timeout=10) as response:
          body_parsed = json.loads(response.read().decode("utf-8"))
        break
      except HTTPError as err:
        if retry_count == max_retries or err.code not in RETRIABLE_HTTP_CODES:
          if not handle_http_error:
            # This means the caller wants to the HTTPError and will handle it on
            # their own.
            raise

          print_http_error(self.user_output, request, err)
          raise SilentlyExitError from err
        else:
          print_http_error(
              self.user_output, request, err, is_debug_message=True)
      except URLError as error:
        if retry_count == max_retries:
          self.user_output.error("ERROR:", error.reason)
          raise SilentlyExitError from error
        else:
          self.user_output.debug("ERROR:", error.reason)
      except TimeoutError as error:
        if retry_count == max_retries:
          self.user_output.error("ERROR The REST request timed out")
          raise SilentlyExitError from error
        else:
          self.user_output.debug("ERROR The REST request timed out")
      except json.JSONDecodeError as error:
        self.user_output.error(
            "ERROR Failure occured parsing the response as json", error)
        raise SilentlyExitError from error

      retry_count += 1
      sleep_secs = 2**(retry_count)
      self.user_output.debug(
          f"Sleeping for {sleep_secs} seconds before retrying")
      time.sleep(sleep_secs)

    self.user_output.debug("Successful REST response: ", body_parsed)
    return body_parsed
