from abc import ABC, abstractmethod
from typing import Optional

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.usage import UsageLimits

from RobotAid.self_healing_system.agents.prompts import PromptsLocator
from RobotAid.self_healing_system.clients.llm_client import get_model
from RobotAid.self_healing_system.context_retrieving.base_dom_utils import BaseDomUtils
from RobotAid.self_healing_system.context_retrieving.dom_utility_factory import (
    DomUtilityFactory,
)
from RobotAid.self_healing_system.schemas import LocatorHealingResponse, PromptPayload
from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings


class BaseLocatorAgent(ABC):
    """Abstract base class for locator agents.

    Defines the common interface and shared functionality for all locator agent flavors.

    Attributes:
        app_settings (AppSettings): Instance of AppSettings containing user defined app configuration.
        client_settings (ClientSettings): Instance of ClientSettings containing user defined client configuration.
        usage_limits (UsageLimits): Usage token and request limits.
        dom_utility (Optional[BaseDomUtils]): DOM utility instance for the specific library.
    """

    def __init__(
        self,
        app_settings: AppSettings,
        client_settings: ClientSettings,
        usage_limits: UsageLimits = UsageLimits(
            request_limit=5, total_tokens_limit=2000
        ),
        dom_utility: Optional[BaseDomUtils] = None,
    ) -> None:
        self.usage_limits: UsageLimits = usage_limits
        self.app_settings = app_settings
        self.client_settings = client_settings
        self._provided_dom_utility = dom_utility
        self._dom_utility: Optional[BaseDomUtils] = None

        # Initialize the generation agent with the appropriate system prompt
        self.generation_agent: Agent[PromptPayload, LocatorHealingResponse] = Agent[
            PromptPayload, LocatorHealingResponse
        ](
            model=get_model(
                provider=app_settings.locator_agent.provider,
                model=app_settings.locator_agent.model,
                client_settings=client_settings,
            ),
            system_prompt=self._get_system_prompt(),
            deps_type=PromptPayload,
            output_type=LocatorHealingResponse,
        )

        # Set up output validation
        self._setup_output_validation()

    def _setup_output_validation(self) -> None:
        """Set up output validation for the generation agent."""

        @self.generation_agent.output_validator
        async def validate_output(
            output: LocatorHealingResponse,
        ) -> LocatorHealingResponse:
            """Validates the output of the locator agent.

            Args:
                output (LocatorHealingResponse): Output from the locator agent.

            Returns:
                LocatorHealingResponse: Validated output.
            """
            try:
                # The output is already a LocatorHealingResponse, but we can validate and process locators
                fixed_locators = output.suggestions
                if not fixed_locators:
                    raise ModelRetry("No fixed locators found in the response.")

                # Process and validate locators using flavor-specific logic
                suggestions = [self._process_locator(x) for x in fixed_locators]
                suggestions = self._sort_locators(suggestions)

                if suggestions:
                    return LocatorHealingResponse(suggestions=suggestions)
                raise ModelRetry("None of the fixed locators are valid or unique.")
            except Exception as e:
                raise ModelRetry(f"Invalid locator healing response: {str(e)}") from e

    @property
    def dom_utility(self) -> Optional[BaseDomUtils]:
        """Get the DOM utility instance, creating it lazily if needed.

        Returns:
            Optional[BaseDomUtils]: The DOM utility instance, or None if creation failed.
        """
        if self._dom_utility is None and self._provided_dom_utility is None:
            # Create DOM utility based on agent type
            agent_type = self.get_agent_type()
            self._dom_utility = DomUtilityFactory.create_dom_utility_from_agent_type(
                agent_type
            )
        elif self._provided_dom_utility is not None:
            return self._provided_dom_utility
        return self._dom_utility

    async def heal_async(
        self, ctx: RunContext[PromptPayload]
    ) -> LocatorHealingResponse:
        """Generates suggestions for fixing broken locator.

        Args:
            ctx (RunContext): PydanticAI context.

        Returns:
            LocatorHealingResponse: List of repaired locator suggestions.
        """
        response: AgentRunResult[
            LocatorHealingResponse
        ] = await self.generation_agent.run(
            PromptsLocator.get_user_msg(ctx=ctx),
            deps=ctx.deps,
            usage_limits=self.usage_limits,
            model_settings={"temperature": 0.1},
        )
        if not isinstance(response.output, LocatorHealingResponse):
            raise ModelRetry(
                "Locator healing response is not of type LocatorHealingResponse."
            )
        return response.output

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt specific to this locator agent flavor.

        Returns:
            str: The system prompt for this agent flavor.
        """
        pass

    @abstractmethod
    def _process_locator(self, locator: str) -> str:
        """Process the locator to make it compatible with the target library.

        Args:
            locator (str): The raw locator from the LLM.

        Returns:
            str: The processed locator compatible with the target library.
        """
        pass

    def _is_locator_valid(self, locator: str) -> bool:
        """Check if the locator is valid and unique in the current context.

        Args:
            locator (str): The locator to validate.

        Returns:
            bool: True if the locator is valid and unique, False otherwise.
        """
        if self.dom_utility is None:
            return True
        try:
            return self.dom_utility.is_locator_valid(locator)
        except Exception:
            return False

    @abstractmethod
    def get_agent_type(self) -> str:
        """Get the type identifier for this agent flavor.

        Returns:
            str: The agent type identifier.
        """
        pass

    def _is_locator_unique(self, locator: str) -> bool:
        """Check if the locator is unique in the current context.

        Args:
            locator (str): The locator to check.

        Returns:
            bool: True if the locator is unique, False otherwise.
        """
        if self.dom_utility is None:
            return True
        try:
            return self.dom_utility.is_locator_unique(locator)
        except Exception:
            return False

    def _sort_locators(self, locators: list[str]) -> list[str]:
        """Sort locators based on their uniqueness and validity.

        Args:
            locators (list[str]): List of locators to sort.

        Returns:
            list[str]: Sorted list of locators.
        """
        valid_locators = [loc for loc in locators if self._is_locator_valid(loc)]
        return sorted(
            valid_locators, key=lambda x: self._is_locator_unique(x), reverse=True
        )
