*** Settings ***
Library    Browser    timeout=5s
Library    RobotAid    config_path=${CURDIR}/../config_test.yaml
Suite Setup    New Browser    browser=${BROWSER}    headless=${HEADLESS}
Test Setup    New Context    viewport={'width': 1280, 'height': 720}
Test Teardown    Close Context
Suite Teardown    Close Browser    ALL

*** Variables ***
${BROWSER}    chromium
${HEADLESS}    True

*** Test Cases ***
Login with valid credentials
    New Page    https://automationintesting.com/selenium/testpage/
    Set Browser Timeout    1s
    Fill Text    id=first_name    tom
    Fill Text    id=last_name    smith
    Select Options By    id=usergender    label    Male
    Click    id=red
    Fill Text    id=tell_me_more    More information
    Select Options By    id=user_continent    label    Africa
    Click    id=i_do_nothing

Not a broken locator error
    New Page    https://automationintesting.com/selenium/testpage/
    Run Keyword And Expect Error    Text 'First name\\n' (str) should be 'Incorrect Label' (str)    Get Text    label >> text=First Name    ==    Incorrect Label

Self Healing returns value in Getter Keyword
    New Page    https://automationintesting.com/selenium/testpage/
    Fill Text    id=first_name    tom
    ${name}    Get Text    id=first_name
    Should Be Equal    ${name}    tom

Resolve to multiple elements
    New Page    https://automationintesting.com/selenium/testpage/
    Set Browser Timeout    1s
    Fill Text    input    tom

Resolve to wrong element type
    New Page    https://automationintesting.com/selenium/testpage/
    Set Browser Timeout    1s
    Fill Text    button >> text=I do nothing!    tom

