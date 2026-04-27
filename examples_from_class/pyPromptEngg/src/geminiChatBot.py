import google.generativeai as genai
from dotenv import load_dotenv
import os
import datetime


# Load environment variables
load_dotenv()


class GeminiChatbot:
    def __init__(self, model_name='models/gemini-2.0-flash', system_instruction=None, output_folder="../data/output/"):
        """
        Initializes the Gemini chatbot.

        Args:
            model_name (str): The name of the Gemini model to use.
            output_folder (str): The folder where chat history will be saved.
        """
        self.model_name = model_name
        self.output_folder = output_folder

        # Configure API key
        genai.configure(api_key=self._load_api_key())

        # Default generation parameters
        temperature = 0.5
        top_p = 0
        """top_p stands for "top probability" and specifies the cumulative probability threshold for the tokens to consider.
        For example, if top_p is set to 0.95, the model will consider all tokens that together make up 95% of the total probability.
        top_p is set to 0, it essentially disables the top_p filtering mechanism.
        """
        top_k = 50
        """The top_k parameter is used to control the diversity of the generated text. 
        It specifies the number of topmost likely next tokens to consider when generating text.
        When top_k is set to 0, it means that the model will consider all possible next tokens.
        """

        # Initialize generation config
        self.generation_config = genai.GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k
        )

        # Initialize the model and chat session
        self.model = genai.GenerativeModel(self.model_name, generation_config=self.generation_config)
        self.chat = self.model.start_chat(history=[])
        if system_instruction:
            self.chat.send_message(system_instruction)

        print(f"Gemini Chatbot ({self.model_name}) Initialized. Ready for conversation.")

    @staticmethod
    def _load_api_key():
        """
        Loads the API key from an environment variable or a file.

        Returns:
            str: The API key.

        Raises:
            ValueError: If the API key is not found.
        """
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

    @staticmethod
    def list_models():
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)

    def send_message(self, message):
        """
        Sends a message to the Gemini model and returns the response.

        Args:
            message (str): The message to send to the chatbot.

        Returns:
            str: The response from the chatbot or an error message.
        """
        try:
            response = self.chat.send_message(message)
            return response.text
        except Exception as e:
            print(f"Error sending message: {e}")
            return f"**Error:** {e}"

    def end_chat(self):
        """
        Saves the chat history to a file with a timestamp.
        """
        try:
            os.makedirs(self.output_folder, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.output_folder, f'Gemini_history_output_{timestamp}.txt')

            with open(output_file, 'a') as file:
                for message in self.chat.history:
                    file.write(f'**{message.role}**: {message.parts[0].text}\n')

            print(f'\nChat history saved to file: {output_file}')
        except Exception as e:
            print(f"Error saving chat history: {e}")

    def change_temperature(self, temperature):
        """
        Changes the temperature of the model.

        Args:
            temperature (float): The new temperature value (must be between 0 and 1).

        Raises:
            ValueError: If the temperature is not within the valid range.
        """
        if not (0 <= temperature <= 1):
            raise ValueError("Temperature must be between 0 and 1.")

        try:
            self.generation_config.temperature = temperature
            self.model = genai.GenerativeModel(self.model_name, generation_config=self.generation_config)
            self.chat = self.model.start_chat(history=self.chat.history)  # Preserve history
            print(f"Temperature changed to: {temperature}")
        except Exception as e:
            print(f"Error changing temperature: {e}")

    def change_top_k(self, top_k):
        """
        Changes the TopK of the model.

        Args:
            top_k (int): The new TopK value (must be a positive integer).
        """
        if not (isinstance(top_k, int) and top_k > 0):
            raise ValueError("TopK must be a positive integer.")

        try:
            self.generation_config.top_k = top_k
            self.model = genai.GenerativeModel(self.model_name, generation_config=self.generation_config)
            self.chat = self.model.start_chat(history=self.chat.history)  # Preserve history
            print(f"TopK changed to: {top_k}")
        except Exception as e:
            print(f"Error changing top_k: {e}")

    def change_top_p(self, top_p):
        """
        Changes the TopP of the model.

        Args:
            top_p (float): The new TopP value (must be between 0 and 1).
        """
        if not (0 <= top_p <= 1):
            raise ValueError("TopP must be between 0 and 1.")

        try:
            self.generation_config.top_p = top_p
            self.model = genai.GenerativeModel(self.model_name, generation_config=self.generation_config)
            self.chat = self.model.start_chat(history=self.chat.history)  # Preserve history
            print(f"TopP changed to: {top_p}")
        except Exception as e:
            print(f"Error changing top_p: {e}")

    def max_random(self):
        """
        Sets parameters to maximum randomness.
        """
        try:
            temperature = 1
            top_p = 1
            top_k = 40

            self.generation_config.temperature = temperature
            self.generation_config.top_p = top_p
            self.generation_config.top_k = top_k

            self.model = genai.GenerativeModel(self.model_name, generation_config=self.generation_config)
            self.chat = self.model.start_chat(history=self.chat.history)  # Preserve history

            print("Parameters set to maximum randomness.")
        except Exception as e:
            print(f"Error setting max randomness: {e}")

    def output_chat_history(self):
        for message in self.chat.history:
            print(f'**{message.role}**: {message.parts[0].text}\n')

    def get_last_response(self):
        prev_response = self.chat.history[-1]
        # print("Previous response:", prev_response)
        return prev_response[1].parts[0].text

def start_chat(system_instruction=None):
    chatbot = GeminiChatbot()
    print("Type 'exit' to end the chat.")
    if system_instruction:
        print("Chatbot:", chatbot.send_message(system_instruction))
    while True:
        user_message=input("You: ")
        if user_message.lower() in ['exit', 'quit']:
            chatbot.end_chat()
            break
        elif user_message.lower().startswith("temperature"):
            try:
                temp_value=float(user_message.split()[1])
                chatbot.change_temperature(temp_value)
            except (IndexError, ValueError):
                print("Invalid temperature value.  Use: temperature [0.0-1.0]")
        elif user_message.lower().startswith("topk"):
            try:
                topk_value=int(user_message.split()[1])
                chatbot.change_top_k(topk_value)
            except (IndexError, ValueError):
                print("Invalid TopK value.  Use: topk [integer]")
        elif user_message.lower().startswith("topp"):
            try:
                topp_value=float(user_message.split()[1])
                chatbot.change_top_p(topp_value)
            except (IndexError, ValueError):
                print("Invalid TopP value.  Use: topp [0.0-1.0]")
        elif user_message.lower()=="maxrandom":
            chatbot.max_random()
        elif user_message.lower()=="rewind":
            response = chatbot.get_last_response()
            print("Prev Response:", response)
        else:
            response=chatbot.send_message(user_message)
            print("Chatbot:", response)


def invoke(prompt = "Tell me something funny but not corny.",
           temp=.6,
           top_k=100,
           top_p=0.6,):
    chatbot = GeminiChatbot()
    chatbot.change_temperature(temp)
    chatbot.change_top_k(top_k)
    chatbot.change_top_p(top_p)

    response=chatbot.send_message(prompt)
    print("Gemini:", response)


# Example usage (command-line chatbot):
if __name__ == '__main__':
    invoke(temp=.3, top_p=0)
    # main()