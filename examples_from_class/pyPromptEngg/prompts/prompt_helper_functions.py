def fetch_prompt(prompt_dict, prompt_key="default", params=None):
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
    prompt = prompt_dict.get(prompt_key, "default")
    if params is not None:
        if not isinstance(params, list):
            raise TypeError("params must be a list")
        prompt = prompt.format(*params)
    return prompt

def list_prompt_keys(prompt_dict):
    for key in prompt_dict:
        print(key)

if __name__ == "__main__":
    # print(fetch_prompt("step_by_step", ['Spanish','HAPPY DATA']))
    # list_prompt_keys()
    print(fetch_prompt("sb_winner"))