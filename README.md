# Robot Framework Selfhealing Agents
![banner](./static/github_banner.png)

[![PyPI version](https://img.shields.io/pypi/v/robotframework-selfhealing-agents.svg)](https://pypi.org/project/robotframework-selfhealing-agents/)
![Python versions](https://img.shields.io/pypi/pyversions/robotframework-selfhealing-agents.svg)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](#license)

A robotframework library that **repairs failing Robot Framework tests automatically** using **Large Language Models
(LLMs)**. It currently heals broken locators, with upcoming releases expanding to additional common failure modes.

**Note:** This repository does not collect or store any user data. However, when using LLMs, 
data privacy cannot be fully guaranteed by this repository alone. If you are working with sensitive information, 
ensure you use a trusted provider and/or connect to a secure endpoint that enforces data privacy and prevents your 
data from being used for model training. \
The repository is designed to be flexible, allowing you to integrate different providers and/or add custom endpoints as needed.

---

## ✨ Features
- 🧭 **Heals broken locators** automatically
- 📂 Supports test suites with external **resource files**
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
pip install robotframework-selfhealing-agents
```
---
## 🛠️Setup

To configure the project, create a .env file in the root directory of the repository. This file should contain all required environment variables for your chosen LLM provider.

### Minimal Example (OpenAI)
For a quick start with the default settings and OpenAI as the provider, your `.env` file only needs:
```env
OPENAI_API_KEY="your-openai-api-key"
```
### Custom Endpoint
If you need to use a custom endpoint (for example, for compliance or privacy reasons), add the BASE_URL variable:
```env
OPENAI_API_KEY="your-openai-api-key"
BASE_URL="your-endpoint-to-connect-to"
```
### Azure OpenAI Example
To use Azure as your LLM provider, specify the following variables:
```env
AZURE_API_KEY="your-azure-api-key"
AZURE_API_VERSION="your-azure-api-version"
AZURE_ENDPOINT="your-azure-endpoint"

ORCHESTRATOR_AGENT_PROVIDER="azure"
LOCATOR_AGENT_PROVIDER="azure"
```
### LiteLLM Example
To use LiteLLM as your LLM provider, specify the following variables:
```env
LITELLM_API_KEY="your-litellm-api-key"
BASE_URL="your-endpoint-to-connect-to"

ORCHESTRATOR_AGENT_PROVIDER="litellm"
LOCATOR_AGENT_PROVIDER="litellm"
```
These minimal examples demonstrate how to run the project with different providers using the default settings. For more details on available configuration options (such as selecting a specific model) please refer to the "Configuration" section.

---
## 🚀 Usage
After installing the package and adding your necessary parameters to the `.env` file, simply add the Library `SelfhealingAgents` to your test suite(s).
```robotframework
*** Settings ***
Library    Browser    timeout=5s
Library    SelfhealingAgents
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

After running your test suite(s), you'll find a "SelfHealingReports" directory in your current working directory containing 
detailed logs and output reports. There are three types of reports generated:
1) **Action Log**: Summarizes all healing steps performed and their locations within your tests
2) **Healed Files**: Provides repaired copies of your test suite(s)
3) **Diff Files**: Shows a side-by-side comparison of the original and healed files, with differences highlighted for easy review
4) **Summary**: A json summary file for a quick overview of number of healing steps and files affected etc. 

### Action Log
![action_log](./static/action_log.png)

### Healed File
```robotframework
*** Settings ***
Library    Browser    timeout=5s
Library    SelfhealingAgents
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

### Summary json
```json
{
  "total_healing_events": 6,
  "nr_affected_tests": 1,
  "nr_affected_files": 1,
  "affected_tests": [
    "Login with valid credentials"
  ],
  "affected_files": [
    "ait.robot"
  ]
}
```

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
ORCHESTRATOR_AGENT_TEMPERATURE=0.1
LOCATOR_AGENT_PROVIDER="openai"
LOCATOR_AGENT_MODEL="gpt-4o-mini"
LOCATOR_AGNET_TEMPERATURE=0.1
LOCATOR_TYPE="css"
```

### 📝 Configuration Parameters

| Name                               | Default        | Required?                | Description                                                                |
|------------------------------------|----------------|--------------------------|----------------------------------------------------------------------------|
| **OPENAI_API_KEY**                 | `None`         | If using OpenAI          | Your OpenAI API key                                                        |
| **LITELLM_API_KEY**                | `None`         | If using LiteLLM         | Your LiteLLM API key                                                       |
| **AZURE_API_KEY**                  | `None`         | If using Azure           | Your Azure OpenAI API key                                                  |
| **AZURE_API_VERSION**              | `None`         | If using Azure           | Azure OpenAI API version                                                   |
| **AZURE_ENDPOINT**                 | `None`         | If using Azure           | Azure OpenAI endpoint                                                      |
| **BASE_URL**                       | `None`         | No                       | Endpoint to connect to (if required)                                       |
| **ENABLE_SELF_HEALING**            | `True`         | No                       | Enable or disable SelfhealingAgents                                        |
| **USE_LLM_FOR_LOCATOR_GENERATION** | `True`         | No                       | If `True`, LLM generates locator suggestions directly (see note below)     |
| **MAX_RETRIES**                    | `3`            | No                       | Number of self-healing attempts per locator                                |
| **REQUEST_LIMIT**                  | `5`            | No                       | Internal agent-level limit for valid LLM response attempts                 |
| **TOTAL_TOKENS_LIMIT**             | `6000`         | No                       | Maximum input tokens per LLM request                                       |
| **ORCHESTRATOR_AGENT_PROVIDER**    | `"openai"`     | No                       | Provider for the orchestrator agent (`"openai"`, `"azure"` or `"litellm"`) |
| **ORCHESTRATOR_AGENT_MODEL**       | `"gpt-4o-mini"` | No                       | Model for the orchestrator agent                                           |
| **ORCHESTRATOR_AGENT_TEMPERATURE** | `0.1`          | No                       | Orchestrator model temperature.                                            |
| **LOCATOR_AGENT_PROVIDER**         | `"openai"`     | No                       | Provider for the locator agent (`"openai"`, `"azure"` or `"litellm"`)      |
| **LOCATOR_AGENT_MODEL**            | `"gpt-4o-mini"` | No                       | Model for the locator agent                                                |
| **LOCATOR_AGENT_TEMPERATURE**      | `0.1`          | No                       | Locator model temperature.                                                 |
| **LOCATOR_TYPE**                   | `"css"`        | No                       | Restricts the locator suggestions of the agent to the given type           |

> **Note:**  
> Locator suggestions can be generated either by assembling strings from the DOM tree (with an LLM selecting the best option), or by having the LLM generate suggestions directly itself with the context given (DOM included). Set `USE_LLM_FOR_LOCATOR_GENERATION` to `True` to enable direct LLM generation (default is True).

## 🔮 Outlook

While SelfhealingAgents currently focuses on healing broken locators, its architecture is designed for much more. The introduced 
multi-agent system provides a modular and extensible foundation for integration of additional agents, each specialized 
in healing different types of test failures.

Upcoming releases will expand beyond locator healing, allowing for the multi-agent framework to automatically repair a 
broader range of common test errors, making your Robot Framework suites even more resilient with minimal manual 
intervention. So stay tuned!