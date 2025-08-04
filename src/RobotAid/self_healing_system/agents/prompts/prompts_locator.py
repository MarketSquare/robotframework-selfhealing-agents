from pydantic_ai import RunContext

from RobotAid.self_healing_system.schemas.prompt_payload import PromptPayload


class PromptsLocator:
    system_msg: str = (
        "You are a xpath and css selector self-healing tool.\n"
        "You will provide a fixed_locator for a failed_locator.\n"
        "Using the elements in the DOM at failure time, suggest 3 new locators.\n"
        "You are also given a list of tried locator suggestions memory that were tried but still failed. "
        "Make sure you do not suggest a locator that is on that list. "
        "IMPORTANT: Respond ONLY with the JSON. Do not include any explanations, analysis, or additional text.\n"
        'ONLY return the JSON in this exact format: {"suggestions": ["locator1", "locator2", "locator3"]}\n'
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

    system_msg_choose_locator: str = (
        "You are a locator selection tool for Robot Framework self-healing.\n"
        "Your task is to choose the best locator from the provided suggestions.\n"
        "You will receive a list of locator suggestions and must select the most appropriate one.\n"
        "Respond ONLY with the JSON. Do not include any explanations, analysis, or additional text.\n"
        'ONLY return the JSON in this exact format: {"suggestions": "locator"}\n'
    )

    @staticmethod
    def get_user_msg_choose_locator(
        ctx: RunContext[PromptPayload], suggestions: list, metadata: list
    ) -> str:
        """Assembles user message (a.k.a. user prompt) for choosing a locator.

        Args:
            ctx (RunContext): PydanticAI context. Contains information about keyword failure.

        Returns:
            (str): Assembled user message (a.k.a. user prompt) for choosing a locator.
        """
        return (
            f"Failed locator: `{ctx.deps.failed_locator}`\n\n"
            f"Keyword name: `{ctx.deps.keyword_name}`\n\n"
            f"Keyword arguments: `{ctx.deps.keyword_args}`\n\n"
            f"Suggestions:\n {suggestions}\n\n"
            f"Metadata:\n {metadata}\n\n"
            f"Tried Locator Suggestion Memory:\n{ctx.deps.tried_locator_memory}\n\n"
        )
