from pydantic_ai import RunContext
from RobotAid.self_healing_system.schemas import PromptPayload


class PromptsOrchestrator:
    system_msg: str = "You are a helpful assistant."
    user_msg: str = ("Please call the tool 'locator_heal'. Only respond with the message the tool gave you, do "
                     "not add any additional information in any case.")


class PromptsLocator:
    system_msg: str = "You are a helpful assistant for fixing broken locators in the context of robotframework tests."

    @staticmethod
    def get_user_msg(ctx: RunContext[PromptPayload]) -> str:
        """Assembles user message (a.k.a. user prompt) based on context.

        Args:
            ctx (RunContext): PydanticAI context. Contains information about keyword failure.

        Returns:
            (str): Assembled user message (a.k.a. user prompt) based on context.
        """
        return (
            f"You are given a Robot Framework keyword that failed due to an inaccessible locator. "
            f"Using the elements in the DOM at failure time, suggest 3 new locators. "
            f"You are also given a list of tried locator suggestions memory that were tried but still failed. "
            f"Make sure you do not suggest a locator that is on that list. "
            f"Note: Only respond with the locators, do not give any additional information in any case.\n\n"
            f"Error message:\n{ctx.deps.error_msg}\n\n"
            f"Dom Tree:\n{ctx.deps.dom_tree}\n\n"
            f"Keyword call:\n{ctx.deps.robot_code_line}\n\n"
            f"Tried Locator Suggestion Memory:\n{ctx.deps.tried_locator_memory}\n\n"
        )