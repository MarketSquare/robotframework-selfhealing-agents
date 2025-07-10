from abc import ABC, abstractmethod
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.usage import UsageLimits

from RobotAid.self_healing_system.agents.prompts import PromptsLocator
from RobotAid.self_healing_system.clients.llm_client import get_model
from RobotAid.utils.reponse_converters import convert_response_to_dict
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
    """

    def __init__(
        self,
        app_settings: AppSettings,
        client_settings: ClientSettings,
        usage_limits: UsageLimits = UsageLimits(
            request_limit=5, total_tokens_limit=2000
        ),
    ) -> None:
        self.usage_limits: UsageLimits = usage_limits
        self.app_settings = app_settings
        self.client_settings = client_settings

        self.generation_agent: Agent[PromptPayload, str] = Agent[PromptPayload, str](
            model=get_model(
                provider=app_settings.locator_agent.provider,
                model=app_settings.locator_agent.model,
                client_settings=client_settings,
            ),
            system_prompt=self._get_system_prompt(),
            deps_type=PromptPayload,
            output_type=str,
        )

        @self.generation_agent.output_validator
        def validate_output(ctx: RunContext[PromptPayload], output: str) -> str:
            """Validates the output of the locator agent.

            Args:
                output (str): Output from the locator agent.

            Returns:
                (str): Validated output.
            """
            try:
                locator_dict = convert_response_to_dict(output)
                fixed_locators = locator_dict.get("suggestions", [])
                if not fixed_locators:
                    raise ModelRetry("No fixed locators found in the response.")

                suggestions = []
                for locator in fixed_locators:
                    processed_locator = self._process_locator(locator)
                    if self._is_locator_valid(processed_locator):
                        suggestions.append(processed_locator)

                if suggestions:
                    return LocatorHealingResponse(
                        suggestions=suggestions
                    ).model_dump_json()
                raise ModelRetry("None of the fixed locators are valid or unique.")
            except Exception as e:
                raise ModelRetry(
                    f"Invalid output format: {str(e)}. Expected format: {{'suggestions': ['locator1', 'locator2', ...]}}"
                ) from e

    async def heal_async(self, ctx: RunContext[PromptPayload]) -> str:
        """Generates suggestions for fixing broken locator.

        Args:
            ctx (RunContext): PydanticAI context.

        Returns:
            (str): List of repaired locator suggestions.
        """
        response: AgentRunResult = await self.generation_agent.run(
            PromptsLocator.get_user_msg(ctx=ctx),
            deps=ctx.deps,
            usage_limits=self.usage_limits,
            model_settings={"temperature": 0.1},
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

    @abstractmethod
    def _is_locator_valid(self, locator: str) -> bool:
        """Check if the locator is valid and unique in the current context.

        Args:
            locator (str): The locator to validate.

        Returns:
            bool: True if the locator is valid and unique, False otherwise.
        """
        pass

    @abstractmethod
    def get_agent_type(self) -> str:
        """Get the type identifier for this agent flavor.

        Returns:
            str: The agent type identifier.
        """
        pass
