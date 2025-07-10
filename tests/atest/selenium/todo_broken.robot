*** Settings ***
Library    SeleniumLibrary
Library    RobotAid    config_path=${CURDIR}/../config_test.yaml
Test Setup    Open Browser    browser=${BROWSER}
Test Teardown    Close All Browsers

*** Variables ***
${BROWSER}    headlesschrome

*** Test Cases ***
Add Two ToDos And Check Items
    [Documentation]    Checks if ToDos can be added and ToDo count increases
    [Tags]    Add ToDo
    Given ToDo App is open
    When I Add A New ToDo "Learn Robot Framework"
    And I Add A New ToDo "Write Test Cases"
    Then Open ToDos should show "2 items left!"

Add ToDo And Mark Same ToDo
    [Tags]    Mark ToDo
    Given ToDo App is open
    When I Add A New ToDo "Learn Robot Framework"
    And I Mark ToDo "Learn Robot Framework"
    Then Open ToDos should show "0 items left!"

Add Two ToDo And Mark ToDos
    [Tags]    Mark ToDo
    Given ToDo App is open
    When I Add A New ToDo "Learn Robot Framework"
    Then Open ToDos should show "1 item left!"
    When I Add A New ToDo "Write Tests"
    Then Open ToDos should show "2 items left!"
    When I Mark ToDo "Write Tests"
    And I Mark ToDo "Learn Robot Framework"
    Then Open ToDos should show "0 items left!"

*** Keywords ***
ToDo App is open
    Set Window Size    1280    720
    Go To    https://todomvc.com/examples/react/dist/

I Add A New ToDo "${todo}"   
    Input Text  .todo  ${todo}
    Press Keys  .todo  RETURN
    
Open ToDos should show "${text}"
    Element Text Should Be    span.todo-count    ${text}

I Mark ToDo "${todo}"
    Click Element    input.toggle >> "${todo}" 