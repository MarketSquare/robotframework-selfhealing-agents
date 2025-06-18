from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits
from pydantic_ai.agent import AgentRunResult
from pydantic_ai import ModelRetry
from RobotAid.utils.app_settings import AppSettings
from RobotAid.utils.client_settings import ClientSettings
from RobotAid.self_healing_system.clients.llm_client import get_model
from RobotAid.self_healing_system.agents.locator_agent import LocatorAgent
from RobotAid.self_healing_system.agents.prompts import PromptsOrchestrator
from RobotAid.self_healing_system.schemas import PromptPayload, LocatorHealingResponse



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
            deps_type=PromptPayload,
            output_type=[ self.get_healed_locators, str]
        ))

    async def get_healed_locators(self, ctx: RunContext[PromptPayload], broken_locator: str) -> str:
        """Get a list of healed locator suggestions for a broken locator.

        Args:
            ctx (RunContext): PydanticAI tool context.
            broken_locator (str): Locator that needs to be healed.

        Returns:
            (str): List of repaired locator suggestions in JSON format.

        Example:
            >>> get_healed_locators(ctx, broken_locator="#btn-login")
            '{"suggestions": ["#btn-login-fixed", "input[type=\'submit\']", "css=.btn-login"]}'
        """
        try:
            return await self.locator_agent.heal_async(ctx=ctx)
        except Exception as e:
            raise ModelRetry(f"Locator healing failed: {str(e)}")

    async def run_async(self, robot_ctx: dict) -> str :
        """Run orchestration asynchronously.

        Args:
            robot_ctx (dict): Contains context for the self-healing process of the LLM.

        Returns:
            (str): List of repaired locator suggestions.
        """
        payload: PromptPayload = PromptPayload(**robot_ctx)
        response: AgentRunResult = await self.agent.run(
            PromptsOrchestrator.get_user_msg(payload),
            deps=payload,
            usage_limits=self.usage_limits,
            model_settings={'temperature': 0.1, 'parallel_tool_calls': False}
        )
        return cleanup_response(response.output)

def cleanup_response(response: str) -> str:
    """Cleans up the response from the agent to ensure it is in the correct format.
        e.g. if response starts with "The JSON response is " or <|python_tag|> or {"output": "{"suggestions": [...]}"}
        Just returns the JSON part of the response.
    
    Args:
        response (str): Raw response from the agent.

    Returns:
        LocatorHealingResponse: Parsed and validated response.
    """
    import re
    if response.startswith("The JSON response is"):
        response = response[len("The JSON response is"):].strip()
    if response.startswith("<|python_tag|>"):
        response = response[len("<|python_tag|>"):].strip()
    if response.endswith("."):
        response = response[:-1].strip()
    # Handle nested JSON structure like {"output": "..."}
    # Extract content from nested JSON structure like {"output": "..."}
    nested_json_pattern = r'^\{"output":\s*"(.*)"\}$'
    match = re.match(nested_json_pattern, response)
    if match:
        response = match.group(1)
        # Replace \\"
        response = response.replace('\\"', '"')
    return response