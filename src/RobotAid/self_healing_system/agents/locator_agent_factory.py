from enum import Enum
from typing import Optional, Union

from pydantic_ai.usage import UsageLimits

from RobotAid.self_healing_system.agents.base_locator_agent import BaseLocatorAgent
from RobotAid.self_healing_system.agents.browser_locator_agent import (
    BrowserLocatorAgent,
)
from RobotAid.self_healing_system.agents.selenium_locator_agent import (
    SeleniumLocatorAgent,
)
from RobotAid.self_healing_system.context_retrieving.base_dom_utils import BaseDomUtils
from RobotAid.self_healing_system.context_retrieving.dom_utility_factory import (
    DomUtilityFactory,
    DomUtilityType,
)
from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings


class LocatorAgentType(Enum):
    """Enumeration of supported locator agent types."""

    BROWSER = "browser"
    SELENIUM = "selenium"
    APPIUM = "appium"  # Placeholder for future Appium support


class LocatorAgentFactory:
    """Factory class for creating locator agents at runtime.

    This factory provides a clean way to create different flavors of locator agents
    based on the automation library being used. The decision about which agent to
    create is made at runtime based on the provided agent type.
    """

    @staticmethod
    def create_agent(
        agent_type: Union[LocatorAgentType, str, DomUtilityType],
        app_settings: AppSettings,
        client_settings: ClientSettings,
        usage_limits: Optional[UsageLimits] = None,
        dom_utility: Optional[BaseDomUtils] = None,
    ) -> BaseLocatorAgent:
        """Create a locator agent of the specified type.

        Args:
            agent_type: The type of agent to create (browser, selenium, or appium).
                       Can be LocatorAgentType enum, DomUtilityType enum, or string.
            app_settings: Application settings instance.
            client_settings: Client settings instance.
            usage_limits: Optional usage limits for the agent.
            dom_utility: Optional DOM utility instance. If not provided, will be created
                        automatically based on agent type.

        Returns:
            BaseLocatorAgent: An instance of the requested locator agent type.

        Raises:
            ValueError: If the agent type is not supported.
        """
        if usage_limits is None:
            usage_limits = UsageLimits(request_limit=5, total_tokens_limit=2000)

        # Normalize agent type to enum
        agent_type = LocatorAgentFactory._normalize_agent_type(agent_type)

        if dom_utility is None:
            dom_utility_type = LocatorAgentFactory._agent_type_to_dom_type(agent_type)
            try:
                dom_utility = DomUtilityFactory.create_dom_utility(dom_utility_type)
            except Exception as e:
                print(
                    f"Warning: Could not create DOM utility for {agent_type.value}: {e}"
                )
                dom_utility = None

        if agent_type == LocatorAgentType.BROWSER:
            return BrowserLocatorAgent(
                app_settings=app_settings,
                client_settings=client_settings,
                usage_limits=usage_limits,
                dom_utility=dom_utility,
            )
        elif agent_type == LocatorAgentType.SELENIUM:
            return SeleniumLocatorAgent(
                app_settings=app_settings,
                client_settings=client_settings,
                usage_limits=usage_limits,
                dom_utility=dom_utility,
            )
        else:
            # For now, APPIUM is not implemented, but we can add it easily
            raise ValueError(
                f"Unsupported agent type: {agent_type}. Supported types: {[t.value for t in LocatorAgentType if t != LocatorAgentType.APPIUM]}"
            )

    @staticmethod
    def _normalize_agent_type(
        agent_type: Union[LocatorAgentType, str, DomUtilityType],
    ) -> LocatorAgentType:
        """Normalize different agent type representations to LocatorAgentType enum.

        Args:
            agent_type: The agent type to normalize.

        Returns:
            LocatorAgentType: The normalized agent type.

        Raises:
            ValueError: If the agent type cannot be normalized.
        """
        if isinstance(agent_type, LocatorAgentType):
            return agent_type
        elif isinstance(agent_type, DomUtilityType):
            # Convert DomUtilityType to LocatorAgentType
            return LocatorAgentType(agent_type.value)
        elif isinstance(agent_type, str):
            try:
                return LocatorAgentType(agent_type.lower())
            except ValueError:
                raise ValueError(
                    f"Unsupported agent type string: {agent_type}. Supported types: {[t.value for t in LocatorAgentType]}"
                )
        else:
            raise ValueError(f"Unsupported agent type: {type(agent_type)}")

    @staticmethod
    def _agent_type_to_dom_type(agent_type: LocatorAgentType) -> DomUtilityType:
        """Convert LocatorAgentType to DomUtilityType.

        Args:
            agent_type: The locator agent type.

        Returns:
            DomUtilityType: The corresponding DOM utility type.
        """
        return DomUtilityType(agent_type.value)

    @staticmethod
    def get_supported_types() -> list[str]:
        """Get a list of supported agent types.

        Returns:
            list[str]: List of supported agent type strings.
        """
        supported_types = [
            LocatorAgentType.BROWSER.value,
            LocatorAgentType.SELENIUM.value,
            # Note: APPIUM is not yet implemented
        ]
        return supported_types

    @staticmethod
    def detect_agent_type() -> LocatorAgentType:
        """Detect the appropriate agent type based on available libraries.

        This method uses the DOM utility factory's detection logic to ensure
        consistency across the system.

        Returns:
            LocatorAgentType: The detected agent type.
        """
        try:
            dom_type = DomUtilityFactory._auto_detect_utility_type()
            return LocatorAgentType(dom_type.value)
        except Exception:
            return LocatorAgentType.BROWSER

    @staticmethod
    def detect_agent_type_from_keyword_result(result) -> Optional[LocatorAgentType]:
        """Detect the locator agent type from a Robot Framework keyword result.

        Args:
            result: Robot Framework keyword result object with an 'owner' attribute.

        Returns:
            LocatorAgentType: The detected agent type, or None if not detected.
        """
        dom_type = DomUtilityFactory.detect_library_from_keyword_result(result)
        if dom_type is None:
            return None
        return LocatorAgentType(dom_type.value)

    @staticmethod
    def create_auto_detected_agent(
        app_settings: AppSettings,
        client_settings: ClientSettings,
        usage_limits: Optional[UsageLimits] = None,
        dom_utility: Optional[BaseDomUtils] = None,
    ) -> BaseLocatorAgent:
        """Create a locator agent with auto-detected type.

        This method automatically detects the appropriate agent type based on
        available libraries and creates the corresponding agent.

        Args:
            app_settings: Application settings instance.
            client_settings: Client settings instance.
            usage_limits: Optional usage limits for the agent.
            dom_utility: Optional DOM utility instance. If not provided, will be created
                        automatically based on detected type.

        Returns:
            BaseLocatorAgent: An instance of the auto-detected locator agent type.
        """
        agent_type = LocatorAgentFactory.detect_agent_type()
        return LocatorAgentFactory.create_agent(
            agent_type=agent_type,
            app_settings=app_settings,
            client_settings=client_settings,
            usage_limits=usage_limits,
            dom_utility=dom_utility,
        )

    @staticmethod
    def create_agent_from_keyword_result(
        result,
        app_settings: AppSettings,
        client_settings: ClientSettings,
        usage_limits: Optional[UsageLimits] = None,
        dom_utility: Optional[BaseDomUtils] = None,
    ) -> BaseLocatorAgent:
        """Create a locator agent based on Robot Framework keyword result.

        This method detects the appropriate agent type from the keyword result
        and creates the corresponding agent.

        Args:
            result: Robot Framework keyword result object.
            app_settings: Application settings instance.
            client_settings: Client settings instance.
            usage_limits: Optional usage limits for the agent.
            dom_utility: Optional DOM utility instance. If not provided, will be created
                        automatically based on detected type.

        Returns:
            BaseLocatorAgent: An instance of the detected locator agent type.
        """
        agent_type = LocatorAgentFactory.detect_agent_type_from_keyword_result(result)
        if agent_type is None:
            # Fallback to auto-detection if keyword result detection fails
            agent_type = LocatorAgentFactory.detect_agent_type()

        return LocatorAgentFactory.create_agent(
            agent_type=agent_type,
            app_settings=app_settings,
            client_settings=client_settings,
            usage_limits=usage_limits,
            dom_utility=dom_utility,
        )
