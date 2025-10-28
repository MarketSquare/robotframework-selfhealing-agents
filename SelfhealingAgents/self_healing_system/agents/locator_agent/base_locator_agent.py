from abc import ABC, abstractmethod
from typing import Optional

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.usage import UsageLimits
from robot.api import logger as rf_logger

from SelfhealingAgents.self_healing_system.agents.prompts.locator.prompts_locator import (
    PromptsLocatorGenerationAgent,
    PromptsLocatorSelectionAgent,
)
from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import (
    BaseDomUtils,
)
from SelfhealingAgents.self_healing_system.llm.client_model import get_client_model
from SelfhealingAgents.self_healing_system.schemas.api.locator_healing import (
    LocatorHealingResponse,
)
from SelfhealingAgents.self_healing_system.schemas.internal_state.prompt_payload import (
    PromptPayload,
)
from SelfhealingAgents.utils.cfg import Cfg
from SelfhealingAgents.utils.logging import log


class BaseLocatorAgent(ABC):
    """Abstract base class for locator agents.

    Defines the common interface and shared functionality for all locator agent flavors.

    Attributes:
        _cfg (Cfg): An instance of the Cfg config class containing user-defined application configuration.
        _usage_limits (UsageLimits): Usage token and request limits.
        _dom_utility (BaseDomUtils): DOM utility instance for the specific library.
        _use_llm_for_locator_generation (bool): Whether to use LLM for locator generation.
        generation_agent (Optional[Agent[PromptPayload, LocatorHealingResponse]]): Agent for LLM-based locator
                                                                                   generation.
        selection_agent (Optional[Agent[PromptPayload, str]]): Agent for DOM-based locator selection.
    """

    def __init__(self, cfg: Cfg, dom_utility: BaseDomUtils) -> None:
        """Initializes the BaseLocatorAgent.

        Args:
            cfg (Cfg): Instance of Cfg config class containing user-defined app configuration.
            dom_utility (BaseDomUtils): DOM utility instance for validation.
        """
        self._cfg = cfg
        self._usage_limits: UsageLimits = UsageLimits(
            request_limit=cfg.request_limit, total_tokens_limit=cfg.total_tokens_limit
        )
        self._dom_utility: BaseDomUtils = dom_utility
        self._use_llm_for_locator_generation = cfg.use_llm_for_locator_generation

        # Initialize agent attributes
        self.generation_agent: Optional[
            Agent[PromptPayload, LocatorHealingResponse]
        ] = None
        self.selection_agent: Optional[Agent[PromptPayload, str]] = None

        # Only create LLM agent if LLM generation is enabled
        if self._use_llm_for_locator_generation:
            self.generation_agent = Agent[PromptPayload, LocatorHealingResponse](
                model=get_client_model(
                    provider=cfg.locator_agent_provider,
                    model=cfg.locator_agent_model,
                    cfg=cfg,
                ),
                system_prompt=PromptsLocatorGenerationAgent.get_system_msg(
                    self._dom_utility
                ),
                deps_type=PromptPayload,
                output_type=LocatorHealingResponse,
            )

            # Set up output validation
            self._setup_output_validation()
        else:
            # For DOM-based approach, create an agent for choosing between locators
            self.selection_agent = Agent[PromptPayload, str](
                model=get_client_model(
                    provider=cfg.locator_agent_provider,
                    model=cfg.locator_agent_model,
                    cfg=cfg,
                ),
                system_prompt=PromptsLocatorSelectionAgent.get_system_msg(),
                deps_type=PromptPayload,
                output_type=str,
            )

    def _setup_output_validation(self) -> None:
        """Sets up output validation for the generation agent.

        Configures the output validator that processes and validates the locator healing response from the LLM.
        """
        if self.generation_agent is None:
            return

        @self.generation_agent.output_validator
        @log
        async def validate_output(
            ctx: RunContext[PromptPayload],
            output: LocatorHealingResponse,
        ) -> LocatorHealingResponse:
            """Validates the output of the locator agent.

            Args:
                ctx (RunContext[PromptPayload]): The tool context.
                output (LocatorHealingResponse): Output from the locator agent.

            Returns:
                LocatorHealingResponse: Validated output with processed and sorted locators.

            Raises:
                ModelRetry: If the output is invalid or contains no valid locators.
            """
            try:
                # The output is already a LocatorHealingResponse, but we can validate and process locators
                fixed_locators = output.suggestions
                if not fixed_locators:
                    raise ModelRetry("No fixed locators found in the response.")

                suggestions = [self._process_locator(x) for x in fixed_locators]
                suggestions = self._sort_locators(suggestions)

                # Filter out non-clickable locators if deps.ct
                keyword_name = ctx.deps.keyword_name
                clickable_keywords = [
                    "click",
                    "click with options",
                    "select options by",
                    "deselect options",
                    "tap",
                    "check checkbox",
                    "uncheck checkbox",
                    "checkbox",
                    "double click",
                    "get list items",
                    "get selected list",
                    "list selection",
                    "list should have",
                    "mouse down",
                    "contain button",
                    "contain link",
                    "contain list",
                    "contain checkbox",
                    "contain radio button",
                    "radio button should",
                    "select checkbox",
                    "select all from list",
                    "select from list by",
                    "select radio button",
                    "unselect from list by",
                    "unselect radio button",
                    "unselect checkbox",
                ]
                if keyword_name and any(
                    keyword in keyword_name.lower() for keyword in clickable_keywords
                ):
                    rf_logger.info(
                        f"Filtering clickable locators for keyword '{keyword_name}'",
                        also_console=True,
                    )
                    rf_logger.info(
                        f"Locators before filtering: {suggestions}",
                        also_console=True,
                    )
                    suggestions = self._filter_clickable_locators(suggestions)
                    rf_logger.info(
                        f"Locators after filtering: {suggestions}",
                        also_console=True,
                    )

                if suggestions:
                    return LocatorHealingResponse(suggestions=suggestions)
                raise ModelRetry("None of the fixed locators are valid or unique.")
            except Exception as e:
                raise ModelRetry(f"Invalid locator healing response: {str(e)}") from e

    @log
    async def heal_async(
        self, ctx: RunContext[PromptPayload]
    ) -> LocatorHealingResponse | str:
        """Generates suggestions for fixing a broken locator.

        Args:
            ctx (RunContext[PromptPayload]): PydanticAI context containing the prompt payload.

        Returns:
            LocatorHealingResponse | str: List of repaired locator suggestions.

        Raises:
            ModelRetry: If the response is not of the expected type.
        """
        if self._use_llm_for_locator_generation:
            return await self._heal_with_llm(ctx)
        else:
            return await self._heal_with_dom_utils(ctx)

    @log
    async def _heal_with_llm(
        self, ctx: RunContext[PromptPayload]
    ) -> LocatorHealingResponse:
        """Generates locator suggestions using the LLM approach.

        Args:
            ctx (RunContext[PromptPayload]): PydanticAI context containing the prompt payload.

        Returns:
            LocatorHealingResponse: List of repaired locator suggestions.

        Raises:
            ModelRetry: If the response is not of the expected type.
        """
        response: AgentRunResult[
            LocatorHealingResponse
        ] = await self.generation_agent.run(
            PromptsLocatorGenerationAgent.get_user_msg(ctx),
            deps=ctx.deps,
            usage_limits=self._usage_limits,
            model_settings={"temperature": self._cfg.locator_agent_temperature},
        )
        if not isinstance(response.output, LocatorHealingResponse):
            raise ModelRetry(
                "Locator healing response is not of type LocatorHealingResponse."
            )
        return response.output

    @log
    async def _heal_with_dom_utils(
        self, ctx: RunContext[PromptPayload]
    ) -> LocatorHealingResponse:
        """Generates locator suggestions using DOM utilities approach.

        Args:
            ctx (RunContext[PromptPayload]): PydanticAI context containing the prompt payload.

        Returns:
            LocatorHealingResponse: List of repaired locator suggestions.

        Raises:
            ModelRetry: If locator proposals cannot be generated or selection fails.
        """
        try:
            failed_locator = ctx.deps.failed_locator
            keyword_name = ctx.deps.keyword_name

            metadata_list = []

            proposals = self._dom_utility.get_locator_proposals(
                failed_locator, keyword_name
            )

            if not proposals:
                raise ModelRetry("No locator proposals could be generated from DOM")

            # Process locators for library compatibility
            processed_proposals = [self._process_locator(loc) for loc in proposals]

            # Sort and filter locators
            sorted_proposals = self._sort_locators(processed_proposals)

            # Filter clickable locators if needed for click-related keywords
            clickable_keywords = [
                "click",
                "click with options",
                "select options by",
                "deselect options",
                "tap",
                "check checkbox",
                "uncheck checkbox",
                "checkbox",
                "double click",
                "get list items",
                "get selected list",
                "list selection",
                "list should have",
                "mouse down",
                "contain button",
                "contain link",
                "contain list",
                "contain checkbox",
                "contain radio button",
                "radio button should",
                "select checkbox",
                "select all from list",
                "select from list by",
                "select radio button",
                "unselect from list by",
                "unselect radio button",
                "unselect checkbox",
            ]
            if keyword_name and any(
                keyword in keyword_name.lower() for keyword in clickable_keywords
            ):
                rf_logger.info(
                    f"Filtering clickable locators for keyword '{keyword_name}'",
                    also_console=True,
                )
                rf_logger.info(
                    f"Locators before filtering: {sorted_proposals}",
                    also_console=True,
                )
                sorted_proposals = self._filter_clickable_locators(sorted_proposals)
                rf_logger.info(
                    f"Locators after filtering: {sorted_proposals}",
                    also_console=True,
                )

            for loc in sorted_proposals:
                # Log each proposal for debugging
                metadata = self._dom_utility.get_locator_metadata(loc)
                metadata_list.append(metadata[0] if metadata else {})

            response: AgentRunResult[str] = await self.selection_agent.run(
                user_prompt=PromptsLocatorSelectionAgent.get_user_msg(
                    ctx=ctx,
                    suggestions=sorted_proposals,
                    metadata=metadata_list,
                ),
                deps=ctx.deps,
                usage_limits=self._usage_limits,
                model_settings={"temperature": self._cfg.locator_agent_temperature},
            )

            # Parse the selected locator from the response
            if isinstance(response.output, str):
                import json

                try:
                    parsed_response = json.loads(response.output)
                    if (
                        isinstance(parsed_response, dict)
                        and "suggestions" in parsed_response
                    ):
                        selected_locator = parsed_response["suggestions"]
                    else:
                        # Fallback: use the raw response
                        selected_locator = response.output.strip()
                except json.JSONDecodeError:
                    # Fallback: use the raw response
                    selected_locator = response.output.strip()

                # Return as LocatorHealingResponse with the single selected locator
                return LocatorHealingResponse(suggestions=[selected_locator])

            raise ModelRetry("Selection response is not a valid string.")
        except Exception as e:
            raise ModelRetry(f"DOM-based locator generation failed: {str(e)}")

    @abstractmethod
    def _process_locator(self, locator: str) -> str:
        """Processes the locator to make it compatible with the target library.

        Args:
            locator (str): The raw locator from the LLM.

        Returns:
            str: The processed locator compatible with the target library.
        """
        pass

    def _is_locator_valid(self, locator: str) -> bool:
        """Checks if the locator is valid and unique in the current context.

        Args:
            locator (str): The locator to validate.

        Returns:
            bool: True if the locator is valid and unique, False otherwise.
        """
        try:
            return self._dom_utility.is_locator_valid(locator)
        except Exception:
            return False

    def _is_locator_unique(self, locator: str) -> bool:
        """Checks if the locator is unique in the current context.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the locator is unique, False otherwise.
        """
        try:
            return self._dom_utility.is_locator_unique(locator)
        except Exception:
            return False

    def _is_element_clickable(self, locator: str) -> bool:
        """Checks if the element identified by the locator is clickable.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the element is clickable, False otherwise.
        """
        try:
            return self._dom_utility.is_element_clickable(locator)
        except Exception:
            return False

    def _sort_locators(self, locators: list[str]) -> list[str]:
        """Sorts locators based on their uniqueness and validity.

        Args:
            locators (list[str]): List of locators to sort.

        Returns:
            list[str]: Sorted list of locators with unique locators first.
        """
        valid_locators = [loc for loc in locators if self._is_locator_valid(loc)]
        return sorted(
            valid_locators, key=lambda x: self._is_locator_unique(x), reverse=True
        )

    def _filter_clickable_locators(self, locators: list[str]) -> list[str]:
        """Filters locators to only include clickable ones.

        Args:
            locators (list[str]): List of locators to filter.

        Returns:
            list[str]: List of locators that are clickable.
        """
        return [loc for loc in locators if self._is_element_clickable(loc)]

    @staticmethod
    @abstractmethod
    def is_failed_locator_error(message: str) -> bool:
        """Checks if the locator error is due to a failed locator.

        Args:
            message (str): The error message to check.

        Returns:
            bool: True if the error is due to a failed locator, False otherwise.
        """
        pass
