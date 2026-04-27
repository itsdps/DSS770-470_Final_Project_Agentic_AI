from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class SimpleChatBot:
    def __init__(self, system_instruction="", model_name="gpt-4o-mini"):
        # OpenAI SDK automatically reads OPENAI_API_KEY from environment
        self.client = OpenAI()

        self.temperature = 0.5
        self.top_p = 1.0

        # Store system instruction and model name
        self.system_instruction = system_instruction
        self.model_name = model_name

        # Chat history (OpenAI format: list of dicts with role and content)
        self.messages = []

    def __call__(self, message):
        """Handles user input and returns chatbot response."""
        # Add user message to history
        self.messages.append({"role": "user", "content": message})

        result = self.execute()
        if result == "An error occurred while processing the message.":
            # Remove the failed user message if error occurs
            self.messages.pop()
            return None  # Indicate error

        # Add assistant response to history
        self.messages.append({"role": "assistant", "content": result})
        return result

    def clear_chat_history(self):
        """Clears the chat history."""
        self.messages = []

    def execute(self):
        """Executes the chat with the accumulated messages using OpenAI API."""
        try:
            # Prepare system message if provided
            system_message = None
            if self.system_instruction:
                system_message = {"role": "system", "content": self.system_instruction}
            
            # Build messages list with system instruction at the front
            messages_to_send = []
            if system_message:
                messages_to_send.append(system_message)
            messages_to_send.extend(self.messages)
            
            # Send to OpenAI API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages_to_send,
                temperature=self.temperature,
                top_p=self.top_p
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error executing chat: {e}")
            return "An error occurred while processing the message."

# Example usage:
if __name__ == '__main__':
    chatbot = SimpleChatBot(system_instruction="You are a helpful and concise assistant.")  # , model_name="gemini-1.5-pro")

    while True:
        user_message = input("You: ")
        if user_message.lower() in ['exit', 'quit', 'bye', 'goodbye', 'bye!']:
            print("Assistant: Goodbye!")
            break

        response = chatbot(user_message)

        if response is None:  # Exit loop if an error occurs
            print("An error occurred. Exiting chat.")
            break

        print("Assistant:", response)
