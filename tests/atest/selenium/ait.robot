*** Settings ***
Library    SeleniumLibrary
Library    RobotAid    config_path=${CURDIR}/../config_test.yaml
Test Setup    Open Browser    browser=headlesschrome
Test Teardown    Close All Browsers
Test Tags    not_ready

*** Variables ***
${BROWSER}    chromium

*** Test Cases ***
Login with valid credentials
    Go To    https://automationintesting.com/selenium/testpage/
    Set Selenium Timeout    1s
    Input Text    id:first_name    tom
    Input Text    id:last_name    smith
    Select From List By Label    id:usergender    Male
    Click Element    id:red
    Input Text    id:tell_me_more    More information
    Select From List By Label    id:user_continent    Africa
    Click Element    id:i_do_nothing