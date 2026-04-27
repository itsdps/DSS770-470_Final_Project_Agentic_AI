PROD_EXAMPLES = """
    Product description: a refrigerator that dispenses soda
    Product names:iCoolFridge, iRefreshingSoda, iSeekSoda
    
    Product description: a watch that tells daily horoscopes
    Product names: iLuckWatch, iPredictWatch, iStars
    
    Product description: a car mug warmer
    Product names: iKeepWarm, iMakeHot, iCarMug
    ---
"""

def simple_prompt():
    return "Generate a list of 10 product names for vacuum cleaner."

def product_prompt_template(product_description, num=3, famous_inventor='Walt Disney', product_examples=PROD_EXAMPLES):
    prompt_template = f"""
    Brainstorm a list of {num} product names for a {product_description}, in the style of {famous_inventor}.
    Use the provided examples for guidance.
    
    ## Output format
    Return the results as a comma separated list, in this format:
    Product description: {product_description}
    Product names: [list of {num} product names]
    
    ## Examples
    {product_examples}
    """
    return prompt_template

def rate_products_prompt(product_info):

    prompt_template = f"""
    # Given the product info
    {product_info}
    ## Instructions
    Rate the product names based on their catchiness, uniqueness, and simplicity. Rate them on a scale from 1-5, with 5 being the highest score.
    ## Output format
    Respond only with a markdown table containing the results.
    """
    return prompt_template


if __name__ == '__main__':
    print(product_prompt_template('Diecase car.'))