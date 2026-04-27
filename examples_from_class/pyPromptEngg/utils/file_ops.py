import json

def save_to_json(data_dict:dict=None, file_name: str='./data/exported_data.json') -> None:
    print(f"Saving JSON file '{file_name}'...")
    with open(file_name, 'w') as f:
        json.dump(data_dict, f, indent=4)

def save_to_text(text: str, file_name: str = 'prompt.txt', folder_name: str = './data/') -> None:
    """
    Saves the given text to a file.

    Args:
        text (str): The text to be saved.
        folder_name (str, optional): The folder where the file will be saved. Defaults to './data/'.
        file_name (str, optional): The name of the file. Defaults to 'prompt.txt'.

    Returns:
        None

    Raises:
        TypeError: If text is not a string.
        ValueError: If foldername or filename is empty.
        OSError: If there is an error creating the folder or writing to the file.
    """
    import os

    # Check if text is a string
    if not isinstance(text, str):
        raise TypeError("Text must be a string.")

    # Check if foldername and filename are not empty
    if not folder_name:
        raise ValueError("Foldername cannot be empty.")
    if not file_name:
        raise ValueError("Filename cannot be empty.")

    try:
        # Create the folder if it doesn't exist
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        # Save the text to the file
        with open(os.path.join(folder_name, file_name), 'w') as file:
            file.write(text)
        print(f"Text saved to '{os.path.join(folder_name, file_name)}'")
    except OSError as e:
        raise OSError(f"Error saving to file: {e}")


if __name__ == "__main__":
    fn='test1.txt'
    prompt = "What's the distance to the moon?"
    save_to_text(text=prompt, file_name=fn)
