import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Default configuration
DEFAULT_MODEL = "gemini-2.0-flash"

def get_client():
    """
    Creates and returns a Gemini Client.
    Ensures the API key is available in the environment.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("API Key not found. Please set GEMINI_API_KEY or GOOGLE_API_KEY in your .env file.")
    
    return genai.Client(api_key=api_key)

def generate_text(prompt, model_name=DEFAULT_MODEL, system_instruction=None, temperature=0.7, thinking_budget=None):
    """
    Generates text from a prompt using the specified model.
    
    Args:
        prompt (str): The input text prompt.
        model_name (str): The name of the model to use (default: gemini-2.5-flash).
        system_instruction (str): Optional system instructions to guide the model.
        temperature (float): Controls randomness (0.0 to 1.0).
        thinking_budget (int): Token budget for thinking (0 disables thinking).
    
    Returns:
        str: The generated text.
    """
    client = get_client()
    
    # Match notebook behavior: Disable thinking for 2.5-flash by default to save quota
    if model_name == "gemini-2.5-flash" and thinking_budget is None:
        thinking_budget = 0

    thinking_config = None
    if thinking_budget is not None:
        thinking_config = types.ThinkingConfig(thinking_budget=thinking_budget)
    
    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system_instruction,
        thinking_config=thinking_config
    )
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config
        )
        return response.text
    except Exception as e:
        # Simple retry for rate limits
        if "429" in str(e):
            print("Rate limit hit. Retrying in 5 seconds...")
            time.sleep(5)
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                return response.text
            except Exception as retry_e:
                print(f"Retry failed: {retry_e}")
                return None
        print(f"Error generating text: {e}")
        return None

def generate_text_stream(prompt, model_name=DEFAULT_MODEL, thinking_budget=None):
    """
    Generates text in a stream (yields chunks).
    """
    client = get_client()
    
    # Match notebook behavior: Disable thinking for 2.5-flash by default
    if model_name == "gemini-2.5-flash" and thinking_budget is None:
        thinking_budget = 0

    thinking_config = None
    if thinking_budget is not None:
        thinking_config = types.ThinkingConfig(thinking_budget=thinking_budget)
        
    config = types.GenerateContentConfig(
        thinking_config=thinking_config
    )
    
    try:
        response = client.models.generate_content_stream(
            model=model_name,
            contents=prompt,
            config=config
        )
        for chunk in response:
            yield chunk.text
    except Exception as e:
        print(f"Error in streaming: {e}")

def chat_session(model_name=DEFAULT_MODEL):
    """
    Starts a simple interactive chat session in the terminal.
    """
    client = get_client()
    chat = client.chats.create(model=model_name)
    
    print(f"--- Chat Session Started ({model_name}) ---")
    print("Type 'quit' to exit.")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            break
        
        try:
            response = chat.send_message(user_input)
            print(f"Gemini: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    print("--- Testing Gemini API ---")
    
    # 1. Simple Text Generation
    print("\n1. Simple Text Generation:")
    result = generate_text("Explain quantum computing in one sentence.")
    print(f"Result: {result}")
    
    # 2. System Instructions
    print("\n2. With System Instructions (Pirate Mode):")
    pirate_result = generate_text(
        "Hello, how are you?", 
        system_instruction="You are a pirate. Speak like one."
    )
    print(f"Result: {pirate_result}")
    
    # 3. Streaming
    print("\n3. Streaming Response:")
    print("Result: ", end="", flush=True)
    for chunk in generate_text_stream("Count to 5 slowly."):
        print(chunk, end="", flush=True)
    print()
    
    # 4. Chat Session (Uncomment to run interactively)
    # chat_session()
