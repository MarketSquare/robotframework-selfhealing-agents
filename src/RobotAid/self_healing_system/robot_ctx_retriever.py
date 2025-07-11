from typing import Optional

from robot import result
from robot.libraries.BuiltIn import BuiltIn
from robot.utils.misc import seq2str

from RobotAid.self_healing_system.context_retrieving.base_dom_utils import BaseDomUtils
from RobotAid.self_healing_system.context_retrieving.dom_utility_factory import (
    DomUtilityFactory,
)


class RobotCtxRetriever:
    """Retrieves context for the self-healing process of the LLM."""

    @staticmethod
    def get_context(
        result: result.Keyword, dom_utility: Optional[BaseDomUtils] = None
    ) -> dict:
        """Returns context for self-healing process of the LLM.

        Args:
            result: Keyword and additional information passed by robotframework listener.
            dom_utility: Library-specific DOM utility. If not provided,
                         it will be auto-detected based on the keyword result.

        Returns:
            Contains context for the self-healing process of the LLM.
        """
        robot_code_line: str = RobotCtxRetriever._format_keyword_call(result)

        # Use provided DOM utility or create one based on the keyword result
        if dom_utility is None:
            utility_type = DomUtilityFactory.detect_library_from_keyword_result(result)
            dom_utility = DomUtilityFactory.create_dom_utility(utility_type)

        dom_tree: str = dom_utility.get_dom_tree()

        robot_ctx: dict = {
            "robot_code_line": robot_code_line,
            "error_msg": result.message,
            "dom_tree": dom_tree,
            "keyword_name": result.name,
            "keyword_args": result.args,
            "failed_locator": BuiltIn().replace_variables(result.args[0]),
            "library_type": dom_utility.get_library_type(),
        }
        return robot_ctx

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
