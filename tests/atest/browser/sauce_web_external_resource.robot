*** Settings ***
Library    Browser    timeout=5s
Library    SelfhealingAgents
Resource    ./resources/sauce_web_vars.resource
Resource    ./resources/sauce_web_keywords.resource
Suite Setup    New Browser    browser=${BROWSER}    headless=${HEADLESS}
Test Setup    New Context    viewport={'width': 1280, 'height': 720}
Test Teardown    Close Context
Suite Teardown    Close Browser    ALL
Test Tags    not_ready

*** Variables ***
${BROWSER}    chromium
${HEADLESS}    True

*** Test Cases ***
Login with valid credentials
    New Page    https://www.saucedemo.com/
    Fill Text    ${username}    standard_user
    Fill Text    id=pass    secret_sauce
    Click    ${loginbtn}
    Get Url    ==    https://www.saucedemo.com/inventory.html

Add Product To Cart
    Login
    Click    ${adding_cart}
    Get Text    shopping_cart      ==    1

*** Variables ***
${adding_cart}     Sauce Labs Onesie >> Add To Cart
