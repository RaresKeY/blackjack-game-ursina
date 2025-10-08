import re
from typing import Callable


def vinput(prompt: str, pattern: str = None, condition: Callable[[str], bool] = None) -> str: # type: ignore
    """
    Prompt until input matches optional regex and condition.

    Args:
        prompt: Text shown to the user.
        pattern: Regex the input must match, if provided.
        condition: Function that takes the input and returns True if valid.

    Returns:
        The valid input string.
    """
    while True:
        text = input(prompt)
        if pattern and not re.fullmatch(pattern, text):
            print("Invalid format, try again.")
            continue
        if condition and not condition(text):
            print("Condition not met, try again.")
            continue
        return text


def is_valid_e164(number: str) -> bool:
    """
    Validate if a phone number is in E.164 format.

    Rules:
      - Must start with '+'
      - Country code cannot start with 0
      - Total length: 8 to 15 digits (including country code)
      - No spaces, dashes, or extra characters
    """
    return bool(re.fullmatch(r"\+[1-9]\d{7,14}", number))