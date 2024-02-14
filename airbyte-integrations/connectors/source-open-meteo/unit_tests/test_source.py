#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

from unittest.mock import MagicMock

from source_open_meteo.source import SourceOpenMeteo
import json

def test_check_connection(mocker):
    source = SourceOpenMeteo()
    logger_mock = MagicMock()
    with open('unit_tests/config_valid_base.json') as fp:
        config_valid_base = json.load(fp)
        
    assert source.check_connection(logger_mock, config_valid_base) == (True, None)

def test_check_invalid_connection(mocker):
    source = SourceOpenMeteo()
    logger_mock = MagicMock()
    with open('unit_tests/config_invalid_latitude.json') as fp:
        config_invalid_latitude = json.load(fp)

    # Should return (False, "Latitude -137.1 must be between -90.0 and 90.0")    
    assert not source.check_connection(logger_mock, config_invalid_latitude) == (True, None)


def test_streams(mocker):
    source = SourceOpenMeteo()
    
    with open('unit_tests/config_valid_base.json') as fp:
        config_valid_base = json.load(fp)

    streams = source.streams(config_valid_base)
    expected_streams_number = 2
    
    assert len(streams) == expected_streams_number
