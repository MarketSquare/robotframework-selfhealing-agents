import asyncio
from robot.api import logger

from pydantic_ai.usage import UsageLimits
from robot import result

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.agents.locator_agent.locator_agent import LocatorAgent
from RobotAid.self_healing_system.agents.orchestrator_agent.orchestrator_agent import OrchestratorAgent
from RobotAid.self_healing_system.context_retrieving.dom_utils.dom_utility_factory import (
    DomUtilityFactory,
)
from RobotAid.self_healing_system.context_retrieving.robot_ctx_retriever import RobotCtxRetriever
from RobotAid.self_healing_system.schemas.api.locator_healing import (
    LocatorHealingResponse,
    NoHealingNeededResponse,
)
from RobotAid.utils.logfire_init import init_logfire

_LIBRARY_MAPPING = {
    "SeleniumLibrary": "selenium",
    "Browser": "browser",
    "AppiumLibrary": "appium",
}


class KickoffMultiAgentSystem:
    """Core class for kickoff the self-healing-system for broken robotframework tests."""

    init_logfire()

    @staticmethod
    def kickoff_healing(
        result: result.Keyword,
        cfg: Cfg,
        tried_locator_memory: list,
    ) -> LocatorHealingResponse | str | NoHealingNeededResponse:
        """Instantiates the multi-agent system, retrieves context and kicks off self-healing-system.

        Args:
            result: Keyword and additional information passed by robotframework listener.
            cfg: Instance of Cfg config class containing user defined app configuration.
            tried_locator_memory: Memory list of executed locator suggestions that still failed.

        Returns:
            List of suggestions for healing the current robotframework test.
        """
        agent_type = _LIBRARY_MAPPING.get(result.owner or "", None)
        dom_utility = DomUtilityFactory.create_dom_utility(utility_type=agent_type)

        # Get context using the library-specific DOM utility (auto-detected)
        robot_ctx: dict = RobotCtxRetriever.get_context(
            result=result, dom_utility=dom_utility
        )
        robot_ctx["tried_locator_memory"] = tried_locator_memory

        # Create appropriate locator agent (let LocatorAgent handle auto-detection)
        locator_agent = LocatorAgent(
            cfg=cfg,
            usage_limits=UsageLimits(request_limit=5, total_tokens_limit=8000),
            dom_utility=dom_utility,
            agent_type=agent_type,
        )

        orchestrator_agent: OrchestratorAgent = OrchestratorAgent(
            locator_agent=locator_agent,
            cfg=cfg,
            usage_limits=UsageLimits(request_limit=5, total_tokens_limit=8000),
        )

        response = asyncio.get_event_loop().run_until_complete(
            orchestrator_agent.run_async(robot_ctx=robot_ctx)
        )
        logger.debug(f"{response}")
        return response
