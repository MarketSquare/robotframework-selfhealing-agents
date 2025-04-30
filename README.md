# RobotAid - Self-healing for Robot Framework

A Robot Framework listener library that provides self-healing capabilities for your test automation. RobotAid helps you:

- Fix broken locators during test execution
- Suggest fixes for changed/missing steps after test failures
- Generate healing reports to help maintain your test suite

## Features

- Mid-execution healing for broken locators
- Post-execution analysis and fix suggestions
- LLM-based intelligent healing strategies
- Configurable retry policies
- Easy integration with existing Robot Framework tests

## Installation

```bash
pip install robotframework-aid
```

## Usage

```robot
*** Settings ***
Library    RobotAid
```	

