from src.openai_client import Chat
import time
import random


def bot_to_bot_chat(bot1_initial_prompt, bot2_initial_prompt, max_iterations=20, max_retries=3, bot1_model="gpt-4o", bot2_model="gpt-4o-mini"):
    bot1=Chat(model_name=bot1_model)
    bot2=Chat(model_name=bot2_model, system_instruction=bot2_initial_prompt)

    def delay_response(bot, prompt, max_retries=max_retries):
        retries=0
        response=bot.send_message(prompt)
        while retries<max_retries and response is None:
            seconds=round(random.uniform(1, 2), 2)
            print(f"Delaying for {seconds} seconds...")
            retries+=1
            time.sleep(seconds)
            response=bot.send_message(prompt)
        return response

    i=0
    b1_response=bot1.send_message(bot1_initial_prompt)
    while i<max_iterations:
        i+=1
        print(f"TUTOR/> ({bot1.model_name}) /???> {b1_response}")

        b2_response=delay_response(bot2, b1_response)
        print(f"STUDENT/> ({bot2.model_name}) /~~~> {b2_response}")

        if "bye" in b1_response.lower():
            print("#"*25, "END: B2B CONVERSATION", "#"*25)
            break

        b1_response=delay_response(bot1, b2_response)


if __name__ == "__main__":
    # Example: Simple debate between two bots
    bot1_prompt = "You are arguing that remote work is better. be brief and concise."
    bot2_prompt = "You are arguing that office work is better. be brief and concise."
    
    print('\n' + '#'*25 + " START: B2B CONVERSATION " + "#"*25)
    bot_to_bot_chat(
        bot1_initial_prompt="Which is better: remote work or office work?",
        bot2_initial_prompt=bot2_prompt,
        max_iterations=5,
        max_retries=3
    )