from robot import result
from robot.utils.misc import seq2str

from RobotAid.self_healing_system.context_retrieving.dom_robot_utils import RobotDomUtils


class RobotCtxRetriever:
    """Retrieves context for the self-healing process of the LLM."""
    @staticmethod
    def get_context(result: result.Keyword) -> dict:
        """Returns context for self-healing process of the LLM.

        Args:
            result (result.Keyword): Keyword and additional information passed by robotframework listener.

        Returns:
            robot_ctx (dict): Contains context for the self-healing process of the LLM.
        """
        robot_code_line: str = RobotCtxRetriever._format_keyword_call(result)
        dom_tree: str = RobotDomUtils().get_dom_tree()
        robot_ctx: dict = {
            "robot_code_line": robot_code_line,
            "error_msg": result.message,
            "dom_tree": dom_tree,
            "keyword_name": result.name,
            "keyword_args": result.args,
            "failed_locator": result.args[0]
        }
        return robot_ctx

    @staticmethod
    def _format_keyword_call(result: result.Keyword) -> str:
        """Turns a Robot Keyword result into an one‐liner string.

        Args:
            result (result.Keyword): Keyword and additional information passed by robotframework listener.

        Returns:
            (str): Formatted Robot Keyword object to string.
        """
        assign_str: str = ""
        if getattr(result, "assign", None):
            assign_str = " = ".join(result.assign) + " = "

        args_part: str = seq2str(
            result.args,
            quote="",
            sep=" ",
            lastsep=" "
        )
        return f"{assign_str}{result.name} {args_part}"
