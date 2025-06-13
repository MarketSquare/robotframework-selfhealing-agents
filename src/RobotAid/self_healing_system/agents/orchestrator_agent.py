from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from pydantic_ai.agent import AgentRunResult
from pydantic_ai import ModelRetry

from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings
from RobotAid.self_healing_system.schemas import PromptPayload
from RobotAid.self_healing_system.clients.llm_client import get_model
from RobotAid.self_healing_system.agents.locator_agent import LocatorAgent
from RobotAid.self_healing_system.agents.prompts import PromptsOrchestrator


# MVP Orchestrator Agent - will be adjusted to context and when additional agents will be implemented.
class OrchestratorAgent:
    """Routes raw failure text to the appropriate healing tool.

    Attributes:
        app_settings (AppSettings): Instance of AppSettings containing user defined app configuration.
        client_settings (ClientSettings): Instance of ClientSettings containing user defined client configuration.
        locator_agent (LocatorAgent): LocatorAgent instance.
    """
    def __init__(self, app_settings: AppSettings, client_settings: ClientSettings, locator_agent: LocatorAgent, usage_limits: UsageLimits = UsageLimits(request_limit=5, total_tokens_limit=2000)) -> None:
        self.locator_agent: LocatorAgent = locator_agent
        self.usage_limits: UsageLimits = usage_limits
        self.agent: Agent[PromptPayload, str] = (
            Agent[PromptPayload, str](
            model=get_model(provider=app_settings.orchestrator_agent.provider,
                            model=app_settings.orchestrator_agent.model,
                            client_settings=client_settings),
            system_prompt=PromptsOrchestrator.system_msg,
            deps_type=PromptPayload
        ))

        @self.agent.tool(name="locator_heal")
        async def locator_heal(ctx: RunContext[PromptPayload]) -> str:
            """Invoke LocatorAgent on locator error.

            Args:
                ctx (RunContext): PydanticAI tool context.

            Returns:
                (str): Repaired locator suggestion.
            """
            try:
                return await self.locator_agent.heal_async(ctx=ctx)
            except Exception as e:
                raise ModelRetry(f"Locator healing failed: {str(e)}")

    async def run_async(self, robot_ctx: dict) -> str:
        """Run orchestration asynchronously.

        Args:
            robot_ctx (dict): Contains context for the self-healing process of the LLM.

        Returns:
            (str): Repaired locator suggestion.
        """
        payload: PromptPayload = PromptPayload(**robot_ctx)
        response: AgentRunResult = await self.agent.run(
            PromptsOrchestrator.get_user_msg(payload),
            deps=payload,
            usage_limits=self.usage_limits,
            model_settings={'temperature': 0.0}
        )
        return response.output
