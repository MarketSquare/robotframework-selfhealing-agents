# RobotAid - Self-healing for Robot Framework
![banner](./static/github_banner.png)

[![PyPI version](https://img.shields.io/pypi/v/robotframework-selfhealer.svg)](https://pypi.org/project/robotframework-selfhealer/)
![Python versions](https://img.shields.io/pypi/pyversions/robotframework-selfhealer.svg)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](#license)
[![Tests](https://img.shields.io/github/actions/workflow/status/MarketSquare/robot-heal-testbed/ci.yml?branch=main)](https://github.com/MarketSquare/robot-heal-testbed/actions)

A robotframework library that **repairs failing Robot Framework tests automatically** using **Large Language Models
(LLMs)**. It currently heals broken locators, with upcoming releases expanding to additional common failure modes.

---

## ✨ Features
- 🧭 **Heals broken locators** automatically
- ⏱️ **Runtime hooking** keeps tests running after locator fixes
- 📝 **Generates reports** with healing steps, repaired files and diffs
- 🤖 **LLM multi-agent** workflow (extensible for more error types)
- 🌐 **Supports Browser & Selenium** (Appium planned)
- 🔌 Supports **OpenAI, Azure OpenAI, LiteLLM** and pluggable providers
- 🧰 **RF Library** for easy test suite integration
- 🔍 **Monitor your agents with Logfire**

---
## ⚙️ ️Installation
```bash
pip install robotframework-selfhealer
```
---
## 🛠️Setup

All necessary settings must be specified in a `.env` file at the root of the repository.
A minimal `.env` file is all you need to get started with the default settings and OpenAI as the provider:
```env
OPENAI_API_KEY="your-openai-api-key"
```
---
## 🚀 Usage
After installing the package and adding your API key to the `.env` file, simply add the Library `RobotAid` to your test suite.
```
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
    New Page    https://automationintesting.com/selenium/testpage/
    Set Browser Timeout    1s
    Fill Text    id=first_name    tom
    Fill Text    id=last_name    smith
    Select Options By    id=usergender    label    Male
    Click    id=red
    Fill Text    id=tell_me_more    More information
    Select Options By    id=user_continent    label    Africa
    Click    id=i_do_nothing
```

After running your test suite(s), you'll find a "RobotAid" directory in your current working directory containing 
detailed logs and output reports. There are three types of reports generated:
1) **Action Log**: Summarizes all healing steps performed and their locations within your tests
2) **Healed Files**: Provides repaired copies of your test suite(s)
3) **Diff Files**: Shows a side-by-side comparison of the original and healed files, with differences highlighted for easy review

### Action Log
![action_log](./static/action_log.png)

## Healed File
```robotframework
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
    New Page    https://automationintesting.com/selenium/testpage/
    Set Browser Timeout    1s
    Fill Text    css=input[id='firstname']    tom
    Fill Text    css=input[id='surname']    smith
    Select Options By    css=select[id='gender']    label    Male
    Click    id=red
    Fill Text    css=textarea[placeholder='Tell us some fun stuff!']    More information
    Select Options By    css=select#continent    label    Africa
    Click    css=button#submitbutton

```

### Diff File
![diff_file](./static/diff_file.png)

---
## Configuration
Below is an example `.env` file containing all available parameters:

```env
OPENAI_API_KEY="your-openai-api-key"
LITELLM_API_KEY="your-litellm-api-key"
AZURE_API_KEY="your-azure-api-key"
AZURE_API_VERSION="your-azure-api-version"
AZURE_ENDPOINT="your-azure-endpoint"
BASE_URL="your-base-url"

ENABLE_SELF_HEALING=True
USE_LLM_FOR_LOCATOR_GENERATION=True
MAX_RETRIES=3
REQUEST_LIMIT=5
TOTAL_TOKENS_LIMIT=6000
ORCHESTRATOR_AGENT_PROVIDER="openai"
ORCHESTRATOR_AGENT_MODEL="gpt-4o-mini"
LOCATOR_AGENT_PROVIDER="openai"
LOCATOR_AGENT_MODEL="gpt-4o-mini"
```

### 📝 Configuration Parameters

| Name                          | Default         | Required?                | Description                                                               |
|-------------------------------|-----------------|--------------------------|---------------------------------------------------------------------------|
| **OPENAI_API_KEY**            | `None`          | If using OpenAI          | Your OpenAI API key                                                       |
| **LITELLM_API_KEY**           | `None`          | If using LiteLLM         | Your LiteLLM API key                                                      |
| **AZURE_API_KEY**             | `None`          | If using Azure           | Your Azure OpenAI API key                                                 |
| **AZURE_API_VERSION**         | `None`          | If using Azure           | Azure OpenAI API version                                                  |
| **AZURE_ENDPOINT**            | `None`          | If using Azure           | Azure OpenAI endpoint                                                     |
| **BASE_URL**                  | `None`          | No                       | Base URL for your provider (if required)                                  |
| **ENABLE_SELF_HEALING**       | `True`          | No                       | Enable or disable RobotAid                                                |
| **USE_LLM_FOR_LOCATOR_GENERATION** | `True`    | No                       | If `True`, LLM generates locator suggestions directly (see note below)    |
| **MAX_RETRIES**               | `3`             | No                       | Number of self-healing attempts per locator                               |
| **REQUEST_LIMIT**             | `5`             | No                       | Internal agent-level limit for valid LLM response attempts                |
| **TOTAL_TOKENS_LIMIT**        | `6000`          | No                       | Maximum input tokens per LLM request                                      |
| **ORCHESTRATOR_AGENT_PROVIDER** | `"openai"`    | No                       | Provider for the orchestrator agent (`"openai"`, `"azure"` or `"litellm"`) |
| **ORCHESTRATOR_AGENT_MODEL**  | `"gpt-4o-mini"` | No                       | Model for the orchestrator agent                                          |
| **LOCATOR_AGENT_PROVIDER**    | `"openai"`      | No                       | Provider for the locator agent (`"openai"`, `"azure"` or `"litellm"`)     |
| **LOCATOR_AGENT_MODEL**       | `"gpt-4o-mini"` | No                       | Model for the locator agent                                               |

> **Note:**  
> Locator suggestions can be generated either by assembling strings from the DOM tree (with an LLM selecting the best option), or by having the LLM generate suggestions directly itself with the context given (DOM included). Set `USE_LLM_FOR_LOCATOR_GENERATION` to `True` to enable direct LLM generation.

## 🔮 Outlook

While RobotAid currently focuses on healing broken locators, its architecture is designed for much more. The introduced 
multi-agent system provides a modular and extensible foundation for integration of additional agents, each specialized 
in healing different types of test failures.

Upcoming releases will expand beyond locator healing, allowing for the multi-agent framework to automatically repair a 
broader range of common test errors, making your Robot Framework suites even more resilient with minimal manual 
intervention. So stay tuned!