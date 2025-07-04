from typing import Any, Optional

from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn


def rerun_keyword_with_fixed_locator(data: Any, fixed_locator: Optional[str] = None) -> str:
    if fixed_locator:
        data.args = list(data.args)
        data.args[0] = fixed_locator
    try:
        logger.info(f"Re-trying Keyword '{data.name}' with arguments '{data.args}'.", also_console=True)
        return_value = BuiltIn().run_keyword(data.name, *data.args)
        # BuiltIn().run_keyword("Take Screenshot")
        return return_value
    except Exception as e:
        logger.debug(f"Unexpected error: {e}")
        raise