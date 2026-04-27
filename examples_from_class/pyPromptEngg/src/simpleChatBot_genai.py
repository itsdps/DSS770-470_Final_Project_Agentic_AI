import google.generativeai as genai
import os
from dotenv import load_dotenv

class SimpleChatBot:
    def __init__(self, system_instruction="", model_name="gemini-1.5-flash"):
        self.api_key = self._load_api_key()
        genai.configure(api_key=self.api_key)

        self.temperature = 0.5
        self.top_p = 0
        self.top_k = 1

        self.generation_config = genai.types.GenerationConfig(
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k
        )

        # Initialize the model with system instructions
        self.model_name = model_name
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            system_instruction=system_instruction  # Proper way to set system behavior
        )

        # Chat history
        self.messages = []
        self.chat = self.model.start_chat(history=self.messages)

    def _load_api_key(self):
        """Loads the API key from an environment variable or a file."""
        load_dotenv()

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            try:
                with open("GOOGLE_API_KEY.txt", "r") as file:
                    api_key = file.read().strip()
            except FileNotFoundError:
                print("Error: GOOGLE_API_KEY.txt not found. Set GOOGLE_API_KEY environment variable or create the file.")
                raise  # Re-raise the exception to stop execution

        if not api_key:
            raise ValueError("API key not found. Set GOOGLE_API_KEY environment variable or create GOOGLE_API_KEY.txt.")
        return api_key

    def __call__(self, message):
        """Handles user input and returns chatbot response."""
        self.messages.append({"role": "user", "parts": [message]})

        result = self.execute()
        if result == "An error occurred while processing the message.":
            return None  # Indicate error

        self.messages.append({"role": "model", "parts": [result]})  # Append chatbot response
        return result

    def clear_chat_history(self):
        self.messages=[]
        self.chat=self.model.start_chat(history=self.messages)

    def execute(self):
        """Executes the chat with the accumulated messages."""
        try:
            # Send latest user message and get response
            response = self.chat.send_message(self.messages[-1]["parts"][0])  # Send only latest message
            return response.text
        except Exception as e:
            print(f"Error executing chat: {e}")
            return "An error occurred while processing the message."

# Example usage:
if __name__ == '__main__':
    chatbot = SimpleChatBot(system_instruction="You are a helpful and concise assistant.")  # , model_name="gemini-1.5-pro")

    while True:
        user_message = input("You: ")
        if user_message.lower() in ['exit', 'quit', 'bye']:
            print("Assistant: Goodbye!")
            break

        response = chatbot(user_message)

        if response is None:  # Exit loop if an error occurs
            print("An error occurred. Exiting chat.")
            break

        print("Assistant:", response)
