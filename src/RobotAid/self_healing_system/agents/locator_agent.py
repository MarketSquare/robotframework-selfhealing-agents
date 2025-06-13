from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from pydantic_ai.agent import AgentRunResult
from pydantic_ai import ModelRetry

from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings
from RobotAid.self_healing_system.clients.llm_client import get_model
from RobotAid.self_healing_system.agents.prompts import PromptsLocator
from RobotAid.self_healing_system.reponse_converters import convert_response_to_list, convert_response_to_dict
from RobotAid.self_healing_system.context_retrieving.dom_robot_utils import RobotDomUtils 
from RobotAid.self_healing_system.schemas import PromptPayload, LocatorHealingResponse


# MVP LocatorAgent - prompt will be adjusted based on provided context.
try:
    robot_dom_utility = RobotDomUtils()
except:
    print("RobotDomUtils is not installed. Skipping robot DOM utility initialization.")
    robot_dom_utility = None
class LocatorAgent:
    """Produces alternatives for broken locator.

    Attributes:
        app_settings (AppSettings): Instance of AppSettings containing user defined app configuration.
        client_settings (ClientSettings): Instance of ClientSettings containing user defined client configuration.
        usage_limits (UsageLimits): Usage token and request limits.
    """
    def __init__(
        self,
        app_settings: AppSettings,
        client_settings: ClientSettings,
        usage_limits: UsageLimits = UsageLimits(request_limit=5, total_tokens_limit=2000)
    ) -> None:
        self.usage_limits: UsageLimits = usage_limits

        self.generation_agent: Agent[PromptPayload, str] = (
            Agent[PromptPayload, str](
            model=get_model(provider=app_settings.locator_agent.provider,
                            model=app_settings.locator_agent.model,
                            client_settings=client_settings),
            system_prompt=PromptsLocator.system_msg,
            deps_type=PromptPayload,
            output_type=str
        ))
        
        @self.generation_agent.output_validator
        def validate_output(self, output: str) -> str:
            """Validates the output of the locator agent.

            Args:
                output (str): Output from the locator agent.

            Returns:
                (str): Validated output.
            """
            try:
                locator_dict = convert_response_to_dict(output)
                fixed_locators = locator_dict.get("fixed_locators", [])
                if not fixed_locators:
                    raise ModelRetry("No fixed locators found in the response.")
                # Try each locator and return the first valid one
                for locator in fixed_locators:
                    if robot_dom_utility.is_locator_unique(locator):
                        return locator
                raise ModelRetry("None of the fixed locators are valid or unique.")
            except Exception as e:
                raise ModelRetry(f"Invalid output format: {str(e)}. Expected format: {{'fixed_locators': ['locator1', 'locator2', ...]}}") from e

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
            model_settings={'temperature': 0.1}
        )
        return response.output
