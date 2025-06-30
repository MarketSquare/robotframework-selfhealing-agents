import asyncio
from robot import result
from pydantic_ai.usage import UsageLimits
from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings
from RobotAid.self_healing_system.schemas import LocatorHealingResponse
from RobotAid.self_healing_system.robot_ctx_retriever import RobotCtxRetriever
from RobotAid.self_healing_system.agents.locator_agent import LocatorAgent
from RobotAid.self_healing_system.agents.orchestrator_agent import OrchestratorAgent
from pydantic_ai.usage import UsageLimits

try:
    import logfire
    logfire.configure()
    logfire.instrument_pydantic_ai()
except ImportError:
    print("Logfire is not installed. Skipping logfire configuration.")
	

# - The returned locators are not handled yet.
# - Orchestrator agent is implemented for showcase reasons, not directly needed for MVP for locator fix.
class KickoffSelfHealing:
    """Core class for kickoff the self-healing-system for broken robotframework tests."""
    @staticmethod
    def kickoff_healing(
            result: result.Keyword,
            app_settings: AppSettings,
            client_settings: ClientSettings,
            tried_locator_memory: list
    ) -> LocatorHealingResponse:
        """Instantiates the multi-agent system, retrieves context and kicks off self-healing-system.

        Args:
            result (result.Keyword): Keyword and additional information passed by robotframework listener.
            app_settings (AppSettings): Instance of AppSettings containing user defined app configuration.
            client_settings (ClientSettings): Instance of ClientSettings containing user defined client configuration.
            tried_locator_memory (list): Memory list of executed locator suggestions that still failed.

        Returns:
            response (LocatorHealingResponse): List of suggestions for healing the current robotframework test.
        """
        robot_ctx: dict = RobotCtxRetriever.get_context(result=result)
        robot_ctx["tried_locator_memory"] = tried_locator_memory

        locator_agent: LocatorAgent = LocatorAgent(app_settings=app_settings,
                                                   client_settings=client_settings,
                                                   usage_limits=UsageLimits(request_limit=5, total_tokens_limit=8000)
                                                   )
                                                                                   
        orchestrator_agent: OrchestratorAgent = OrchestratorAgent(locator_agent=locator_agent,
                                                                  app_settings=app_settings,
                                                                  client_settings=client_settings,
                                                                  usage_limits=UsageLimits(request_limit=5, total_tokens_limit=8000)
                                                                  )

        response: str = asyncio.run(
            orchestrator_agent.run_async(robot_ctx=robot_ctx)
        )
        print(response)
        return LocatorHealingResponse.model_validate_json(response)