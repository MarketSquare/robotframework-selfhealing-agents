from robot import result
from robot.utils.misc import seq2str
from robot.libraries.BuiltIn import BuiltIn

from RobotAid.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import BaseDomUtils
from RobotAid.self_healing_system.schemas.internal_state.prompt_payload import PromptPayload


class RobotCtxRetriever:
    """Retrieves context for the self-healing process of the LLM."""

    @staticmethod
    def get_context_payload(
        result: result.Keyword, dom_utility: BaseDomUtils
    ) -> PromptPayload:
        """Returns context for self-healing process of the LLM.

        Args:
            result: Keyword and additional information passed by robotframework listener.
            dom_utility: Library-specific DOM utility. If not provided,
                         it will be auto-detected based on the keyword result.

        Returns:
            Contains context for the self-healing process of the LLM.
        """
        robot_code_line: str = RobotCtxRetriever._format_keyword_call(result)
        dom_tree: str = dom_utility.get_dom_tree()

        robot_ctx_payload: PromptPayload = PromptPayload(
            robot_code_line=robot_code_line,
            error_msg=result.message,
            dom_tree=dom_tree,
            keyword_name=result.name,
            keyword_args=result.args,
            failed_locator=BuiltIn().replace_variables(result.args[0]),
            tried_locator_memory=[]
        )
        return robot_ctx_payload

    @staticmethod
    def _format_keyword_call(result: result.Keyword) -> str:
        """Turns a Robot Keyword result into an one‐liner string.

        Args:
            result: Keyword and additional information passed by robotframework listener.

        Returns:
            Formatted Robot Keyword object to string.
        """
        assign_str: str = ""
        if getattr(result, "assign", None):
            assign_str = " = ".join(result.assign) + " = "

        args_part: str = seq2str(result.args, quote="", sep=" ", lastsep=" ")
        return f"{assign_str}{result.name} {args_part}"
