def get_system_msg_browser(system_msg: str) -> str:
    """Returns the Browser library-specific system prompt for locator generation.

    Appends Browser library-specific instructions to the provided base system message,
    including keyword-element associations and selector prefixing.

    Args:
        system_msg (str): The base system message to extend.

    Returns:
        str: The system prompt containing Browser library-specific instructions
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
    """Returns the Selenium library-specific system prompt for locator generation.

    Appends Selenium library-specific instructions to the provided base system message,
    including keyword-element associations and selector prefixing.

    Args:
        system_msg (str): The base system message to extend.

    Returns:
        str: The system prompt containing Selenium library-specific instructions
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


def get_system_msg_appium(system_msg: str) -> str:
    """Returns the Appium library-specific system prompt for locator generation.

    Adds guidance for mobile locators. Only XPath and accessibility/resource-id
    strategies are valid; CSS selectors are not applicable in Appium.

    Args:
        system_msg (str): The base system message to extend.

    Returns:
        str: Appium-specific instructions for locator generation and formatting.
    """
    return (
        f"{system_msg}\n"
        "APPIUM LIBRARY SPECIFIC INSTRUCTIONS:\n"
        "- Output only XPath or accessibility/resource-id based locators.\n"
        "- Prefer attributes that are stable on mobile:\n"
        "  ANDROID: @resource-id, @content-desc, @text, @class\n"
        "  iOS: @name, @label, @value, XCUI element type\n"
        "- Do NOT use CSS selectors.\n"
        "- Examples (Android):\n"
        "  xpath=//*[@resource-id='com.app:id/username']\n"
        "  //*[contains(@content-desc,'login')]\n"
        "  //android.widget.Button[@text='LOGIN']\n"
        "- Examples (iOS):\n"
        "  //XCUIElementTypeTextField[@name='username']\n"
        "  //*[contains(@label,'Submit')]\n"
        "Example response: {\"suggestions\": [\"//*[@resource-id='com.app:id/btn']\", \"//*[contains(@content-desc,'submit')]\", \"//XCUIElementTypeButton[@label='Submit']\"]}\n"
    )
