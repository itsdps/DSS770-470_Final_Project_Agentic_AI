from IPython.display import Markdown, display
import textwrap
import re

def to_markdownx(text):
    if text is None:
        return None
    # Consistent bullet points
    text = re.sub(r'[-•*] ', '* ', text)
    # Remove extra spaces before * in list items after replacement
    text = text.replace(' *', '*')
    # Only indent if not already indented (avoids nested blockquotes)
    if not text.startswith(">"):
        lines = text.split('\n')
        indented_lines = ["> " + line if line.strip() != "" else line for line in lines]
        text = "\n".join(indented_lines)
    return Markdown(text)  # Return the Markdown object

def to_markdown(text):
  text = text.replace('•', '  *')
  return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))

def render_markdown(text):
    text = to_markdown(text)
    display(text)

def replace_tabs(text, num_spaces=4):
    """
    Replace tabs with a specified number of spaces.

    Parameters:
    text (str): The input text.
    num_spaces (int): The number of spaces to replace each tab with. Defaults to 4.

    Returns:
    str: The text with tabs replaced by spaces.
    """
    return text.replace("\t", " " * num_spaces)


def replace_leading_tabs(text, num_spaces=0):
    """
    Replace leading tabs with a specified number of spaces.

    Parameters:
    text (str): The input text.
    num_spaces (int): The number of spaces to replace each tab with. Defaults to 4.

    Returns:
    str: The text with leading tabs replaced by spaces.
    """
    return re.sub(r'^\t+', ' ' * num_spaces, text, flags=re.MULTILINE)

def remove_leading_whitespace(text, num_chars=4):
    """
    Remove a specified number of leading whitespace characters (spaces or tabs) from each line of text.

    Parameters:
    text (str): The input text.
    num_chars (int): The number of leading whitespace characters to remove. Defaults to 4.

    Returns:
    str: The text with the specified number of leading whitespace characters removed.
    """
    lines = text.splitlines()
    modified_lines = [re.sub(r'^\s{' + str(num_chars) + '}', '', line) for line in lines]
    return '\n'.join(modified_lines)

def stream_markdown(llm, prompt):
    """
    Stream llm responses and convert to Markdown.

    :param llm: LLaMA model instance
    :param prompt: Input prompt
    :yield: Markdown formatted chunks
    """
    for chunk in llm.stream(prompt):
        text = chunk.content.replace('•', '  *')
        yield Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))


if __name__ == "__main__":
    # Example usage:
    text_with_tabs = """
    First line\n\tHello\tWorld!\n\tAnother line
    """
    text_without_leading_tabs = remove_leading_whitespace(text_with_tabs, 0)
    print(text_without_leading_tabs)
