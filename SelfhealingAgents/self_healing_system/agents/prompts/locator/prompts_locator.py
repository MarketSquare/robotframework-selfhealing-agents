from typing import Callable, ClassVar

from pydantic_ai import RunContext

from SelfhealingAgents.self_healing_system.agents.prompts.base_prompt_agent import BasePromptAgent
from SelfhealingAgents.self_healing_system.schemas.internal_state.prompt_payload import PromptPayload
from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import BaseDomUtils
from SelfhealingAgents.self_healing_system.agents.prompts.locator.library_specific_additions import (
    get_system_msg_browser,
    get_system_msg_selenium,
    get_system_msg_appium
)


class PromptsLocatorGenerationAgent(BasePromptAgent):
    """Agent for generating new locator suggestions for self-healing in Robot Framework.

    Provides system and user message generation for suggesting new locators
    when a locator fails, ensuring only unique and untried locators are proposed.

    Attributes:
        _system_msg (ClassVar[str]): Class-level system message describing the agent's role and output format.
        _library_func_mapping_system_msg (dict[str, Callable[[], str]]): Mapping of library types to their system message generator functions.
    """
    _system_msg: ClassVar[str] = (
        "You are a locator/selector self-healing tool.\n"
        "You will provide a fixed_locator for a failed_locator.\n"
        "Using the elements in the DOM at failure time, suggest 3 new locators.\n"
        "You are also given a list of tried locator suggestions memory that were tried but still failed. "
        "Make sure you do not suggest a locator that is on that list. "
        "IMPORTANT: Respond ONLY with the JSON. Do not include any explanations, analysis, or additional text.\n"
        'ONLY return the JSON in this exact format: {"suggestions": ["locator1", "locator2", "locator3"]}\n'
        'Example response: {"suggestions": ["css=input[id=\'my_id\']", "xpath=//*[contains(text(),\'Login\')]", "xpath=//label[contains(text(),\'Speeding\')]/..//input"]}\n'
    )

    _library_func_mapping_system_msg: dict[str, Callable[[], str]] = {
        "browser": get_system_msg_browser,
        "selenium": get_system_msg_selenium,
        "appium": get_system_msg_appium     # Not yet implemented
    }

    @classmethod
    def get_system_msg(cls, dom_utility: BaseDomUtils):
        """Returns the system message for the locator generation agent, customized per library.

        Args:
            dom_utility (BaseDomUtils): The DOM utility instance to determine the library type.

        Returns:
            str: The system message string for the agent.

        Raises:
            ValueError: If the library type is unknown.
        """
        library_type: str = dom_utility.get_library_type()
        func: Callable = cls._library_func_mapping_system_msg.get(library_type)
        if func is None:
            raise ValueError(f"Unknown library: {library_type}")
        return func(cls._system_msg)     # type: ignore

    @staticmethod
    def get_user_msg(ctx: RunContext[PromptPayload]) -> str:
        """Assembles the user message (prompt) for locator generation based on context.

        Args:
            ctx (RunContext): PydanticAI context containing information about the keyword failure.

        Returns:
            str: The assembled user message for locator generation.
        """
        return (
            f"Your suggested locators should be only of type: {ctx.deps.locator_type}. No other types are allowed. \n\n"
            f"Error message: `{ctx.deps.error_msg}`\n\n"
            f"Failed locator: `{ctx.deps.failed_locator}`\n\n"
            f"Keyword name: `{ctx.deps.keyword_name}`\n\n"
            f"Dom Tree: ```{ctx.deps.dom_tree}```\n\n"
            f"Tried Locator Suggestion Memory:\n{ctx.deps.tried_locator_memory}\n\n"
        )


class PromptsLocatorSelectionAgent(BasePromptAgent):
    """Agent for selecting the best locator from a list of suggestions for self-healing.

    Provides system and user message generation for choosing the most appropriate locator
    from a set of suggestions, based on context and metadata.

    Attributes:
        _system_msg (ClassVar[str]): Class-level system message describing the agent's role and output format.
    """
    _system_msg: ClassVar[str] = (
        "You are a locator selection tool for Robot Framework self-healing.\n"
        "Your task is to choose the best locator from the provided suggestions.\n"
        "You will receive a list of locator suggestions and must select the most appropriate one.\n"
        "Respond ONLY with the JSON. Do not include any explanations, analysis, or additional text.\n"
        'ONLY return the JSON in this exact format: {"suggestions": "locator"}\n'
    )

    @classmethod
    def get_system_msg(cls) -> str:
        """Returns the system message for the locator selection agent.

        Returns:
            str: The system message string for the agent.
        """
        return cls._system_msg

    @staticmethod
    def get_user_msg(
        ctx: RunContext[PromptPayload], suggestions: list, metadata: list
    ) -> str:
        """Assembles the user message (prompt) for choosing a locator.

        Args:
            ctx (RunContext): PydanticAI context containing information about the keyword failure.
            suggestions (list): List of locator suggestions to choose from.
            metadata (list): List of metadata dictionaries for each suggestion.

        Returns:
            str: The assembled user message for locator selection.
        """
        return (
            f"Failed locator: `{ctx.deps.failed_locator}`\n\n"
            f"Keyword name: `{ctx.deps.keyword_name}`\n\n"
            f"Keyword arguments: `{ctx.deps.keyword_args}`\n\n"
            f"Suggestions:\n {suggestions}\n\n"
            f"Metadata:\n {metadata}\n\n"
            f"Tried Locator Suggestion Memory:\n{ctx.deps.tried_locator_memory}\n\n"
        )
