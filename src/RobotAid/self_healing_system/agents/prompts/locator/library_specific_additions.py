def get_system_msg_browser(system_msg: str) -> str:
    """Get the Browser library specific system prompt.

    Returns:
        The system prompt containing Browser library specific instructions
        for locator generation and formatting.
    """
    return (
        f"{system_msg}\n"
        "BROWSER LIBRARY SPECIFIC INSTRUCTIONS:\n"
        "- Keywords like 'Fill Text', 'Enter Text' or 'Press Keys'  are always related to 'input' or 'textarea' elements.\n"
        "- Keywords like 'Click' are often  related to 'button','checkbox', 'a' or 'input' elements.\n"
        "- Keywords like 'Select' or 'Deselect' are often related to 'select' elements.\n"
        "- Keywords like 'Check' or 'Uncheck' are often related to 'checkbox' elements.\n"
        "- Prefix CSS selectors with 'css=' \n"
        "- Prefix XPath expressions with 'xpath='\n"
        '- Example response: {"suggestions": ["css=input[id=\'my_id\']", "xpath=//*[contains(text(),\'Login\')]", "css=button:has-text(\'Submit\')"]}\n'
    )


def get_system_msg_selenium(system_msg: str) -> str:
    """Get the Selenium library specific system prompt.

    Returns:
        The system prompt containing Selenium library specific instructions
        for locator generation and formatting.
    """
    return (
        f"{system_msg}\n"
        "SELENIUM LIBRARY SPECIFIC INSTRUCTIONS:\n"
        "- Keywords like 'Input Text', 'Input Password' or 'Press Keys'  are always related to 'input' or 'textarea' elements.\n"
        "- Keywords like 'Click' are often  related to 'button','checkbox', 'a' or 'input' elements.\n"
        "- Keywords like 'Select From List' are often related to 'select' elements.\n"
        "- Keywords like 'Select Checkbox' are often related to 'checkbox' elements.\n"
        "- Prefix CSS selectors with 'css:' \n"
        "- Prefix XPath expressions with 'xpath:'\n"
        '- Example response: {"suggestions": ["css:input[id=\'my_id\']", "xpath://*[contains(text(),\'Login\')]", "css:button:contains(Submit)"]}\n'
    )


# ToDo: implement appium support
def get_system_msg_appium(system_msg: str) -> None:
    """Get the Selenium library specific system prompt.

    Returns:
        The system prompt containing Selenium library specific instructions
        for locator generation and formatting.
    """
    return None