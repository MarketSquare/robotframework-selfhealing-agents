from bs4 import BeautifulSoup
from robot import result
from robot.utils.misc import seq2str
from robot.libraries.BuiltIn import BuiltIn


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
        html_ids: list = RobotCtxRetriever._get_html_ids()
        robot_ctx: dict = {
            "robot_code_line": robot_code_line,
            "error_msg": result.message,
            "html_ids": html_ids,
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

    @staticmethod
    def _get_html_ids() -> list:
        """Fetches html IDs from Browser instance.

        Returns:
            html_ids (list): List of html IDs present in Browser instance.
        """
        browser_lib = BuiltIn().get_library_instance('Browser')
        html_content = browser_lib.get_page_source()
        soup = BeautifulSoup(html_content, 'html.parser')
        html_ids = [tag['id'] for tag in soup.find_all(attrs={'id': True})]
        return html_ids

