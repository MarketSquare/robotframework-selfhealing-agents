from typing import TypeVar, Generic, ClassVar, Any


T = TypeVar('T')


class BasePromptAgent(Generic[T]):

    _system_msg: ClassVar[str]

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if "_system_msg" not in cls.__dict__ or not isinstance(cls.__dict__["_system_msg"], str):
            raise TypeError("Subclasses must define class attribute `_system_msg: str`")

    @classmethod
    def get_system_msg(cls, *args: Any, **kwargs: Any) -> str:
        ...

    @staticmethod
    def get_user_msg(*args: Any, **kwargs: Any) -> str:
        ...