import re
from typing import Any
from json import JSONDecodeError, JSONDecoder

from robot.api import logger


def extract_json_objects(text: str, decoder: JSONDecoder = JSONDecoder()) -> Any:
    """Extracts JSON objects or arrays from a text string, handling common LLM formatting issues.

    This function attempts to parse one or more JSON objects or arrays from the input text.
    It fixes common formatting issues such as single quotes, trailing commas, and newlines
    that are often introduced by large language models (LLMs).

    If the text contains a single JSON object or array, it is returned directly as a dict or list.
    If multiple top-level objects or arrays are found, a list of these objects is returned.
    If no valid JSON is found, returns None.

    Args:
        text: The input string potentially containing JSON objects or arrays.
        decoder: An optional JSONDecoder instance to use for decoding.

    Returns:
        A dict, list, or list of dicts/lists if multiple objects are found, or None if no valid JSON is found.
    """
    # Attempt to fix common LLM issues: single quotes, trailing commas, etc.
    def fix_json_string(s: str) -> str:
        s = s.strip()
        # If the string starts and ends with single quotes, replace them with double quotes
        if s.startswith("'") and s.endswith("'"):
            s = '"' + s[1:-1] + '"'
        # Replace single quotes with double quotes, but not inside already double-quoted strings
        s = re.sub(r'(?<!")\'(?!")', '"', s)
        # Unescape inner single quotes in double-quoted strings
        s = s.replace('\\"', '"').replace("\\'", "'")
        # Remove trailing commas before closing brackets/braces
        s = re.sub(r",([\s\n]*[\]\}])", r"\1", s)
        # Remove newlines between brackets/braces
        s = re.sub(r"([\[\{])\s*\n+\s*", r"\1", s)
        s = re.sub(r"\s*\n+\s*([\]\}])", r"\1", s)
        return s

    pos = 0
    text = text.strip()
    results = []
    while pos < len(text):
        # Find the next JSON object or array
        match_obj = text.find("{", pos)
        match_arr = text.find("[", pos)
        if match_obj == -1 and match_arr == -1:
            break
        if match_obj == -1 or (match_arr != -1 and match_arr < match_obj):
            match = match_arr
        else:
            match = match_obj
        original = text[match:]
        try:
            result, index = decoder.raw_decode(original)
            results.append(result)
            pos = match + index
        except (ValueError, JSONDecodeError):
            try:
                fixed = fix_json_string(original)
                result, index = decoder.raw_decode(fixed)
                results.append(result)
                pos = match + index
            except (ValueError, JSONDecodeError):
                pos = match + 1
                continue
    if not results:
        return None
    if len(results) == 1:
        return results[0]
    return results


def convert_response_to_list(response: str) -> list:
    """Converts a JSON response string to a list of strings.

    Attempts to extract JSON data from the response string and convert it to a list of strings.
    If the extracted data is a list, each item is converted to a string. If the data is not a list,
    all items are converted to strings and returned as a list. Returns an empty list on error.

    Args:
        response: The JSON response string.

    Returns:
        A list of strings extracted from the JSON response, or an empty list if extraction fails.
    """
    try:
        json_data = list(extract_json_objects(response))
        if not json_data:
            return []
        # If the first item is a list, flatten it
        if isinstance(json_data[0], list):
            return [str(item) for item in json_data[0]]
        # Otherwise, return all items as strings
        return [str(item) for item in json_data]
    except Exception as e:
        logger.error(f"Error converting response to list: {e}")
        return []


def convert_response_to_dict(response: str) -> dict:
    """Converts a JSON response string to a dictionary.

    Attempts to extract a JSON object from the response string and return it as a dictionary.
    If the extracted data is not a dictionary, logs an error and returns an empty dictionary.

    Args:
        response: The JSON response string.

    Returns:
        A dictionary extracted from the JSON response, or an empty dictionary if extraction fails.
    """
    try:
        json_data = extract_json_objects(response)
        if isinstance(json_data, dict):
            return json_data
        else:
            logger.error("Response is not a valid JSON object.")
            return {}
    except Exception as e:
        logger.error(f"Error converting response to dict: {e}")
        return {}


def convert_locator_to_browser(locator: str) -> str:
    """Converts a locator string to a format compatible with the Browser Library.

    This function replaces prefixes and patterns in the locator string to ensure compatibility
    with the Browser Library. Specifically, it replaces:
      - 'css:' or 'xpath:' with 'css=' or 'xpath='
      - ':contains' with ':has-text'
      - ':-soup-contains-own' with ':text'
      - ':-soup-contains' with ':has-text'

    All replacements are performed on the locator string, and only the final locator is returned.

    Args:
        locator: The locator string to convert.

    Returns:
        The converted locator string compatible with the Browser Library.
    """
    locator = locator.strip()
    if locator.startswith("css:"):
        locator = "css=" + locator[4:]
    elif locator.startswith("xpath:"):
        locator = "xpath=" + locator[6:]

    locator = locator.replace(":contains", ":has-text")
    locator = locator.replace(":-soup-contains-own", ":text")
    locator = locator.replace(":-soup-contains", ":has-text")

    return locator
