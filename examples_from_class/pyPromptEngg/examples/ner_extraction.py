from src.openai_client import generate_text


def ner(text):
    prompt = f"""
    You will be provided with text delimited by triple tildas.
    Using name entity recognition (NER) capabilities, \
    extract the entities in the text in the following format:
    Item 1: ...
    Item 2: ...
    ...
    Item N: ...
    
    If the text does not contain entities, then simply write \
    <No Entities Found!>
    ~~~{text}~~~ 
    """
    return generate_text(prompt)

text = f"""
As we celebrate our 60th year, I am pleased to share the success of Comcast, 
marking the best financial performance in our history. Growth and innovation 
remain central to our DNA, and our strong 2023 results were fueled by six key areas: 
Residential Broadband, Business Services, Mobile, Streaming, Theme Parks, and our Film 
and Television Studios...
"""

# t = 'hello there.'
# Source: https://comcastcorp.sharepoint.com/sites/ComcastNow/SitePages/Our-2023-Letter-to-Shareholders.aspx
print(ner(text))