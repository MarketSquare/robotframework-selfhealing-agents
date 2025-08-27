from typing import ClassVar

from SelfhealingAgents.self_healing_system.schemas.internal_state.prompt_payload import PromptPayload
from SelfhealingAgents.self_healing_system.agents.prompts.base_prompt_agent import BasePromptAgent


class PromptsOrchestrator(BasePromptAgent):
    """Orchestrates prompt-based recovery for Robot Framework using tool outputs.

    Provides system and user message generation for smart recovery tooling, ensuring
    that only the raw JSON output from the tool is returned.

    Attributes:
        _system_msg (ClassVar[str]): Class-level system message describing the agent's role and available tools.
    """
    _system_msg: ClassVar[str] = (
        "You are a Robot Framework smart recovery tool and a JSON passthrough machine. Your only job is to return the exact, raw JSON output from a tool.\n"
        "The following tools are available to you:\n"
        "- get_healed_locators: This tool provides locator suggestions for a broken locator.\n\n"
        # "Your task is to call a tool ONCE and return its response in pure JSON format.\n"
        # "Your output must be a character-for-character copy of the tool's output.\n"
        # "DO NOT describe what you did. DO NOT explain the result. DO NOT add any text before or after the JSON.\n\n"
        # "NEVER return the tool call format like {\"name\": \"tool_name\", \"parameters\": {...}}.\n"
        # "ALWAYS return the tool's actual response which looks like {\"suggestions\": [...]}.\n"
    )

    @classmethod
    def get_system_msg(cls):
        """Returns the system message for the orchestrator agent.

        Returns:
            str: The system message string describing the agent's role and available tools.
        """
        return cls._system_msg

    @staticmethod
    def get_user_msg(robot_ctx_payload: PromptPayload) -> str:
        """Assembles the user message (prompt) based on the provided context.

        Args:
            robot_ctx_payload (PromptPayload): The context containing information about the keyword failure.

        Returns:
            str: The assembled user message instructing the tool call for the broken locator.
        """
        return (
            f"Call the 'get_healed_locators' tool for the broken locator: `{robot_ctx_payload.failed_locator}`.\n"
            # "Call the 'get_healed_locators' tool ONCE and return the result as pure JSON.\n"
            # "OUTPUT REQUIREMENT: Return ONLY the tool's response.\n"
            # "DO NOT describe, explain, or add any text.\n"
            # "STOP after you receive the tool's response.\n"
            # "Expected format: {\"suggestions\":[\"locator1\", \"locator2\", \"locator3\"]}"
            # f"Use the 'get_healed_locators' tool ONCE for the failed locator: ```{ctx.failed_locator}``` \n"
            # "After getting the result, return ONLY the tool output in pure JSON format and then STOP. \n"
        )
