*** Settings ***
Resource    ./sauce_web_vars.resource

*** Keywords ***
Login
    New Page    https://www.saucedemo.com/
    Fill Text    ${username}    standard_user
    Fill Text    id=pwd    secret_sauce
    Click    css=input#login-button
    Get Url    ==    https://www.saucedemo.com/inventory.html