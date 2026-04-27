prompts = {
"default": "Remind me to select the proper text analysis task!",
"list_gen":
    """Instructions
    ---
    Create a list of 10 article headlines for the topic: digital marketing.
    
    Example output
    ---
    - 10 Digital Marketing Strategies
    - That Will Boost Your Business Growth
    - 5 Dos and 10 Don'ts
    - How to Use Influencer Marketing to Reach Your Target Audience
    
    Rules
    ---
    Don't talk about SEO in the article titles
    Also avoid including any references to blogging, or email marketing with the generated headlines:
    ---""",
"sentiment_analysis":
    """You are working as a data analyst for a company that wants to improve customer satisfaction. Your task is to perform sentiment analysis on customer reviews of their product.

    The label must be neutral, negative or positive
    ---
    product review text: This marketing product was a complete waste of time and money. It didn't do anything it promised and the customer service was terrible. I'm very unhappy with the purchase and would not recommend it to anyone.
    sentiment: negative
    product review text: I recently purchased a marketing product from this company and I am so glad I did. The product was exactly what I was looking for, and the customer service was outstanding. The staff was very helpful and knowledgeable and they made sure I got exactly what I needed. I highly recommend this company and their products.
    sentiment: positive
    product review text: 
    This product is an effective marketing tool that is easy to use. It has a lot of features that can help with creating a successful marketing campaign. However, it does have some drawbacks that should be taken into consideration when deciding if it is the right solution for your needs. Overall, the product is worth considering.
    sentiment: neutral
    ---
    product review text:  I recently purchased a marketing product from this company and I am so pleased with the results. The product is easy to use and the customer service team was incredibly helpful. They provided me with clear instructions and answered all my questions. The product has already improved my marketing efforts, and I look forward to seeing even better results in the future.
    sentiment:
    """,
"explain_liam5":
    """Explain the text below like I’m five:
     String Theory.""",
"least_to_most":
    """# Create a list of 3 Disney characters.
    ## For each character, generate a short biography to tell me more about the character.
    """,
"delimited_instruct":
    """"Summarize the text delimited by triple quotes.
    '''{0}'''
    """,
"step_by_step":
    """# Follow these steps:
    ## Step 1: 
    Condense the text enclosed in triple quotes into a single sentence.
    
    ## Step 2: 
    Translate the summarized text into {0}.
    
    # Output format
    Summary: <output from Step 1>.
    {0} Translation: <output from Step 2>
    
    '''{1}'''
    """,
"sb_winner": """Tell me the name of the superbowl winner in 2024.
    """,
"new_prompt": """this is my new prompt....
    """,

}


def fetch_prompt(prompt_key="default", params=None):
    """
    Fetch a prompt by key and format it with optional parameters.

    Args:
        prompt_key (str, optional): The key of the prompt. Defaults to "default".
        params (list, optional): A list of parameters to format the prompt. Defaults to None.

    Returns:
        str: The formatted prompt.

    Raises:
        TypeError: If params is not a list.
    """
    prompt = prompts.get(prompt_key, "default")
    if params is not None:
        if not isinstance(params, list):
            raise TypeError("params must be a list")
        prompt = prompt.format(*params)
    return prompt

def list_prompt_keys():
    for key in prompts:
        print(key)


if __name__ == "__main__":
    # print(fetch_prompt("step_by_step", ['Spanish','HAPPY DATA']))
    # list_prompt_keys()
    # print(fetch_prompt("sb_winner"))
    text='some garbage text is being entered here.'
    prompt=fetch_prompt("delimited_instruct", [text])
    print(prompt)