import copy
import asyncio
import logging
from pathlib import Path
from functools import wraps
from typing import Callable, Any, Dict
from logging.handlers import RotatingFileHandler

from SelfhealingAgents.utils.cfg import Cfg


def _redact_sensitive_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Redacts sensitive objects (like Cfg) from kwargs for safe logging.

    Args:
        kwargs (dict): The keyword arguments to filter.

    Returns:
        dict: A copy of kwargs with sensitive objects replaced by a placeholder.
    """
    redacted = {}
    for k, v in kwargs.items():
        if isinstance(v, Cfg):
            cfg_redacted = copy.deepcopy(v)
            cfg_redacted.model_config["frozen"] = False
            cfg_redacted.openai_api_key = "<REDACTED API Key>"
            cfg_redacted.litellm_api_key = "<REDACTED API Key>"
            cfg_redacted.azure_api_key = "<REDACTED API Key>"
            cfg_redacted.azure_endpoint = "<REDACTED API Endpoint>"
            cfg_redacted.base_url = "<REDACTED BASE URL>"
            redacted[k] = cfg_redacted
        else:
            redacted[k] = v
    return redacted


def initialize_logger() -> None:
    """Initializes the root logger with a file handler for INFO level logs.

    Creates a 'logs' directory three levels above the current file if it does not exist, and sets up
    a file handler to write logs to 'info.log'. If a file handler is already present, no new handler is added.
    """
    logs_dir: Path = Path.cwd() / "SelfhealingAgentsLogs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file_path: Path = logs_dir / "info.log"

    logger: logging.Logger = logging.getLogger("SelfhealingReports")
    logger.propagate = False
    logger.setLevel(logging.INFO)

    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        file_handler: RotatingFileHandler = logging.handlers.RotatingFileHandler(
            log_file_path, maxBytes=1024 * 1024, backupCount=5
        )
        formatter: logging.Formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def log(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that logs function calls, arguments, return values, and exceptions.

    Supports both synchronous and asynchronous functions. Sensitive objects in kwargs are redacted.

    Args:
        func (Callable[..., Any]): The function to be decorated and logged.

    Returns:
        Callable[..., Any]: The wrapped function with logging enabled.
    """
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger: logging.Logger = logging.getLogger("SelfhealingReports")
            logger.propagate = False
            safe_kwargs: Dict[str, Any] = _redact_sensitive_kwargs(kwargs)
            logger.info(f"Calling async function: {func.__name__} with args: {args}, kwargs: {safe_kwargs}")
            try:
                result: Any = await func(*args, **kwargs)
                logger.info(f"Function {func.__name__} returned: {result}")
                return result
            except Exception as e:
                logger.exception(f"Function {func.__name__} raised an exception:")
                raise
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            logger: logging.Logger = logging.getLogger("SelfhealingReports")
            logger.propagate = False
            safe_kwargs: Dict[str, Any] = _redact_sensitive_kwargs(kwargs)
            logger.info(f"Calling function: {func.__name__} with args: {args}, kwargs: {safe_kwargs}")
            try:
                result: Any = func(*args, **kwargs)
                logger.info(f"Function {func.__name__} returned: {result}")
                return result
            except Exception as e:
                logger.exception(f"Function {func.__name__} raised an exception:")
                raise
        return sync_wrapper