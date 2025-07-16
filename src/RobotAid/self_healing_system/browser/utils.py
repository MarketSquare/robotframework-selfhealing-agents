def convert_locator_to_browser(locator: str) -> str:
    """Converts a locator to a format suitable for Browser Library.
    Replaces
        css: or xpath: with css= or xpath=.
        ":contains" with ":has-text"
        ":-soup-contains-own" with ":text"
        ":-soup-contains" with ":has-text"
    This is used to ensure that the locator is compatible with the Browser Library's expectations.
    All replacements will be performed on the locator string.
    Only the final locator will be returned, no additional text or explanations.

    Args:
        css_selector (str): The CSS selector to convert.

    Returns:
        str: The converted CSS selector.
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
