from pydantic_ai import RunContext
from RobotAid.self_healing_system.schemas import PromptPayload


class PromptsOrchestrator:
    system_msg: str = (
        # "You fix a broken keyword in a robotframework test."
        #                "If the keyword failed due to a broken locator, call the tool 'locator_heal' "                       
        #             "If the tool locator_heal returns a valid locator (e.g., a valid XPath or CSS selector), do not call the tool again and return the locator as the final output."       
                    "You fix a broken keyword in a Robot Framework test." 
                    "If the keyword failed due to a broken locator, call the tool 'locator_heal'."
                    "When the tool returns a string starting with 'xpath=' or 'css=', return **that exact string** as the final output."
                    "Do not wrap it, do not explain it, do not quote it. Simply return the string. Do not call the tool again."
                    "If the tool returns a string that does not start with 'xpath=' or 'css=' or if the tool returns an error, call the tool again."
    )
    user_msg: str = ("Please call the tool 'locator_heal'. Only respond with the message the tool gave you, do "
                     "not add any additional information in any case.")
    @staticmethod
    def get_user_msg(ctx: PromptPayload) -> str:
        """Assembles user message (a.k.a. user prompt) based on context.

        Args:
            ctx (RunContext): PydanticAI context. Contains information about keyword failure.

        Returns:
            (str): Assembled user message (a.k.a. user prompt) based on context.
        """
        return (
            "Please call the tool 'locator_heal'. Only respond with the message the tool gave you, do "
            "not add any additional information or text in any case."
            # "Example responses: 'xpath=//div[@class=\"example\"]' or 'css=.example-class'"

            # f"Failed locator:\n{ctx.failed_locator}\n\n"

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
        'Respond using the following json schema: {"fixed_locators": ["locator1", "locator2", "locator3", ... ]}.\n'
        'Example: {"fixed_locators": ["css=input[id=\'my_id\']", "xpath=//*[contains(text(),\'Login\')]", "xpath=//label[contains(text(),\'Speeding\')]/..//input", "xpath=//*[contains(@class, \'submitBtn\')]", "css=button.class1.class2"]}\n'
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