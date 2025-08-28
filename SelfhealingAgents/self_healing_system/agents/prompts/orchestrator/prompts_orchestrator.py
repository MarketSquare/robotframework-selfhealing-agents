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
        )
