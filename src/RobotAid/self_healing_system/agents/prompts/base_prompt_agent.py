from typing import ClassVar, Any
from abc import abstractmethod, ABC


class BasePromptAgent(ABC):
    """Abstract base class for prompt agents.

    Enforces the definition of a class-level system message and provides
    abstract methods for generating system and user messages for prompt-based agents.

    Attributes:
        _system_msg (ClassVar[str]): Class-level system message that must be defined by subclasses.
    """
    _system_msg: ClassVar[str]

    def __init_subclass__(cls) -> None:
        """Validates that subclasses define the required class attribute `_system_msg`.

        Raises:
            TypeError: If the subclass does not define `_system_msg` as a string.
        """
        super().__init_subclass__()
        if "_system_msg" not in cls.__dict__ or not isinstance(cls.__dict__["_system_msg"], str):
            raise TypeError("Subclasses must define class attribute `_system_msg: str`")

    @classmethod
    @abstractmethod
    def get_system_msg(cls, *args: Any, **kwargs: Any) -> str:
        """Returns the system message for the agent.

        Args:
            *args: Positional arguments for system message generation.
            **kwargs: Keyword arguments for system message generation.

        Returns:
            str: The system message string.
        """
        ...

    @staticmethod
    @abstractmethod
    def get_user_msg(*args: Any, **kwargs: Any) -> str:
        """Returns the user message for the agent.

        Args:
            *args: Positional arguments for user message generation.
            **kwargs: Keyword arguments for user message generation.

        Returns:
            str: The user message string.
        """
        ...