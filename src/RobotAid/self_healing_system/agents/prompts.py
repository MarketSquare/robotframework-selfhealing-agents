from pydantic_ai import RunContext
from RobotAid.self_healing_system.schemas import PromptPayload


class PromptsOrchestrator:
    system_msg: str = "You are a helpful assistant."
    user_msg: str = "Please call the tool 'locator_heal'."


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
            f"Using the html_ids from the DOM at failure time, suggest 3 new locators as a list of strings.\n\n"
            f"Error message:\n{ctx.deps.error_msg}\n\n"
            f"HTML ids:\n{ctx.deps.html_ids}\n\n"
            f"Keyword call:\n{ctx.deps.robot_code_line}"
        )