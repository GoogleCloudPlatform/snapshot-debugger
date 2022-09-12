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
""" Unit test file for the http_service module.
"""

import json
import unittest
import urllib

from email.message import EmailMessage
from io import BytesIO
from io import StringIO
from snapshot_dbg_cli.exceptions import SilentlyExitError
from snapshot_dbg_cli import data_formatter
from snapshot_dbg_cli.http_service import HttpService
from snapshot_dbg_cli.user_output import UserOutput
from unittest.mock import ANY
from unittest.mock import call
from unittest.mock import MagicMock
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.error import URLError

TEST_PROJECT_ID = 'test-project-id'
TEST_ACCESS_TOKEN = 'test-access-token'

# Seems the Python library will convert all letters other than the first one to
# lower case. So we use these header defines in the tests where appropriate.
GOOG_USER_PROJECT_HEADER = 'X-goog-user-project'
CONTENT_TYPE_HEADER = 'Content-type'

DEFAULT_JSON_CONTENT_TYPE = 'application/json; charset=utf-8'


def build_response_headers(headers):
  response_headers = EmailMessage()
  for k, v in headers.items():
    response_headers.add_header(k, v)

  return response_headers


def build_http_response(body_bytes,
                        content_type=DEFAULT_JSON_CONTENT_TYPE,
                        url=''):
  response_headers = build_response_headers({CONTENT_TYPE_HEADER: content_type})
  resp = urllib.response.addinfourl(BytesIO(body_bytes), response_headers, url)
  resp.code = 200
  resp.msg = 'OK'
  return resp


class HttpServiceBuildRequestTests(unittest.TestCase):
  """ Unit tests for the build_request method of the HttpService class.
  """

  def setUp(self):
    self.http_service_mock = MagicMock(spec=HttpService)

    self.user_output_mock = MagicMock(
        wraps=UserOutput(
            is_debug_enabled=False,
            data_formatter=data_formatter.DataFormatter()))

    self.http_service = HttpService(TEST_PROJECT_ID, TEST_ACCESS_TOKEN,
                                    self.user_output_mock)

  def test_default_invocation_works_as_expected(self):
    service1 = HttpService('project-1', 'token-1', self.user_output_mock)
    service2 = HttpService('project-2', 'token-2', self.user_output_mock)

    req1 = service1.build_request('GET', 'http://foo1.com')
    req2 = service2.build_request('PUT', 'http://foo2.com')

    self.assertEqual('GET', req1.method)
    self.assertEqual('PUT', req2.method)
    self.assertEqual('http://foo1.com', req1.full_url)
    self.assertEqual('http://foo2.com', req2.full_url)

    self.assertIsNone(req1.data)
    self.assertIsNone(req2.data)
    self.assertTrue(req1.has_header('Authorization'))
    self.assertTrue(req2.has_header('Authorization'))
    self.assertEqual('Bearer token-1', req1.get_header('Authorization'))
    self.assertEqual('Bearer token-2', req2.get_header('Authorization'))
    self.assertFalse(req1.has_header(GOOG_USER_PROJECT_HEADER))
    self.assertFalse(req2.has_header(GOOG_USER_PROJECT_HEADER))

  def test_parameters_works_as_expected(self):
    req1 = self.http_service.build_request(
        'GET', 'http://foo.com', parameters=['p1=v1'])
    req2 = self.http_service.build_request(
        'GET', 'http://foo.com', parameters=['p1=v1', 'p2=v2'])
    req3 = self.http_service.build_request(
        'GET', 'http://foo.com', parameters=['p1=v1', 'p2=v2', 'p3=v3'])

    self.assertEqual('http://foo.com?p1=v1', req1.full_url)
    self.assertEqual('http://foo.com?p1=v1&p2=v2', req2.full_url)
    self.assertEqual('http://foo.com?p1=v1&p2=v2&p3=v3', req3.full_url)

  def test_data_works_as_expected(self):
    testcases = [
        ({}, b'{}'),
        ([], b'[]'),
        ('foo', b'"foo"'),
        ({'p1': 'v1', 'p2': {'p3': 'v3'}},b'{"p1": "v1", "p2": {"p3": "v3"}}')
    ] # yapf: disable (Subjectively, more readable hand formatted)

    for data, expected_data in testcases:
      with self.subTest(data):
        req = self.http_service.build_request(
            'GET', 'http://foo.com', data=data)
        self.assertEqual(expected_data, req.data)
        self.assertTrue(req.has_header(CONTENT_TYPE_HEADER))
        self.assertEqual('application/json',
                         req.get_header(CONTENT_TYPE_HEADER))

  def test_include_project_header_works_as_expected(self):
    service1 = HttpService('project-1', 'token-1', self.user_output_mock)
    service2 = HttpService('project-2', 'token-2', self.user_output_mock)

    req_include_false = service1.build_request(
        'GET', 'http://foo.com', include_project_header=False)
    req_include_true_1 = service1.build_request(
        'GET', 'http://foo.com', include_project_header=True)
    req_include_true_2 = service2.build_request(
        'GET', 'http://foo.com', include_project_header=True)

    self.assertFalse(req_include_false.has_header(GOOG_USER_PROJECT_HEADER))
    self.assertTrue(req_include_true_1.has_header(GOOG_USER_PROJECT_HEADER))
    self.assertTrue(req_include_true_2.has_header(GOOG_USER_PROJECT_HEADER))
    self.assertEqual('project-1',
                     req_include_true_1.get_header(GOOG_USER_PROJECT_HEADER))
    self.assertEqual('project-2',
                     req_include_true_2.get_header(GOOG_USER_PROJECT_HEADER))

  def test_access_token_not_included_when_none(self):
    service = HttpService(
        'project-1', access_token=None, user_output=self.user_output_mock)
    request = service.build_request('GET', 'http://foo.com')
    self.assertFalse(request.has_header('Authorization'))


class HttpServiceSendRequestTests(unittest.TestCase):
  """ Unit tests for the send_request() method of the HttpService class.

  To note, there is some similar overlap in these tests as with the
  HttpServiceSendTests below which tests the send() method. Also, the tests here
  are less comprehensive. This is because send_request() makes use of send(), so
  here we simply test enough to ensure send_request() makes use of send()
  correctly. send() then gets more thorough vetting in the HttpServiceSendTests.
  """

  def setUp(self):
    self.user_output_mock = MagicMock(
        wraps=UserOutput(
            is_debug_enabled=False,
            data_formatter=data_formatter.DataFormatter()))

    # A default test instance which tests are free to use, some tests will still
    # create their own custom version as needed.
    self.http_service = HttpService(TEST_PROJECT_ID, TEST_ACCESS_TOKEN,
                                    self.user_output_mock)

    # Setup patching of the 'urllib.request.urlopen' function, which the
    # HttpService class depends on.
    self.urlopen_patcher = patch(
        'snapshot_dbg_cli.http_service.urlopen', autospec=True)
    self.urlopen_mock = self.urlopen_patcher.start()
    self.addCleanup(self.urlopen_patcher.stop)

    self.sleep_patcher = patch('time.sleep', autospec=True)
    self.sleep_mock = self.sleep_patcher.start()
    self.addCleanup(self.sleep_patcher.stop)

    # Install a happy response so by default calling send will succeed. Tests
    # that care will override when needed.
    self.set_urlopen_response(body={})

  def set_urlopen_response(self,
                           body,
                           content_type=DEFAULT_JSON_CONTENT_TYPE,
                           url=''):
    body = json.dumps(body).encode('utf-8')
    self.urlopen_mock.return_value = build_http_response(
        body, content_type, url)

  def set_urlopen_exception(self, exception):
    self.urlopen_mock.side_effect = exception

  def test_builds_expected_request(self):
    self.http_service.send_request(
        method='POST',
        url='http://foo.com',
        parameters=['p1=v1', 'p2=v2'],
        data={'foo': 'bar'},
        include_project_header=True)

    self.urlopen_mock.assert_called_once()
    request = self.urlopen_mock.call_args[0][0]
    self.assertEqual('POST', request.method)
    self.assertEqual('http://foo.com?p1=v1&p2=v2', request.full_url)
    self.assertEqual(b'{"foo": "bar"}', request.data)
    self.assertTrue(request.has_header(GOOG_USER_PROJECT_HEADER))

  def test_handles_http_error_by_default(self):
    http_error = HTTPError('https://foo.com', 404, 'Not Found', {},
                           BytesIO(b'Fake Error Message'))
    self.set_urlopen_exception(http_error)

    # We expect the HttpService to catch the HttpError, print an error, then
    # raise a SilentlyExitError to cause the CLI to exit.
    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.http_service.send_request(
          method='POST', url='http://foo.com', max_retries=0)

    self.assertIn('Fake Error Message', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_allows_http_error_to_progate_when_requested(self):
    http_error = HTTPError('https://foo.com', 404, 'Not Found', {},
                           BytesIO(b'Fake Error Message'))
    self.set_urlopen_exception(http_error)

    # We expect the HttpService to allow the HttpError to propagate
    # when handle_http_error is set to False
    with self.assertRaises(HTTPError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.http_service.send_request(
          method='GET',
          url='http://foo.com',
          max_retries=0,
          handle_http_error=False)

    self.assertEqual('', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_attempts_four_retries_by_default(self):
    # Note, for this test to work, we must use a retriable error code.
    http_error = HTTPError('https://foo.com', 500, 'Internal Server Error', {},
                           BytesIO(b'Fake Error Message'))
    self.set_urlopen_exception(http_error)

    # Note, we're patching stderr here so no error messages leak out to
    # the terminal running the test.
    with self.assertRaises(SilentlyExitError), \
         patch('sys.stderr'):
      self.http_service.send_request(method='GET', url='http://foo.com')

    # 1 for the initial call, then the 4 retries.
    self.assertEqual(5, self.urlopen_mock.call_count)

  def test_max_retries_is_configurable(self):
    # Note, for this test to work, we must use a retriable error code.
    http_error = HTTPError('https://foo.com', 500, 'Internal Server Error', {},
                           BytesIO(b'Fake Error Message'))
    self.set_urlopen_exception(http_error)

    # Note, we're patching stderr here so no error messages leak out to
    # the terminal running the test.
    with self.assertRaises(SilentlyExitError), \
         patch('sys.stderr'):
      self.http_service.send_request(
          method='GET', url='http://foo.com', max_retries=7)

    # 1 for the initial call, then the 7 retries.
    self.assertEqual(8, self.urlopen_mock.call_count)

  def test_default_timeout_is_expected_value(self):
    self.http_service.send_request(method='POST', url='http://foo.com')
    self.urlopen_mock.assert_called_once_with(ANY, timeout=10)

  def test_timeout_is_configurable(self):
    self.http_service.send_request(
        method='POST', url='http://foo.com', timeout_sec=999)

    self.urlopen_mock.assert_called_once_with(ANY, timeout=999)

  def test_returns_expected_data_on_success(self):
    # Just run it through a few basic test cases, ensure it's decoding the json
    # data as expected and returning it.
    testcases = [
        {},
        [],
        [{
            'foo': 'bar'
        }],
        'foo',
        {
            'p1': 'v1',
            'p2': {
                'p3': 'v3'
            }
        },
    ]

    for data in testcases:
      with self.subTest(data):
        self.set_urlopen_response(body=data)
        obtained_response = self.http_service.send_request(
            method='GET', url='http://foo.com')
        self.assertEqual(data, obtained_response)


class HttpServiceSendTests(unittest.TestCase):
  """ Unit tests for the send() method of the HttpService class.
  """

  def setUp(self):
    self.user_output_mock = MagicMock(
        wraps=UserOutput(
            is_debug_enabled=False,
            data_formatter=data_formatter.DataFormatter()))

    # A default test instance which tests are free to use, some tests will still
    # create their own custom version as needed.
    self.http_service = HttpService(TEST_PROJECT_ID, TEST_ACCESS_TOKEN,
                                    self.user_output_mock)

    # Setup patching of the 'urllib.request.urlopen' function, which the
    # HttpService class depends on.
    self.urlopen_patcher = patch(
        'snapshot_dbg_cli.http_service.urlopen', autospec=True)
    self.urlopen_mock = self.urlopen_patcher.start()
    self.addCleanup(self.urlopen_patcher.stop)

    self.sleep_patcher = patch('time.sleep', autospec=True)
    self.sleep_mock = self.sleep_patcher.start()
    self.addCleanup(self.sleep_patcher.stop)

    # Install a happy response so by default calling send will succeed. Tests
    # that care will override when needed.
    self.set_urlopen_response(body={})

    # Most test will need a valid request, but not care about the contents.
    self.test_request = self.http_service.build_request('GET', 'http://foo.com')

  def set_urlopen_response(self,
                           body,
                           content_type=DEFAULT_JSON_CONTENT_TYPE,
                           url=''):
    body = json.dumps(body).encode('utf-8')
    self.urlopen_mock.return_value = build_http_response(
        body, content_type, url)

  def set_urlopen_exception(self, exception):
    self.urlopen_mock.side_effect = exception

  def test_uses_expected_request(self):
    request = self.http_service.build_request(
        method='POST',
        url='http://foo.com',
        parameters=['p1=v1', 'p2=v2'],
        data={'foo': 'bar'},
        include_project_header=True)

    self.http_service.send(request)

    self.urlopen_mock.assert_called_once()
    request = self.urlopen_mock.call_args[0][0]
    self.assertEqual('POST', request.method)
    self.assertEqual('http://foo.com?p1=v1&p2=v2', request.full_url)
    self.assertEqual(b'{"foo": "bar"}', request.data)
    self.assertTrue(request.has_header(GOOG_USER_PROJECT_HEADER))

  def test_handles_http_error_by_default(self):
    http_error = HTTPError('https://foo.com', 404, 'Not Found', {},
                           BytesIO(b'Fake Error Message'))
    self.set_urlopen_exception(http_error)

    # We expect the HttpService to catch the HttpError, print an error, then
    # raise a SilentlyExitError to cause the CLI to exit.
    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.http_service.send(self.test_request, max_retries=0)

    self.assertIn('Fake Error Message', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_allows_http_error_to_progate_when_requested(self):
    http_error = HTTPError('https://foo.com', 404, 'Not Found', {},
                           BytesIO(b'Fake Error Message'))
    self.set_urlopen_exception(http_error)

    # We expect the HttpService to allow the HttpError to propagate
    # when handle_http_error is set to False
    with self.assertRaises(HTTPError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.http_service.send(
          self.test_request, max_retries=0, handle_http_error=False)

    self.assertEqual('', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_attempts_four_retries_by_default(self):
    # Note, for this test to work, we must use a retriable error code.
    http_error = HTTPError('https://foo.com', 500, 'Internal Server Error', {},
                           BytesIO(b'Fake Error Message'))
    self.set_urlopen_exception(http_error)

    # Note, we're patching stderr here so no error messages leak out to
    # the terminal running the test.
    with self.assertRaises(SilentlyExitError), \
         patch('sys.stderr'):
      self.http_service.send(self.test_request)

    # 1 for the initial call, then the 4 retries.
    self.assertEqual(5, self.urlopen_mock.call_count)

  def test_max_retries_configurable(self):
    # Note, for this test to work, we must use a retriable error code.
    http_error = HTTPError('https://foo.com', 500, 'Internal Server Error', {},
                           BytesIO(b'Fake Error Message'))
    self.set_urlopen_exception(http_error)

    # Note, we're patching stderr here so no error messages leak out to
    # the terminal running the test.
    with self.assertRaises(SilentlyExitError), \
         patch('sys.stderr'):
      self.http_service.send(self.test_request, max_retries=7)

    # 1 for the initial call, then the 7 retries.
    self.assertEqual(8, self.urlopen_mock.call_count)

  def test_max_retries_of_zero_works_as_expected(self):
    # Note, for this test to work, we must use a retriable error code.
    http_error = HTTPError('https://foo.com', 500, 'Internal Server Error', {},
                           BytesIO(b'Fake Error Message'))
    self.set_urlopen_exception(http_error)

    # Note, we're patching stderr here so no error messages leak out to
    # the terminal running the test.
    with self.assertRaises(SilentlyExitError), \
         patch('sys.stderr'):
      self.http_service.send(self.test_request, max_retries=0)

    self.assertEqual(1, self.urlopen_mock.call_count)

  def test_retries_only_retriable_error_codes(self):
    # These are the error_codes HttpService considers retriable.
    retriable_codes = [429, 500, 502, 503, 504]

    for error_code in range(200, 600):
      with self.subTest(f'ErrorCode: {error_code}'):
        self.urlopen_mock.reset_mock()
        http_error = HTTPError('https://foo.com', error_code,
                               f'Error - {error_code}', {},
                               BytesIO(b'Fake Error Message'))

        self.set_urlopen_exception(http_error)

        # Note, we're patching stderr here so no error messages leak out to
        # the terminal running the test.
        with self.assertRaises(SilentlyExitError), \
             patch('sys.stderr'):
          self.http_service.send(self.test_request, max_retries=1)

        expected_call_count = 2 if error_code in retriable_codes else 1
        self.assertEqual(expected_call_count, self.urlopen_mock.call_count)

  def test_send_handles_urlerror_exception_as_expected(self):
    self.set_urlopen_exception(URLError('URLError Fake Error Message'))

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.http_service.send(self.test_request, max_retries=1)

    # It should retry URLErrors, so we expect 2 calls.
    self.assertEqual(2, self.urlopen_mock.call_count)
    self.assertIn('URLError Fake Error Message', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_send_handles_timeout_error_expected(self):
    self.set_urlopen_exception(TimeoutError())

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.http_service.send(self.test_request, max_retries=1)

    # It should retry TimeoutErrors, so we expect 2 calls.
    self.assertEqual(2, self.urlopen_mock.call_count)
    self.assertIn('ERROR The REST request timed out', err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_send_handles_jsondecode_error_as_expected(self):
    # Attempting to decode this response as json should cause a JSONDecodeError
    self.urlopen_mock.return_value = build_http_response(
        '{bad json'.encode('utf-8'))

    with self.assertRaises(SilentlyExitError), \
         patch('sys.stdout', new_callable=StringIO) as out, \
         patch('sys.stderr', new_callable=StringIO) as err:
      self.http_service.send(self.test_request, max_retries=1)

    # It should not retry JSONDecodeErrors, so we expect 1 call.
    self.assertEqual(1, self.urlopen_mock.call_count)
    self.assertIn('ERROR Failure occured parsing the response as json',
                  err.getvalue())
    self.assertEqual('', out.getvalue())

  def test_retry_backoffs_work_as_expected(self):
    # Note, for this test to work, we must use a retriable error code.
    http_error = HTTPError('https://foo.com', 500, 'Internal Server Error', {},
                           BytesIO(b'Fake Error Message'))
    self.set_urlopen_exception(http_error)

    # Note, we're patching stderr here so no error messages leak out to
    # the terminal running the test.
    with self.assertRaises(SilentlyExitError), \
         patch('sys.stderr'):
      self.http_service.send(self.test_request, max_retries=5)

    expected_sleep_calls = [call(1), call(2), call(4), call(8), call(16)]
    self.assertEqual(expected_sleep_calls, self.sleep_mock.mock_calls)

  def test_successful_response_after_retry_works_as_expected(self):
    first_side_effect_call = True

    def side_effect(request, timeout):
      del request
      del timeout
      nonlocal first_side_effect_call
      if first_side_effect_call:
        first_side_effect_call = False
        # Note, for send to retry, we must use a retriable error code.
        raise HTTPError('https://foo.com', 500, 'Internal Server Error', {},
                        BytesIO(b'Fake Error Message'))

      return build_http_response(json.dumps({'foo': 'bar'}).encode('utf-8'))

    self.urlopen_mock.side_effect = side_effect
    response = self.http_service.send(self.test_request, max_retries=4)
    self.assertEqual({'foo': 'bar'}, response)
    self.assertEqual(2, self.urlopen_mock.call_count)

  def test_default_timeout_is_expected_value(self):
    self.http_service.send(self.test_request)
    self.urlopen_mock.assert_called_once_with(ANY, timeout=10)

  def test_timeout_is_configurable(self):
    self.http_service.send(self.test_request, timeout_sec=999)
    self.urlopen_mock.assert_called_once_with(ANY, timeout=999)

  def test_returns_expected_type_for_different_encodings(self):
    simple_html = '<!DOCTYPE html> <p>foo</p> </html>'
    testcases = [
        # testname, body_bytes, content-type, expected_response

        # For JSON input, decoded json is expected
        ('JSON empty dict', '{}'.encode('utf-8'),
         'application/json; charset=utf-8', {}),
        ('JSON empty list', '[]'.encode('utf-8'),
         'application/json; charset=utf-8', []),
        ('JSON string', '"foo"'.encode('utf-8'),
         'application/json; charset=utf-8', 'foo'),
        ('JSON list', '["foo", "bar"]'.encode('utf-8'),
         'application/json; charset=utf-8', ['foo', 'bar']),
        ('JSON dict', '{"foo1": "bar1", "foo2": "bar2"}'.encode('utf-8'),
         'application/json; charset=utf-8', {
             'foo1': 'bar1',
             'foo2': 'bar2'
         }),
        ('JSON UTF-8', '{"foo": "bar"}'.encode('utf-8'),
         'application/json; charset=utf-8', {
             'foo': 'bar'
         }),
        ('JSON UTF-16', '{"foo": "bar"}'.encode('utf-16'),
         'application/json; charset=utf-16', {
             'foo': 'bar'
         }),

        # For non JSON data, the string as is expected to be returned
        ('Text Plain UTF-8', 'foo'.encode('utf-8'), 'text/plain; charset=utf-8',
         'foo'),
        ('Text Plain UTF-16', 'foo'.encode('utf-16'),
         'text/plain; charset=utf-16', 'foo'),
        ('Text HTML UTF-8', simple_html.encode('utf-8'),
         'text/html; charset=utf-8', simple_html),
        ('Text HTML UTF-16', simple_html.encode('utf-16'),
         'text/html; charset=utf-16', simple_html),
    ]

    for testname, body_bytes, content_type, expected_response in testcases:
      with self.subTest(testname):
        self.urlopen_mock.return_value = build_http_response(
            body_bytes, content_type)
        obtained_response = self.http_service.send(self.test_request)
        self.assertEqual(expected_response, obtained_response)
