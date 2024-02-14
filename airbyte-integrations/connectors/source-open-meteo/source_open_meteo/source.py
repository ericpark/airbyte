#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import requests
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.sources.streams.http.auth import TokenAuthenticator
from datetime import datetime

# Basic full refresh stream
class OpenMeteoStream(HttpStream, ABC):
    url_base = "https://api.open-meteo.com/v1/"

    # TODO: Move to incremental stream class. 
    cursor_field = "updated_at"
    primary_key = "time"

    # Mapping for weather codes as in documentation.
    weather_mapping = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog and depositing rime fog",
        48: "Fog and depositing rime fog",
        51: "Drizzle: Light intensity",
        53: "Drizzle: Moderate intensity",
        55: "Drizzle: Dense intensity",
        56: "Freezing Drizzle: Light intensity",
        57: "Freezing Drizzle: Dense intensity",
        61: "Rain: Slight intensity",
        63: "Rain: Moderate intensity",
        65: "Rain: Heavy intensity",
        66: "Freezing Rain: Light intensity",
        67: "Freezing Rain: Heavy intensity",
        71: "Snow fall: Slight intensity",
        73: "Snow fall: Moderate intensity",
        75: "Snow fall: Heavy intensity",
        77: "Snow grains",
        80: "Rain showers: Slight intensity",
        81: "Rain showers: Moderate intensity",
        82: "Rain showers: Violent intensity",
        85: "Snow showers: Slight intensity",
        86: "Snow showers: Heavy intensity",
        95: "Thunderstorm: Slight",
        96: "Thunderstorm with hail: Slight intensity",
        99: "Thunderstorm with hail: Heavy intensity"
    }

    def __init__(self, config: Mapping[str, Any], **kwargs):
        super().__init__()
        self.latitude = str(config['latitude']) #required
        self.longitude = str(config['longitude']) #required
        
        """
        Some Values are defaulted by the UI and have been tested to work with the default value
        """
        self.forecast_days = None if 'forecast_days' not in config else str(config['forecast_days'])        
        self.past_days = None if 'past_days' not in config else str(config['past_days'])
        self.timezone = 'GMT' if 'timezone' not in config else config['timezone'] # None = GMT

        """
        None values are set for some of the following because a dropdown menu item can not be set to a different/empty value.
        """
        self.temperature_unit = (
            None if 'temperature_unit' not in config # None = Celsius
            else None if config['temperature_unit'] == 'celsius' #celsius works
            else config['temperature_unit']
        )
        self.precipitation_unit = (
            None if 'precipitation_unit' not in config # None = millimeter
            else None if config['precipitation_unit'] == 'millimeter' #millimeter is not valid
            else config['precipitation_unit'] 
        )
        self.wind_speed_unit = (
            None if 'wind_speed_unit' not in config # None = km/h
            else 'mph' if config['wind_speed_unit'] == 'Mph' 
            else 'ms' if config['wind_speed_unit'] == 'm/s' 
            else 'kn' if config['wind_speed_unit'] == 'knots' 
            else None
        )
        self.common_req_params = {
            'latitude':self.latitude, 
            'timezone':self.timezone, 
            'longitude':self.longitude, 
            'wind_speed_unit':self.wind_speed_unit, 
            'forecast_days':self.forecast_days, 
            'past_days':self.past_days, 
            'temperature_unit':self.temperature_unit, 
            'precipitation_unit':self.precipitation_unit
        }

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        The API path is the same but the streams are split based on the request params.
        """
        return "forecast"

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        return None

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        """
        Overridden in the subsequent classes. This is used for testing.
        """
        return self.common_req_params 

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        Overridden in the subsequent classes.
        """
        yield {}


class HourlyForecast(OpenMeteoStream):
    def __init__(self, config: Mapping[str, Any], **kwargs):
        super().__init__(config=config)
        """
        Set the common parameters and then set the hourly fields.
        """
        self.hourly =  ",".join(config['hourly'])
    
    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        req_params = self.common_req_params
        req_params['hourly'] = self.hourly
        return req_params

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        hourly data is an object where each key has a list of values with the length of ((forecast_days + past_days) * 24)
        since the number of keys is unknown, the lists are zipped together into a list of day objects
        
        Example:
        { "hourly" : { "time": [ t1, t2, ... ],  "weather_code": [ w1, w2, ... ], "precipitation": [p1, p2, ... ], ... } }
        [{"time": t1, "weather_code: w1, precipitation: p1, ... }, {"time": t2, "weather_code: w2, precipitation: p2, ... }, ... ]

        """

        resp = response.json()

        keys = resp['hourly'].keys()
        data = [dict(zip(keys, values)) for values in zip(*resp['hourly'].values())]
        data = [dict(item, updated_at=datetime.now(), weather_code=self.weather_mapping[item['weather_code']]) for item in data]

        return data


class DailyForecast(OpenMeteoStream):
    def __init__(self, config: Mapping[str, Any], **kwargs):
        super().__init__(config=config)
        """
        Set the common parameters and then set the daily fields.
        """
        self.daily =  ",".join(config['daily'])

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        req_params = self.common_req_params
        req_params['daily'] = self.daily
        return req_params
    
    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        daily data is an object where each key has a list of values with the length of forecast_days + past_days
        since the number of keys is unknown, the lists are zipped together into a list of day objects
        
        Example:
        { "daily" : { "time": [ t1, t2, ... ],  "weather_code": [ w1, w2, ... ], "precipitation": [p1, p2, ... ], ... } }
        [{"time": t1, "weather_code: w1, precipitation: p1, ... }, {"time": t2, "weather_code: w2, precipitation: p2, ... }, ... ]

        """
        resp = response.json()

        keys = resp['daily'].keys()
        data = [dict(zip(keys, values)) for values in zip(*resp['daily'].values())]
        data = [dict(item, updated_at=datetime.now(), weather_code=self.weather_mapping[item['weather_code']]) for item in data]

        return data

# Source
class SourceOpenMeteo(AbstractSource):
    def check_connection(self, logger, config) -> Tuple[bool, any]:
        # Spec ensures a non-empty number is sent for latitude and longitude
        try:       
            if (abs(float(config['latitude'])) >= 90.0 ):
                return False, f"Latitude {config['latitude']} must be between -90.0 and 90.0"
        except:
            return False, "Invalid latitude value provided"
        try:       
            if (abs(float(config['longitude'])) >= 180.0 ):
                return False, f"Longitude {config['longitude']} must be between -180.0 and 180.0"
        except:
            return False, "Invalid longitude value provided"
        
        # Spec ensures an array is sent for both hourly and daily
        if (len(config['daily']) < 1):
            return False, "Daily must include at least one field"
        if (len(config['hourly']) < 1):
            return False, "Hourly must include at least one field"
        
        # TODO: Implement API Key check here
        # TODO: Implement logging to AirbyteLogger on exceptions

        return True, None

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        
        # TODO: Implement API Key Auth here
     
        return [HourlyForecast(config=config), DailyForecast(config=config)]
