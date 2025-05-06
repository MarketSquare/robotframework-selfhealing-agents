import asyncio
from robot import result

from RobotAid.self_healing_system.schemas import LocatorHealingResponse
from RobotAid.self_healing_system.robot_ctx_fetcher import RobotCtxRetriever
from RobotAid.self_healing_system.agents.locator_agent import LocatorAgent
from RobotAid.self_healing_system.agents.orchestrator_agent import OrchestratorAgent


# - The returned locators are not handled yet.
# - Orchestrator agent is implemented for showcase reasons, not directly needed for MVP for locator fix.
class KickoffSelfHealing:
    """Core class for kickoff the self-healing-system for broken robotframework tests."""
    @staticmethod
    def kickoff_healing(result: result.Keyword, llm_provider: str) -> None:
        """Instantiates the multi-agent system, retrieves context and kicks off self-healing-system.

        Args:
            result (result.Keyword): Keyword and additional information passed by robotframework listener.
            llm_provider (str): LLM provider to use; defined by user.
        """
        robot_ctx: dict = RobotCtxRetriever.get_context(result=result)

        locator_agent: LocatorAgent = LocatorAgent(llm_provider=llm_provider)
        orchestrator_agent: OrchestratorAgent = OrchestratorAgent(locator_agent=locator_agent,
                                                                  llm_provider=llm_provider)

        suggestions: LocatorHealingResponse = asyncio.run(
            orchestrator_agent.run_async(robot_ctx=robot_ctx)
        )
        print('Suggestions:', suggestions.suggestions)