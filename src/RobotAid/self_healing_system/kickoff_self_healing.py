import asyncio
from robot import result

from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings
from RobotAid.self_healing_system.schemas import LocatorHealingResponse
from RobotAid.self_healing_system.robot_ctx_retriever import RobotCtxRetriever
from RobotAid.self_healing_system.agents.locator_agent import LocatorAgent
from RobotAid.self_healing_system.agents.orchestrator_agent import OrchestratorAgent


# - The returned locators are not handled yet.
# - Orchestrator agent is implemented for showcase reasons, not directly needed for MVP for locator fix.
class KickoffSelfHealing:
    """Core class for kickoff the self-healing-system for broken robotframework tests."""
    @staticmethod
    def kickoff_healing(
            result: result.Keyword,
            app_settings: AppSettings,
            client_settings: ClientSettings
    ) -> None:
        """Instantiates the multi-agent system, retrieves context and kicks off self-healing-system.

        Args:
            result (result.Keyword): Keyword and additional information passed by robotframework listener.
            app_settings (AppSettings): Instance of AppSettings containing user defined app configuration.
            client_settings (ClientSettings): Instance of ClientSettings containing user defined client configuration.
        """
        robot_ctx: dict = RobotCtxRetriever.get_context(result=result)

        locator_agent: LocatorAgent = LocatorAgent(app_settings=app_settings,
                                                   client_settings=client_settings)
        orchestrator_agent: OrchestratorAgent = OrchestratorAgent(locator_agent=locator_agent,
                                                                  app_settings=app_settings,
                                                                  client_settings=client_settings)

        suggestions: LocatorHealingResponse = asyncio.run(
            orchestrator_agent.run_async(robot_ctx=robot_ctx)
        )
        print('Suggestions:', suggestions.suggestions)