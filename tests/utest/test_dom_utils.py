import Browser
import pytest
from RobotAid.self_healing_system.dom_utils import RobotDomUtils

@pytest.fixture()
def browser(tmpdir):
    Browser.Browser._output_dir = tmpdir
    browser = Browser.Browser()
    yield browser
    browser.close_browser("ALL")


def test_is_locator_unique(browser):
    dom_utils = RobotDomUtils(library_instance=browser)
    browser.new_page("https://playwright.dev/")

    locator = "h1"
    result = dom_utils.is_locator_unique(locator)
    
    # Assert: The locator should be unique
    assert result is True, f"Locator '{locator}' should be unique but was not."   

def test_is_locator_not_unique(browser):
    dom_utils = RobotDomUtils(library_instance=browser)
    browser.new_page("https://playwright.dev/")

    locator = "div"
    result = dom_utils.is_locator_unique(locator)
    
    # Assert: The locator should not be unique
    assert result is False, f"Locator '{locator}' should not be unique but was."

def test_is_locator_visible(browser):
    dom_utils = RobotDomUtils(library_instance=browser)
    browser.new_page("https://playwright.dev/")

    locator = "h1"
    result = dom_utils.is_locator_visible(locator)
    
    # Assert: The locator should be visible
    assert result is True, f"Locator '{locator}' should be visible but was not."