*** Settings ***
Library    SeleniumLibrary
Library    SelfhealingAgents
Test Setup    Open Browser    browser=${BROWSER}
Test Teardown    Close All Browsers

*** Variables ***
${BROWSER}    headlesschrome

*** Test Cases ***
Create Quote for Car
    Open Insurance Application
    Enter Vehicle Data for Automobile
    Check Entered Vehicle Data

*** Keywords ***
Open Insurance Application
    Set Selenium Timeout    30
    Set Window Size    1280    720
    Go To    http://sampleapp.tricentis.com/

Enter Vehicle Data for Automobile
    Click Element    div.main-navigation >> "Automobile"
    Set Selenium Timeout    1
    Select From List By Label    Brand    Audi
    Input Text    engine    110
    Input Text    manufactoringdate    06/12/1980
    Select From List By Label    seats    5
    Select From List By Label    fueltype    Petrol    
    Input Text    price    30000
    Input Text   licenseplate    DEF1234
    Input Text   mileage   10000

Check Entered Vehicle Data
    List Selection Should Be   Brand    Audi
    Textfield Should Contain    engine    110
    Textfield Should Contain    manufactoringdate    06/12/1980
    List Selection Should Be    seats    5
    List Selection Should Be    fueltype    Petrol    
    Textfield Should Contain    price    30000
    Textfield Should Contain    licenseplate    DEF1234
    Textfield Should Contain    mileage   10000
    
Enter Insurant Data
    [Arguments]    ${firstname}=Max    ${lastname}=Mustermann
    Input Text    id=firstname    Max
    Input Text    id=lastname    Mustermann
    Input Text    id=birthdate    01/31/1980
    Select Checkbox    *css=label >> id=gendermale
    Input Text    id=streetaddress    Test Street
    Select From List By Label    id=country    Germany
    Input Text    id=zipcode    40123
    Input Text    id=city    Essen
    Select From List By Label    id=occupation    Employee
    Click Element    text=Cliff Diving
    Click Element    section[style="display: block;"] >> text=Next »

Enter Product Data
    Input Text    id=startdate    06/01/2025
    Select From List By Label    id=insurancesum    7.000.000,00
    Select From List By Label    id=meritrating    Bonus 1
    Select From List By Label    id=damageinsurance    No Coverage
    Select Checkbox    *css=label >> id=EuroProtection
    Select From List By Label    id=courtesycar    Yes
    Click Element    section[style="display: block;"] >> text=Next »

Select Price Option
    [Arguments]    ${price_option}=Silver
    Click Element    *css=label >> css=[value=${price_option}]
    Click Element    section[style="display: block;"] >> text=Next »

Send Quote
    Input Text    "E-Mail" >> .. >> input    max.mustermann@example.com
    Input Text    "Phone" >> .. >> input    0049201123456
    Input Text    "Username" >> .. >> input    max.mustermann
    Input Text    "Password" >> .. >> input    SecretPassword123!
    Input Text    "Confirm Password" >> .. >> input    SecretPassword123!
    Input Text    "Comments" >> .. >> textarea    Some comments
    Click Element    "« Send »"
    Wait Until Element Is Visible    "Sending e-mail success!"
    Click Element    "OK"