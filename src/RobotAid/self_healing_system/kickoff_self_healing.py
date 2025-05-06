import asyncio

from RobotAid.self_healing_system.schemas import LocatorHealingResponse
from RobotAid.self_healing_system.agents.locator_agent import LocatorAgent
from RobotAid.self_healing_system.agents.orchestrator_agent import OrchestratorAgent


# - This is the core setup class to instantiate the multi-agent system and call the orchestrator - context missing.
# - Also, the returned locators are not handled yet.
# - Orchestrator agent is implemented for showcase reasons, not directly needed for MVP for locator fix.
def kickoff_healing(llm_provider: str) -> None:
    locator_agent: LocatorAgent = LocatorAgent(llm_provider=llm_provider)
    orchestrator_agent: OrchestratorAgent = OrchestratorAgent(locator_agent=locator_agent,
                                                              llm_provider=llm_provider)

    tmp_test_prompt: str = """
Test Suite:

*** Settings ***
Library    Browser    timeout=5s
Library    RobotAid
Suite Setup    New Browser    browser=${BROWSER}    headless=${HEADLESS}
Test Setup    New Context    viewport={'width': 1280, 'height': 720}
Test Teardown    Close Context
Suite Teardown    Close Browser    ALL

*** Variables ***
${BROWSER}    chromium
${HEADLESS}    True

*** Test Cases ***
Login with valid credentials
    New Page    https://www.saucedemo.com/
    Fill Text    id=user    standard_user
    Fill Text    id=pass    secret_sauce
    Click    id=loginbutton
    Get Url    ==    https://www.saucedemo.com/inventory.html

Add Product To Cart
    Login
    Click    Sauce Labs Onesie >> Add To Cart
    Get Text    shopping_cart    ==    1


*** Keywords ***
Login
    New Page    https://www.saucedemo.com/
    Fill Text    broken_locator    standard_user
    Fill Text    css=input#password    secret_sauce
    Click    css=input#login-button
    Get Url    ==    https://www.saucedemo.com/inventory.html

*** Variables ***
broken_locator    css=input#user-naming


HTML IDs found on website during failure:
id=user
id=pass
css=input#password
css=input#user-name

Error message:
Timeout error due to locator not available.
    """

    suggestions: LocatorHealingResponse = asyncio.run(
        orchestrator_agent.run_async(
            tmp_test_prompt
        )
    )
    print('Suggestions:', suggestions.suggestions)


if __name__ == '__main__':
    kickoff_healing(llm_provider="azure")