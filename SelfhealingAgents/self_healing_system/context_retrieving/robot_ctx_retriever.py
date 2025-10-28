from pathlib import Path
from robot import result, running
from robot.utils.misc import seq2str
from robot.libraries.BuiltIn import BuiltIn

from SelfhealingAgents.utils.logging import log
from SelfhealingAgents.self_healing_system.context_retrieving.library_dom_utils.base_dom_utils import BaseDomUtils
from SelfhealingAgents.self_healing_system.schemas.internal_state.prompt_payload import PromptPayload


class RobotCtxRetriever:
    """Retrieves context information for the self-healing process of the LLM.

    This class provides static methods to extract and format the necessary context
    from Robot Framework keyword results and DOM utilities for use in LLM-based
    self-healing workflows.
    """
    @staticmethod
    @log
    def get_context_payload(
        data: running.Keyword,
        result: result.Keyword,
        dom_utility: BaseDomUtils
    ) -> PromptPayload:
        """Builds and returns a context payload for the LLM self-healing process.

        Extracts relevant information from the Robot Framework keyword result and
        the provided DOM utility to construct a PromptPayload object.

        Args:
            result: The keyword result and additional information passed by the Robot Framework listener.
            dom_utility: The library-specific DOM utility instance.

        Returns:
            A PromptPayload object containing context for the self-healing process.
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
            tried_locator_memory=[],
            locator_type="tbd",
            file_usage_ctx=RobotCtxRetriever._file_usage_ctx(data)
        )
        return robot_ctx_payload

    @staticmethod
    def _format_keyword_call(result: result.Keyword) -> str:
        """Formats a Robot Framework keyword result as a single-line string.

        Converts the keyword call, including assignments and arguments, into a
        one-liner string representation suitable for context extraction.

        Args:
            result: The keyword result and additional information passed by the Robot Framework listener.

        Returns:
            A string representing the formatted Robot Framework keyword call.
        """
        assign_str: str = ""
        if getattr(result, "assign", None):
            assign_str = " = ".join(result.assign) + " = "

        args_part: str = seq2str(result.args, quote="", sep=" ", lastsep=" ")
        return f"{assign_str}{result.name} {args_part}"

    @staticmethod
    def _file_usage_ctx(data: running.Keyword) -> str:
        """Loads the full source file in which the locator failed and returns it as string for context of LLM.

        Args:
            data: The running test case data.#

        Returns:
            Full file string for context of LLM.
        """
        source_file = Path(data.source)
        if not source_file.exists():
            raise FileNotFoundError(f"Source file for LLM context not found: {source_file}")
        return source_file.read_text(encoding="utf-8", errors="ignore")