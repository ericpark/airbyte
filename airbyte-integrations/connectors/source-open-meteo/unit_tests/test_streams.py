#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

from http import HTTPStatus
from unittest.mock import Mock, patch, MagicMock


from requests import Response

import datetime
import json
import pytest
from source_open_meteo.source import OpenMeteoStream, DailyForecast, HourlyForecast


@pytest.fixture
def patch_base_class(mocker):
    # Mock abstract methods to enable instantiating abstract class
    mocker.patch.object(OpenMeteoStream, "path", "v0/example_endpoint")
    mocker.patch.object(OpenMeteoStream, "primary_key", "test_primary_key")
    mocker.patch.object(OpenMeteoStream, "__abstractmethods__", set())

@pytest.fixture
def config_valid_base():
    with open('unit_tests/config_valid_base.json') as fp:
        config = json.load(fp)
    return config

@pytest.fixture
def config_valid_base_resp():
    with open('unit_tests/config_valid_base_response.json') as fp:
        resp = json.load(fp)
    return resp

def test_request_params(patch_base_class, config_valid_base):
    stream = OpenMeteoStream(config=config_valid_base)
    inputs = {"stream_slice": None, "stream_state": None, "next_page_token": None}
    expected_params = {
        'forecast_days': None,
        'latitude': '-37.1',
        'longitude': '70.6',
        'past_days': None,
        'precipitation_unit': None,
        'temperature_unit': None,
        'timezone': 'GMT',
        'wind_speed_unit': None
    }
    assert stream.request_params(**inputs) == expected_params

def test_request_params_daily(patch_base_class, config_valid_base, ):
    stream = DailyForecast(config=config_valid_base)
    inputs = {"stream_slice": None, "stream_state": None, "next_page_token": None}
    expected_params = {
        'forecast_days': None,
        'latitude': '-37.1',
        'longitude': '70.6',
        'past_days': None,
        'precipitation_unit': None,
        'temperature_unit': None,
        'timezone': 'GMT',
        'wind_speed_unit': None,
        'daily': 'weather_code,precipitation_sum'
    }
    assert stream.request_params(**inputs) == expected_params

def test_request_params_hourly(patch_base_class, config_valid_base):
    stream = HourlyForecast(config=config_valid_base)
    inputs = {"stream_slice": None, "stream_state": None, "next_page_token": None}
    expected_params = {
        'forecast_days': None,
        'latitude': '-37.1',
        'longitude': '70.6',
        'past_days': None,
        'precipitation_unit': None,
        'temperature_unit': None,
        'timezone': 'GMT',
        'wind_speed_unit': None,
        'hourly': 'weather_code'
    }
    assert stream.request_params(**inputs) == expected_params

def test_parse_response_daily(patch_base_class, config_valid_base, config_valid_base_resp):
    mock = MagicMock()
    mock.json.return_value = config_valid_base_resp

    stream = DailyForecast(config=config_valid_base)

    now = datetime.datetime.now()
    expected_parsed_object = {
       'precipitation_sum': 3.4,
        'time': '2024-02-14',
        'weather_code': 'Rain showers: Slight intensity',
        'updated_at': now
    }

    parsed = stream.parse_response(response=mock)[0]
    
    # Do not test udpated_at because it is set at parsing time.
    parsed["updated_at"] = now
    

    assert parsed  == expected_parsed_object

def test_http_method(patch_base_class, config_valid_base):
    stream = OpenMeteoStream(config=config_valid_base)
    # TODO: replace this with your expected http request method
    expected_method = "GET"
    assert stream.http_method == expected_method


@pytest.mark.parametrize(
    ("http_status", "should_retry"),
    [
        (HTTPStatus.OK, False),
        (HTTPStatus.BAD_REQUEST, False),
        (HTTPStatus.TOO_MANY_REQUESTS, True),
        (HTTPStatus.INTERNAL_SERVER_ERROR, True),
    ],
)
def test_should_retry(patch_base_class, http_status, should_retry, config_valid_base):
    response_mock = MagicMock()
    response_mock.status_code = http_status
    stream = OpenMeteoStream(config=config_valid_base)
    assert stream.should_retry(response_mock) == should_retry


def test_backoff_time(patch_base_class, config_valid_base):
    response_mock = MagicMock()
    stream = OpenMeteoStream(config=config_valid_base)
    expected_backoff_time = None
    assert stream.backoff_time(response_mock) == expected_backoff_time