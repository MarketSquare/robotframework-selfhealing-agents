import asyncio

from pydantic_ai.usage import UsageLimits
from robot import result

from RobotAid.self_healing_system.agents.locator_agent import LocatorAgent
from RobotAid.self_healing_system.agents.orchestrator_agent import OrchestratorAgent
from RobotAid.self_healing_system.context_retrieving.dom_utility_factory import (
    DomUtilityFactory,
)
from RobotAid.self_healing_system.robot_ctx_retriever import RobotCtxRetriever
from RobotAid.self_healing_system.schemas import LocatorHealingResponse
from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings

try:
    import logfire

    logfire.configure()
    logfire.instrument_pydantic_ai()
except ImportError:
    print("Logfire is not installed. Skipping logfire configuration.")


# - Orchestrator agent is implemented for showcase reasons, not directly needed for MVP for locator fix.
class KickoffSelfHealing:
    """Core class for kickoff the self-healing-system for broken robotframework tests."""

    @staticmethod
    def kickoff_healing(
        result: result.Keyword,
        app_settings: AppSettings,
        client_settings: ClientSettings,
        tried_locator_memory: list,
    ) -> LocatorHealingResponse | str:
        """Instantiates the multi-agent system, retrieves context and kicks off self-healing-system.

        Args:
            result (result.Keyword): Keyword and additional information passed by robotframework listener.
            app_settings (AppSettings): Instance of AppSettings containing user defined app configuration.
            client_settings (ClientSettings): Instance of ClientSettings containing user defined client configuration.
            tried_locator_memory (list): Memory list of executed locator suggestions that still failed.

        Returns:
            response (LocatorHealingResponse): List of suggestions for healing the current robotframework test.
        """

        # Get result.owner to determine agent_type and dom_utility
        # Create dict to map result.owner to agent_type and dom_utility

        # Create dict to map result.owner to agent_type and dom_utility tuples
        library_mapping = {
            "SeleniumLibrary": "selenium",
            "Browser": "browser",
            "AppiumLibrary": "appium",
            # Add more mappings as needed
        }

        agent_type = library_mapping.get(result.owner or "", None)

        dom_utility = DomUtilityFactory.create_dom_utility(utility_type=agent_type)

        # Get context using the library-specific DOM utility (auto-detected)
        robot_ctx: dict = RobotCtxRetriever.get_context(
            result=result, dom_utility=dom_utility
        )
        robot_ctx["tried_locator_memory"] = tried_locator_memory

        # Create appropriate locator agent (let LocatorAgent handle auto-detection)
        locator_agent = LocatorAgent(
            app_settings=app_settings,
            client_settings=client_settings,
            usage_limits=UsageLimits(request_limit=5, total_tokens_limit=8000),
            dom_utility=dom_utility,
            agent_type=agent_type,
        )

        orchestrator_agent: OrchestratorAgent = OrchestratorAgent(
            locator_agent=locator_agent,
            app_settings=app_settings,
            client_settings=client_settings,
            usage_limits=UsageLimits(request_limit=5, total_tokens_limit=8000),
        )

        response = asyncio.run(orchestrator_agent.run_async(robot_ctx=robot_ctx))
        print(response)
        return response
