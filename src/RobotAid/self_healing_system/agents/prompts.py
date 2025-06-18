from pydantic_ai import RunContext
from RobotAid.self_healing_system.schemas import PromptPayload
from RobotAid.self_healing_system.schemas import LocatorHealingResponse

class PromptsOrchestrator:
    system_msg: str = (
        "You are a Robot Framework smart recovery tool and a JSON passthrough machine. Your only job is to return the exact, raw JSON output from a tool.\n"
        
        "The following tools are available to you:\n"
        "- get_healed_locators: This tool provides locator suggestions for a broken locator.\n\n"
        
        "Your task is to call a tool ONCE and return its response in pure JSON format.\n"
        "Your output must be a character-for-character copy of the tool's output.\n"
        "DO NOT describe what you did. DO NOT explain the result. DO NOT add any text before or after the JSON.\n\n"
        "NEVER return the tool call format like {\"name\": \"tool_name\", \"parameters\": {...}}.\n"
        "ALWAYS return the tool's actual response which looks like {\"suggestions\": [...]}.\n"
    )
    user_msg: str = ("Return pure JSON. No explanations.")
    @staticmethod
    def get_user_msg(ctx: PromptPayload) -> str:
        """Assembles user message (a.k.a. user prompt) based on context.

        Args:
            ctx (RunContext): PydanticAI context. Contains information about keyword failure.

        Returns:
            (str): Assembled user message (a.k.a. user prompt) based on context.        """
        return (
             f"Call the 'get_healed_locators' tool for the broken locator: `{ctx.failed_locator}`.\n"


            # "Call the 'get_healed_locators' tool ONCE and return the result as pure JSON.\n"
            # "OUTPUT REQUIREMENT: Return ONLY the tool's response.\n"
            # "DO NOT describe, explain, or add any text.\n"
            # "STOP after you receive the tool's response.\n"
            # "Expected format: {\"suggestions\":[\"locator1\", \"locator2\", \"locator3\"]}"
            # f"Use the 'get_healed_locators' tool ONCE for the failed locator: ```{ctx.failed_locator}``` \n"
            # "After getting the result, return ONLY the tool output in pure JSON format and then STOP. \n"
        )

class PromptsLocator:
    system_msg: str = (
        "You are a xpath and css selector self-healing tool.\n"
        "You will provide a fixed_locator for a failed_locator.\n"
        "Using the elements in the DOM at failure time, suggest 3 new locators.\n"
        "You are also given a list of tried locator suggestions memory that were tried but still failed. "
        "Make sure you do not suggest a locator that is on that list. "
        "Keywords like 'Fill Text', 'Enter Text' or 'Press Keys'  are always related to 'input' or 'textarea' elements.\n"
        "Keywords like 'Click' are often  related to 'button','checkbox', 'a' or 'input' elements.\n"
        "Keywords like 'Select' or 'Deselect' are often related to 'select' elements.\n"
        "Keywords like 'Check' or 'Uncheck' are often related to 'checkbox' elements.\n"
        "When the 'fixed_locator' is an xpath, always add a xpath= prefix to the locator.\n"
        "When the 'fixed_locator' is an css selector, always add a css= prefix to the locator.\n"
        "IMPORTANT: Respond ONLY with the JSON. Do not include any explanations, analysis, or additional text.\n"
        "ONLY return the JSON in this exact format: {\"suggestions\": [\"locator1\", \"locator2\", \"locator3\"]}\n"
        'Example response: {"suggestions": ["css=input[id=\'my_id\']", "xpath=//*[contains(text(),\'Login\')]", "xpath=//label[contains(text(),\'Speeding\')]/..//input"]}\n'
    )

    @staticmethod
    def get_user_msg(ctx: RunContext[PromptPayload]) -> str:
        """Assembles user message (a.k.a. user prompt) based on context.

        Args:
            ctx (RunContext): PydanticAI context. Contains information about keyword failure.

        Returns:
            (str): Assembled user message (a.k.a. user prompt) based on context.
        """
        return (
            
            f"Error message: `{ctx.deps.error_msg}`\n\n"
            f"Failed locator: `{ctx.deps.failed_locator}`\n\n"
            f"Keyword name: `{ctx.deps.keyword_name}`\n\n"            
            f"Dom Tree: ```{ctx.deps.dom_tree}```\n\n"
            f"Tried Locator Suggestion Memory:\n{ctx.deps.tried_locator_memory}\n\n"
        )