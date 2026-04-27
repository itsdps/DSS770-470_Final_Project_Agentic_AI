import os
import time
try:
    from dotenv import load_dotenv
except ImportError:
    # Fallback if python-dotenv is not installed; environment variables must already be set
    def load_dotenv(*args, **kwargs):
        return False
from openai import OpenAI

# Load environment variables
load_dotenv()

# Default configuration
DEFAULT_MODEL = "gpt-4o-mini"

def get_client():
    """
    Creates and returns an OpenAI Client.
    Ensures the API key is available in the environment.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("API Key not found. Please set OPENAI_API_KEY in your .env file.")
    
    return OpenAI(api_key=api_key)

def get_model(): 
    """
    Returns the default model name.
    """
    return DEFAULT_MODEL

def generate_text(
    prompt, 
    model_name=DEFAULT_MODEL, 
    system_instruction=None, 
    temperature=0.7,
    max_tokens=None,
    stream=False,
    response_format=None,
    frequency_penalty=0.0,
    presence_penalty=0.0,
    stop=None,
    seed=None
):
    """
    Generates text from a prompt using the specified model.
    
    Args:
        prompt (str): The input text prompt.
        model_name (str): The name of the model to use (default: gpt-4o-mini).
        system_instruction (str): Optional system instructions to guide the model.
        temperature (float): Controls randomness (0.0 to 2.0). Lower = more focused, higher = more creative.
        max_tokens (int): Maximum number of tokens to generate. Controls response length and cost.
        stream (bool): If True, returns a generator that yields content as it's generated.
        response_format (dict): Specify output format, e.g., {"type": "json_object"} for JSON mode.
        frequency_penalty (float): Reduces repetition based on token frequency (-2.0 to 2.0).
        presence_penalty (float): Encourages new topics (-2.0 to 2.0).
        stop (str or list): String(s) where generation should stop.
        seed (int): For deterministic outputs (best effort). Useful for testing/debugging.
    
    Returns:
        str: The generated text (if stream=False).
        generator: A generator yielding text chunks (if stream=True).
    """
    client = get_client()
    
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    
    # Build the API call parameters
    api_params = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
        "stream": stream
    }
    
    # Add optional parameters only if specified
    if max_tokens is not None:
        api_params["max_tokens"] = max_tokens
    if response_format is not None:
        api_params["response_format"] = response_format
    if stop is not None:
        api_params["stop"] = stop
    if seed is not None:
        api_params["seed"] = seed
    
    try:
        response = client.chat.completions.create(**api_params)
        
        if stream:
            # Return a generator for streaming responses
            def stream_generator():
                for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content is not None:
                        yield content
            return stream_generator()
        else:
            # Return the complete response
            return response.choices[0].message.content
            
    except Exception as e:
        print(f"Error generating text: {e}")
        return None


# Example usage functions for tutorial demonstrations

def demo_temperature():
    """
    Demonstrates the effect of temperature on creativity.
    """
    prompt = "Write a creative tagline for a coffee shop."
    
    print("=== Temperature Demo ===\n")
    print("Low temperature (0.2) - Focused and consistent:")
    print(generate_text(prompt, temperature=0.2))
    print("\nHigh temperature (1.5) - Creative and varied:")
    print(generate_text(prompt, temperature=1.5))
    print("\n")

def demo_max_tokens():
    """
    Demonstrates how max_tokens controls response length.
    """
    prompt = "Explain what machine learning is."
    
    print("=== Max Tokens Demo ===\n")
    print("Short response (50 tokens):")
    print(generate_text(prompt, max_tokens=50))
    print("\nLonger response (200 tokens):")
    print(generate_text(prompt, max_tokens=200))
    print("\n")

def demo_json_mode():
    """
    Demonstrates structured JSON output.
    """
    prompt = "Analyze the sentiment of this review: 'This product exceeded my expectations!'"
    system_instruction = "You are a sentiment analyzer. Always respond with valid JSON containing 'sentiment' and 'confidence' fields."
    
    print("=== JSON Mode Demo ===\n")
    result = generate_text(
        prompt, 
        system_instruction=system_instruction,
        response_format={"type": "json_object"}
    )
    print("Structured JSON output:")
    print(result)
    print("\n")

def demo_streaming():
    """
    Demonstrates streaming responses for real-time feedback.
    """
    prompt = "Write a short poem about coding."
    
    print("=== Streaming Demo ===\n")
    print("Streaming response (appears word-by-word):")
    
    stream = generate_text(prompt, stream=True)
    for chunk in stream:
        print(chunk, end="", flush=True)
    print("\n\n")

def demo_penalties():
    """
    Demonstrates frequency penalty to reduce repetition.
    """
    prompt = "List 5 benefits of exercise."
    
    print("=== Frequency Penalty Demo ===\n")
    print("Without penalty (may repeat words):")
    print(generate_text(prompt, frequency_penalty=0.0))
    print("\nWith penalty (more variety):")
    print(generate_text(prompt, frequency_penalty=1.0))
    print("\n")

def demo_stop_sequences():
    """
    Demonstrates using stop sequences to control output.
    """
    prompt = "List programming languages:\n1."
    
    print("=== Stop Sequence Demo ===\n")
    print("Stopping at '###':")
    result = generate_text(prompt, stop="###", max_tokens=100)
    print(result)
    print("\n")

def demo_seed():
    """
    Demonstrates reproducible outputs with seed.
    """
    prompt = "Generate a random product name."
    seed_value = 12345
    
    print("=== Seed Demo (Reproducibility) ===\n")
    print(f"First call with seed={seed_value}:")
    print(generate_text(prompt, seed=seed_value, temperature=1.0))
    print(f"\nSecond call with same seed={seed_value}:")
    print(generate_text(prompt, seed=seed_value, temperature=1.0))
    print(f"\nCall with different seed:")
    print(generate_text(prompt, seed=67890, temperature=1.0))
    print("\n")


def list_models():
    """
    Returns a sorted list of all available model IDs from OpenAI.
    """
    client = get_client()
    try:
        models = client.models.list()
        ids = [m.id for m in models.data]
        return sorted(ids)
    except Exception as e:
        print(f"Error listing models: {e}")
        return []

def list_text_models():
    """
    Returns a filtered list of models suitable for text/chat generation.
    Excludes embedding, audio, image-only, and TTS models.
    """
    ids = list_models()
    if not ids:
        return []

    exclude_keywords = [
        "embedding", "audio", "whisper", "tts", "speech", "image", "clip"
    ]
    def is_text_model(mid: str) -> bool:
        lower = mid.lower()
        if any(k in lower for k in exclude_keywords):
            return False
        # Common families for text/chat
        return lower.startswith("gpt") or lower.startswith("o") or lower.startswith("text-")

    return [mid for mid in ids if is_text_model(mid)]

def generate_text_stream(prompt, model_name=DEFAULT_MODEL, system_instruction=None, temperature=0.7):
    """
    Generates text in a stream (yields chunks).
    """
    client = get_client()
    
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    
    try:
        stream = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    except Exception as e:
        print(f"Error in streaming: {e}")

class Chat:
    """
    A class to manage chat history and state, similar to Gemini's ChatSession.
    """
    def __init__(self, model_name=DEFAULT_MODEL, system_instruction=None, history=None):
        self.client = get_client()
        self.model_name = model_name
        self.messages = []
        
        if system_instruction:
            self.messages.append({"role": "system", "content": system_instruction})
        
        if history:
            self.messages.extend(history)

    def send_message(self, message):
        """
        Sends a message to the model and returns the response text.
        Appends both user message and assistant response to history.
        """
        self.messages.append({"role": "user", "content": message})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.messages
            )
            reply = response.choices[0].message.content
            self.messages.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            print(f"Error sending message: {e}")
            return None

def chat_session(model_name=DEFAULT_MODEL, system_instruction=None):
    """
    Starts a simple interactive chat session in the terminal.
    """
    chat = Chat(model_name, system_instruction)
    
    print(f"--- Chat Session Started ({model_name}) ---")
    print("Type 'quit' to exit.")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            break
        
        response = chat.send_message(user_input)
        if response:
            print(f"OpenAI: {response}")

if __name__ == "__main__":
    # Run all demos
    print("OpenAI API Parameter Tutorial\n" + "="*50 + "\n")
    
    demo_temperature()
    # demo_max_tokens()
    # demo_json_mode()
    # demo_streaming()
    # demo_penalties()
    # demo_stop_sequences()
    # demo_seed()

# if __name__ == "__main__":
#     print("--- Testing OpenAI API ---")
    
#     # 1. Simple Text Generation
#     print("\n1. Simple Text Generation:")
#     result = generate_text("Explain quantum computing in one sentence.")
#     print(f"Result: {result}")
    
#     # 2. System Instructions
#     print("\n2. With System Instructions (Pirate Mode):")
#     pirate_result = generate_text(
#         "Hello, how are you?", 
#         system_instruction="You are a pirate. Speak like one."
#     )
#     print(f"Result: {pirate_result}")
    
#     # 3. Streaming
#     print("\n3. Streaming Response:")
#     print("Result: ", end="", flush=True)
#     for chunk in generate_text_stream("Count to 5 slowly."):
#         print(chunk, end="", flush=True)
#     print()
    
    # 4. Chat Session (Uncomment to run interactively)
    # chat_session()
