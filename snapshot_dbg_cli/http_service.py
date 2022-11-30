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

from snapshot_dbg_cli.exceptions import SilentlyExitError

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

DEFAULT_MAX_RETRIES = 4
DEFAULT_TIMEOUT_SEC = 10


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
  the needs of the CLI for making HTTP requests to the Google and Firebase REST
  APIs.
  """

  def __init__(self, project_id, access_token, user_output):
    """Initializes the HttpService instance.

    Args:
      project_id: (string|None) The Google Cloud project ID the requests are
        for.  This value will be used for the X-Goog-User-Project header when
        the include_project_header flag is true in send and build request calls.
        This value can safely be set to None if the project header does not need
        to be set.
      access_token: (string|None) The access token to use for all requests. If
        this value is None, it will not be included in the request header.
      user_output: UserOutput instance to use for emitting user output.
    """
    self._project_id = project_id
    self._access_token = access_token
    self._user_output = user_output

  def send_request(self,
                   method,
                   url,
                   parameters=None,
                   data=None,
                   include_project_header=False,
                   max_retries=DEFAULT_MAX_RETRIES,
                   extra_retry_codes=None,
                   handle_http_error=True,
                   timeout_sec=DEFAULT_TIMEOUT_SEC):
    """ Sends an HTTP request based on the passed in arguments.

    On success, the json decoded body from the HTTP response will be returned,
    otherwise an error is raised. By default the method will suppress HTTPErrors
    and simply raise SilentlyExitError. To instead let it propagate the
    HTTPError out set handle_http_error to False.

    Args:
      method: The HTTP method for the request, e.g. 'GET', 'PUT' etc.
      url: The URL for the request.
      parameters: A list of url parameters to add to the URL. e.g.
        ['user=foo', 'databaseId=db1-cdbg']. This field is optioal, by default
        none are added.
      data: This is the body to use for the request. The format is a data
        representation that can be converted to a json string representation via
        json.dumps(). This field is optional, by default no body is included.
      include_project_header: Boolean flag, that when true will add the
        'X-Goog-User-Project' header to the request. This field is optional,
        by default this header is not included.
      max_retries: How many times to retry the request in case of failure. By
        default it will attempt retries, so for cases where a retry is not
        safe, the caller should set the value to 0.
      extra_retry_codes: A list of extra HTTP error codes that will be retried
        if the request fails in addition to the default error codes that are
        retried.
      handle_http_errror: Flag to tell the method if it should handle HTTPError
        exceptions on its own. Callers that want to receive the error, in order
        to check the error code or message, should set this flag to False. It
        defaults to True.
      timeout_sec: The timeout in seconds to use for each http request.

    Returns:
      The json decoded body of the HTTP response, meaning this value will be a
      python dict, array, string etc depending on the returned json.

    Raises:
      HTTPError: If the caller set handle_http_error to False and an HTTPError
        occurs.
      SilentlyExitError: If error occurs with the HTTP call, unless it's an
        HTTPError and handle_http_error was set to False.
    """
    request = self.build_request(
        method=method,
        url=url,
        parameters=parameters,
        data=data,
        include_project_header=include_project_header)

    return self.send(
        request,
        max_retries=max_retries,
        extra_retry_codes=extra_retry_codes,
        handle_http_error=handle_http_error,
        timeout_sec=timeout_sec)

  def build_request(self,
                    method,
                    url,
                    parameters=None,
                    data=None,
                    include_project_header=False):
    """ Creates a urllib.request.Request instance.

    Args:
      method: The HTTP method for the request, e.g. 'GET', 'PUT' etc.
      url: The URL for the request.
      parameters: A list of url parameters to add to the URL. e.g.
        ['user=foo', 'databaseId=db1-cdbg']. This field is optioal, by default
        none are added.
      data: This is the body to use for the request. The format is a data
        representation that can be converted to a json string representation via
        json.dumps(). This field is optional, by default no body is included.
      include_project_header: Boolean flag, that when true will add the
        'X-Goog-User-Project' header to the request. This field is optional,
        by default this header is not included.

    Returns:
      The appropriately configured urllib.request.Request instance.
    """

    if parameters is not None:
      first_param = True
      for p in parameters:
        url += f"{'?' if first_param else '&'}{p}"
        first_param = False

    headers = {}

    if self._access_token is not None:
      headers["Authorization"] = f"Bearer {self._access_token}"

    if include_project_header:
      headers["X-Goog-User-Project"] = self._project_id

    data_json = None

    if data is not None:
      data_json = json.dumps(data).encode("utf-8")
      headers["Content-Type"] = "application/json"

    request = Request(url, data=data_json, headers=headers, method=method)

    return request

  def send(self,
           request,
           max_retries=DEFAULT_MAX_RETRIES,
           extra_retry_codes=None,
           handle_http_error=True,
           timeout_sec=DEFAULT_TIMEOUT_SEC):
    """ Sends an HTTP request using the passed in request.

    On success, the json decoded body from the HTTP response will be returned,
    otherwise an error is raised. By default the method will suppress HTTPErrors
    and simply raise SilentlyExitError. To instead let it propagate the
    HTTPError out set handle_http_error to False.

    Args:
      request: The urllib.request.Request instance to use for the call to
        urlopen. Callers can use the build_request() method of this class to
        obtain an appropriatly configured instance.
      max_retries: How many times to retry the request in case of failure. By
        default it will attempt retries, so for cases where a retry is not
        safe, the caller should set the value to 0.
      extra_retry_codes: A list of extra HTTP error codes that will be retried
        if the request fails in addition to the default error codes that are
        retried.
      handle_http_errror: Flag to tell the method if it should handle HTTPError
        exceptions on its own. Callers that want to receive the error, in order
        to check the error code or message, should set this flag to False. It
        defaults to True.
      timeout_sec: The timeout in seconds to use for each http request.

    Returns:
      The json decoded body of the HTTP response, meaning this value will be a
      python dict, array, string etc depending on the returned json.

    Raises:
      HTTPError: If the caller set handle_http_error to False and an HTTPError
        occurs.
      SilentlyExitError: If error occurs with the HTTP call, unless it's an
        HTTPError and handle_http_error was set to False.
    """
    retry_count = 0

    # Note, we aren't worried about duplicate codes in retry_codes, no need to
    # filter or anything.
    retry_codes = RETRIABLE_HTTP_CODES if extra_retry_codes is None else [
        *RETRIABLE_HTTP_CODES, *extra_retry_codes
    ]

    while True:
      send_msg = SENDING_REST_MSG.format(
          attempt_count=(retry_count + 1),
          method=request.method,
          url=request.full_url,
          data=request.data,
          headers=get_scrubbed_headers(request.headers))

      self._user_output.debug(send_msg)

      try:
        with urlopen(request, timeout=timeout_sec) as response:
          content_type = response.headers.get_content_type()
          charset = response.headers.get_content_charset("utf-8")
          body_parsed = response.read().decode(charset)

          if content_type == "application/json":
            body_parsed = json.loads(body_parsed)
        break
      except HTTPError as err:
        if retry_count == max_retries or err.code not in retry_codes:
          if not handle_http_error:
            # This means the caller wants the HTTPError and will handle it on
            # their own.
            raise

          print_http_error(self._user_output, request, err)
          raise SilentlyExitError from err
        else:
          print_http_error(
              self._user_output, request, err, is_debug_message=True)
      except URLError as error:
        if retry_count == max_retries:
          self._user_output.error("ERROR:", error.reason)
          raise SilentlyExitError from error
        else:
          self._user_output.debug("ERROR:", error.reason)
      except TimeoutError as error:
        if retry_count == max_retries:
          self._user_output.error("ERROR The REST request timed out")
          raise SilentlyExitError from error
        else:
          self._user_output.debug("ERROR The REST request timed out")
      except json.JSONDecodeError as error:
        self._user_output.error(
            "ERROR Failure occured parsing the response as json", error)
        raise SilentlyExitError from error

      sleep_secs = 2**(retry_count)
      self._user_output.debug(
          f"Sleeping for {sleep_secs} seconds before retrying")
      time.sleep(sleep_secs)
      retry_count += 1

    self._user_output.debug("Successful REST response: ", body_parsed)
    return body_parsed
