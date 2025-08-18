import asyncio
from typing import List, Final

from robot import result

from RobotAid.utils.cfg import Cfg
from RobotAid.utils.logging import log
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
    """Core class for initiating the self-healing system for broken Robot Framework tests.

    This class coordinates the multi-agent system responsible for self-healing failed Robot Framework keywords.
    It retrieves the necessary context, instantiates the appropriate agents, and triggers the healing process.
    """
    @staticmethod
    @log
    def kickoff_healing(
        result: result.Keyword,
        *,
        cfg: Cfg,
        tried_locator_memory: List[str],
    ) -> LocatorHealingResponse | str | NoHealingNeededResponse:
        """Instantiates the multi-agent system, retrieves context, and initiates the self-healing process.

        Args:
            result: The keyword result and additional information passed by the Robot Framework listener.
            cfg: An instance of the Cfg config class containing user-defined application configuration.
            tried_locator_memory: A list of locator suggestions that have already been tried and failed.

        Returns:
            A LocatorHealingResponse with suggestions for healing the current Robot Framework test,
             a string message, or a NoHealingNeededResponse if no healing is required.
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
        return response
