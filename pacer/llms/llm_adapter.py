"""Here we choose a LLM configuration
"""

from enum import StrEnum, auto
from typing import Any, Callable

import dotenv
from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()


class LLMService(StrEnum):
    MISTRAL_LATEST = auto()
    OPENAI_4O = auto()


class LLMSwitch:
    _services: dict[str, Callable[[], Any]] = {}
    _current = None  # Removed Callable type hint from class attribute

    @classmethod
    def register(cls, name: str) -> Callable[[Callable[[], Any]], Callable[[], Any]]:
        """Decorator to register a service function."""

        def decorator(func: Callable[[], Any]) -> Callable[[], Any]:
            cls._services[name] = func
            return func

        return decorator

    @classmethod
    def get_current(cls) -> Any:
        """Get the current service instance."""
        if cls._current is None:
            if cls._services:
                cls._current = list(cls._services.values())[0]
            else:
                raise ValueError("No services registered")
        return cls._current()

    @classmethod
    def services(cls) -> list[str]:
        """Return available service names."""
        return list(cls._services.keys())

    @classmethod
    def switch(cls, service_name: LLMService) -> None:
        """Switch to a different service."""
        service_str = str(service_name)
        if service_str in cls._services:
            cls._current = cls._services[service_str]
        else:
            raise ValueError(f"Service {service_name} not registered")


@LLMSwitch.register(LLMService.OPENAI_4O)
def openai_4o() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o")


@LLMSwitch.register(LLMService.MISTRAL_LATEST)
def mistral_large_latest() -> ChatMistralAI:
    return ChatMistralAI(model="mistral-large-latest")
