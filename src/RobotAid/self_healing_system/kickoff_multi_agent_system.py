import asyncio
from typing import List, Final

from robot import result
from robot.api import logger

from RobotAid.utils.cfg import Cfg
from RobotAid.self_healing_system.schemas.internal_state.prompt_payload import PromptPayload
from RobotAid.self_healing_system.context_retrieving.robot_ctx_retriever import RobotCtxRetriever
from RobotAid.self_healing_system.agents.locator_agent.base_locator_agent import BaseLocatorAgent
from RobotAid.self_healing_system.agents.locator_agent.locator_agent_factory import LocatorAgentFactory
from RobotAid.self_healing_system.agents.orchestrator_agent.orchestrator_agent import OrchestratorAgent
from RobotAid.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import BaseDomUtils
from RobotAid.self_healing_system.context_retrieving.dom_utility_factory import (
    DomUtilityFactory,
)
from RobotAid.self_healing_system.schemas.api.locator_healing import (
    LocatorHealingResponse,
    NoHealingNeededResponse,
)


_LIBRARY_MAPPING: Final[dict[str, str]] = {
    "SeleniumLibrary": "selenium",
    "Browser": "browser",
    "AppiumLibrary": "appium",
}


class KickoffMultiAgentSystem:
    """Core class for kickoff the self-healing-system for broken robotframework tests."""


    @staticmethod
    def kickoff_healing(
        result: result.Keyword,
        *,
        cfg: Cfg,
        tried_locator_memory: List[str],
    ) -> LocatorHealingResponse | str | NoHealingNeededResponse:
        """Instantiates the multi-agent system, retrieves context and kicks off self-healing-system.

        Args:
            result: Keyword and additional information passed by robotframework listener.
            cfg: Instance of Cfg config class containing user defined app configuration.
            tried_locator_memory: Memory list of executed locator suggestions that still failed.

        Returns:
            List of suggestions for healing the current robotframework test.
        """
        agent_type: str = _LIBRARY_MAPPING.get(result.owner, None)
        if agent_type is None:
            raise ValueError(f"Library type: {agent_type} not supported.")
        dom_utility: BaseDomUtils = DomUtilityFactory.create_dom_utility(agent_type)

        robot_ctx_payload: PromptPayload = RobotCtxRetriever.get_context_payload(result, dom_utility)
        robot_ctx_payload.tried_locator_memory = tried_locator_memory

        locator_agent: BaseLocatorAgent = LocatorAgentFactory.create_agent(agent_type, cfg, dom_utility)

        orchestrator_agent: OrchestratorAgent = OrchestratorAgent(cfg, locator_agent)

        response = asyncio.get_event_loop().run_until_complete(
            orchestrator_agent.run_async(robot_ctx_payload)
        )
        logger.debug(f"{response}")
        return response
