from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()

def get_current_weather(location: str):
    return {
        "location": location,
        "temperature": 61.0,
        "unit": "fahrenheit",
        "feels_like": 61.0,
        "condition": "Partly cloudy",
        "humidity": 30,
        "wind_speed": "2.2 mph"
    }

# Define the function declaration for the model
weather_function = {
    "name": "get_current_weather",
    "description": "Gets the current temperature for a given location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city name, e.g. San Francisco",
            },
        },
        "required": ["location"],
    },
}

# Configure the client and tools
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
tools = types.Tool(function_declarations=[weather_function])
config = types.GenerateContentConfig(tools=[tools])

# Send request with function declarations
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="What's the temperature in London?",
    config=config,
)

# Check for a function call
if response.candidates[0].content.parts[0].function_call:
    function_call = response.candidates[0].content.parts[0].function_call
    print(f"Function to call: {function_call.name}")
    print(f"Arguments: {function_call.args}")
    #  In a real app, you would call your function here:
    result = get_current_weather(**function_call.args)
    print(result)
else:
    print("No function call found in the response.")
    print(response.text)