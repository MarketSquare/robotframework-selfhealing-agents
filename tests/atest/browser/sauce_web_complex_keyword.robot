*** Settings ***
Library    Browser    timeout=5s
Library    RobotAid
Resource    ./resources/sauce_web_vars.resource
Resource    ./resources/sauce_web_keywords.resource
Suite Setup    New Browser    browser=${BROWSER}    headless=${HEADLESS}
Test Setup    New Context    viewport={'width': 1280, 'height': 720}
Test Teardown    Close Context
Suite Teardown    Close Browser    ALL
Test Tags    not_ready


*** Test Cases ***
Add Product To Cart With Btn
    LoginLocal    id=pwd  1   standard_user   css=log-button    https://www.saucedemo.com/inventory.html
    Click    ${adding_cart}
    Get Text    shopping_cart      ==    1

Add Product To Cart No Btn
    LoginLocalNoBtn    id=pwd  1   standard_user    https://www.saucedemo.com/inventory.html
    Click    ${adding_cart}
    Get Text    shopping_cart      ==    1

*** Keywords ***
LoginLocal
    [Arguments]
    ...  ${password}
    ...  ${distractor}
    ...  ${text_usrname}
    ...  ${button}
    ...  ${url}
    New Page    https://www.saucedemo.com/
    Fill Text    ${username}    ${text_usrname}
    Fill Text    ${password}    secret_sauce
    Sublogin    ${button}    ${url}

Sublogin
    [Arguments]
    ...  ${button}
    ...  ${url}
    Fill Text    id=pwd    secret_sauce
    Subsublogin    ${button}
    Get Url    ==    ${url}

LoginLocalNoBtn
    [Arguments]
    ...  ${password}
    ...  ${distractor}
    ...  ${text_usrname}
    ...  ${url}
    New Page    https://www.saucedemo.com/
    Fill Text    ${username}    ${text_usrname}
    Fill Text    ${password}    secret_sauce
    SubloginNoBtn    ${url}

SubloginNoBtn
    [Arguments]
    ...  ${url}
    Fill Text    id=pwd    secret_sauce
    SubsubloginNoBtn
    Get Url    ==    ${url}

*** Variables ***
${adding_cart}     Sauce Labs Onesie >> Add To Cart
${BROWSER}    chromium
${HEADLESS}    True
