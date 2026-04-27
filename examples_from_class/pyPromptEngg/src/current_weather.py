import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()
RAPID_API_KEY = os.environ.get('RAPID_API_KEY')


def get_weather_data(location="Mount Laurel, NJ",
                     url="https://weatherapi-com.p.rapidapi.com/current.json"):
    querystring = {"q": location}

    headers = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": "weatherapi-com.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    return response.json()

# print(get_weather_data(location='PHL'))

#{'location': {'name': 'Philadelphia International Airport', 'region': 'Philadelphia', 'country': 'United States of America', 'lat': 39.88, 'lon': -75.24, 'tz_id': 'America/New_York', 'localtime_epoch': 1714149060, 'localtime': '2024-04-26 12:31'}, 'current': {'last_updated_epoch': 1714149000, 'last_updated': '2024-04-26 12:30', 'temp_c': 14.5, 'temp_f': 58.1, 'is_day': 1, 'condition': {'text': 'Sunny', 'icon': '//cdn.weatherapi.com/weather/64x64/day/113.png', 'code': 1000}, 'wind_mph': 10.5, 'wind_kph': 16.9, 'wind_degree': 150, 'wind_dir': 'SSE', 'pressure_mb': 1032.0, 'pressure_in': 30.47, 'precip_mm': 0.0, 'precip_in': 0.0, 'humidity': 31, 'cloud': 0, 'feelslike_c': 13.9, 'feelslike_f': 57.0, 'vis_km': 16.0, 'vis_miles': 9.0, 'uv': 5.0, 'gust_mph': 15.0, 'gust_kph': 24.1}}

def get_current_weather(location="Mount Laurel, NJ", unit='fahrenheit') -> str:
    current_weather_data = get_weather_data(location)['current']
    temp = current_weather_data['temp_f']
    feels_like = current_weather_data['feelslike_f']
    if unit[0] == 'c':
        temp = current_weather_data['temp_c']
        feels_like = current_weather_data['feelslike_c']

    weather_info = {"location": location,
                    "temperature": temp,
                    "unit": unit,
                    "feels_like": feels_like,
                    "condition": current_weather_data['condition']['text'],
                    "humidity": current_weather_data['humidity'],
                    "wind_speed": f"{current_weather_data['wind_mph']} mph"
                    }
    return json.dumps(weather_info)


if __name__ == '__main__':
    print(get_current_weather(location="Myrtle Beach, SC"))
