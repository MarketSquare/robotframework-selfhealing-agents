from abc import ABC, abstractmethod
from typing import Optional

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.usage import UsageLimits
from robot.api import logger

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.agents.prompts.locator.prompts_locator import (
    PromptsLocatorGenerationAgent,
    PromptsLocatorSelectionAgent
)
from RobotAid.self_healing_system.llm.client_model import get_client_model
from RobotAid.self_healing_system.context_retrieving.frameworks.base_dom_utils import BaseDomUtils
from RobotAid.self_healing_system.schemas.internal_state.prompt_payload import PromptPayload
from RobotAid.self_healing_system.schemas.api.locator_healing import LocatorHealingResponse


class BaseLocatorAgent(ABC):
    """Abstract base class for locator agents.

    Defines the common interface and shared functionality for all locator agent flavors.

    Attributes:
        cfg: Instance of Cfg config class containing user defined app configuration.
        usage_limits: Usage token and request limits.
        dom_utility: DOM utility instance for the specific library.
    """
    # TODO: Request limit, token limit to .env, optional default keep with current values
    def __init__(
        self,
        cfg: Cfg,
        dom_utility: BaseDomUtils
    ) -> None:
        """Initialize the BaseLocatorAgent.

        Args:
            cfg: Instance of Cfg config class containing user defined app configuration.
            usage_limits: Token and request limits for the agent. Defaults to
                UsageLimits with request_limit=5 and total_tokens_limit=2000.
            dom_utility: Optional DOM utility instance for validation.
        """
        self.cfg = cfg
        self.usage_limits: UsageLimits = UsageLimits(cfg.request_limit, cfg.total_tokens_limit)
        self._dom_utility: BaseDomUtils = dom_utility
        self.use_llm_for_locator_generation = cfg.use_llm_for_locator_generation

        # Initialize agent attributes
        self.generation_agent: Optional[
            Agent[PromptPayload, LocatorHealingResponse]
        ] = None
        self.selection_agent: Optional[Agent[PromptPayload, str]] = None

        # Only create LLM agent if LLM generation is enabled
        if self.use_llm_for_locator_generation:
            self.generation_agent = Agent[PromptPayload, LocatorHealingResponse](
                model=get_client_model(
                    provider=cfg.locator_agent_provider,
                    model=cfg.locator_agent_model,
                    cfg=cfg,
                ),
                system_prompt=PromptsLocatorGenerationAgent.get_system_msg(self._dom_utility),
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
        """Set up output validation for the generation agent.

        Configures the output validator that processes and validates
        the locator healing response from the LLM.
        """
        if self.generation_agent is None:
            return

        @self.generation_agent.output_validator
        async def validate_output(
            ctx: RunContext[PromptPayload],
            output: LocatorHealingResponse,
        ) -> LocatorHealingResponse:
            """Validates the output of the locator agent.

            Args:
                output: Output from the locator agent.

            Returns:
                Validated output with processed and sorted locators.

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
                    logger.info(
                        f"Filtering clickable locators for keyword '{keyword_name}'",
                        also_console=True,
                    )
                    logger.info(
                        f"Locators before filtering: {suggestions}",
                        also_console=True,
                    )
                    suggestions = self._filter_clickable_locators(suggestions)
                    logger.info(
                        f"Locators after filtering: {suggestions}",
                        also_console=True,
                    )

                if suggestions:
                    return LocatorHealingResponse(suggestions=suggestions)
                raise ModelRetry("None of the fixed locators are valid or unique.")
            except Exception as e:
                raise ModelRetry(f"Invalid locator healing response: {str(e)}") from e

    async def heal_async(
        self, ctx: RunContext[PromptPayload]
    ) -> LocatorHealingResponse | str:
        """Generates suggestions for fixing broken locator.

        Args:
            ctx: PydanticAI context containing the prompt payload.

        Returns:
            List of repaired locator suggestions.

        Raises:
            ModelRetry: If the response is not of the expected type.
        """
        if self.use_llm_for_locator_generation:
            return await self._heal_with_llm(ctx)
        else:
            return await self._heal_with_dom_utils(ctx)

    async def _heal_with_llm(
        self, ctx: RunContext[PromptPayload]
    ) -> LocatorHealingResponse:
        """Generate locator suggestions using LLM approach."""
        response: AgentRunResult[
            LocatorHealingResponse
        ] = await self.generation_agent.run(
            PromptsLocatorGenerationAgent.get_user_msg(ctx=ctx),
            deps=ctx.deps,
            usage_limits=self.usage_limits,
            model_settings={"temperature": 0.1},
        )
        if not isinstance(response.output, LocatorHealingResponse):
            raise ModelRetry(
                "Locator healing response is not of type LocatorHealingResponse."
            )
        return response.output

    async def _heal_with_dom_utils(
        self, ctx: RunContext[PromptPayload]
    ) -> LocatorHealingResponse:
        """Generate locator suggestions using DOM utilities approach."""
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
                logger.info(
                    f"Filtering clickable locators for keyword '{keyword_name}'",
                    also_console=True,
                )
                logger.info(
                    f"Locators before filtering: {sorted_proposals}",
                    also_console=True,
                )
                sorted_proposals = self._filter_clickable_locators(sorted_proposals)
                logger.info(
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
                usage_limits=self.usage_limits,
                model_settings={"temperature": 0.1},
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
        """Process the locator to make it compatible with the target library.

        Args:
            locator: The raw locator from the LLM.

        Returns:
            The processed locator compatible with the target library.
        """
        pass

    def _is_locator_valid(self, locator: str) -> bool:
        """Check if the locator is valid and unique in the current context.

        Args:
            locator: The locator to validate.

        Returns:
            True if the locator is valid and unique, False otherwise.
        """
        try:
            return self._dom_utility.is_locator_valid(locator)
        except Exception:
            return False

    def _is_locator_unique(self, locator: str) -> bool:
        """Check if the locator is unique in the current context.

        Args:
            locator: The locator to check.

        Returns:
            True if the locator is unique, False otherwise.
        """
        try:
            return self._dom_utility.is_locator_unique(locator)
        except Exception:
            return False

    def _is_element_clickable(self, locator: str) -> bool:
        """Check if the element identified by the locator is clickable.

        Args:
            locator: The locator to check.

        Returns:
            True if the element is clickable, False otherwise.
        """
        try:
            return self._dom_utility.is_element_clickable(locator)
        except Exception:
            return False

    def _sort_locators(self, locators: list[str]) -> list[str]:
        """Sort locators based on their uniqueness and validity.

        Args:
            locators: List of locators to sort.

        Returns:
            Sorted list of locators with unique locators first.
        """
        valid_locators = [loc for loc in locators if self._is_locator_valid(loc)]
        return sorted(
            valid_locators, key=lambda x: self._is_locator_unique(x), reverse=True
        )

    def _filter_clickable_locators(self, locators: list[str]) -> list[str]:
        """Filter locators to only include clickable ones.

        Args:
            locators: List of locators to filter.

        Returns:
            List of locators that are clickable.
        """
        return [loc for loc in locators if self._is_element_clickable(loc)]

    @staticmethod
    @abstractmethod
    def is_failed_locator_error(message: str) -> bool:
        """Check if the locator error is due to a failed locator.

        Args:
            message: The error message to check.

        Returns:
            True if the error is due to a failed locator, False otherwise.
        """
        pass
