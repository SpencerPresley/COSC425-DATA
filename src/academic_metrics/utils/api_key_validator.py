import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from langchain.schema.runnable import Runnable

from academic_metrics.constants import LOG_DIR_PATH


@dataclass
class ValidationResult:
    openai: bool = False
    anthropic: bool = False
    google: bool = False


class APIKeyValidator:
    """
    Validator for LLM API keys across different services.

    Example:
        >>> validator = APIKeyValidator(api_key="sk-...")
        >>> if validator.is_valid():
        >>>     print("Key is valid!")
        >>>     validator.print_results()  # See which services work
    """

    def __init__(self):
        # Dict to track api keys which have been validated already
        # Key = api_key, Value = bool (True if valid, False if not)
        self._validated_already: Dict[str, bool] = {}
        self.log_file_path: str = os.path.join(LOG_DIR_PATH, "api_key_validator.log")
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []

        if not self.logger.handlers:
            handler: logging.FileHandler = logging.FileHandler(self.log_file_path)
            handler.setLevel(logging.DEBUG)
            formatter: logging.Formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _validate(self, api_key: str, model: Optional[str] = None) -> None:
        """Run validation tests for each service."""
        from langchain.prompts import (
            ChatPromptTemplate,
            HumanMessagePromptTemplate,
            PromptTemplate,
            SystemMessagePromptTemplate,
        )

        results: ValidationResult = ValidationResult()
        system_prompt_template: PromptTemplate = PromptTemplate(template="test")
        human_prompt_template: PromptTemplate = PromptTemplate(template="test")

        prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(
                    system_prompt_template.template
                ),
                HumanMessagePromptTemplate.from_template(
                    human_prompt_template.template
                ),
            ]
        )

        # Test OpenAI
        try:
            from langchain_openai import ChatOpenAI

            llm: ChatOpenAI = ChatOpenAI(api_key=api_key, model=model or "gpt-4o-mini")

            chain: Runnable = prompt | llm
            chain.invoke({})
            results.openai = True

        except Exception:
            pass

        # Test Anthropic
        try:
            from langchain_anthropic import ChatAnthropic

            llm: ChatAnthropic = ChatAnthropic(
                api_key=api_key, model=model or "claude-3.5-haiku"
            )
            chain: Runnable = prompt | llm
            chain.invoke({})
            results.anthropic = True
        except Exception:
            pass

        # Test Google
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm: ChatGoogleGenerativeAI = ChatGoogleGenerativeAI(
                api_key=api_key, model=model or "gemini-1.5-pro"
            )
            chain: Runnable = prompt | llm
            chain.invoke({})
            results.google = True
        except Exception:
            pass

        self._validated_already[api_key] = results

    def _check_attr(self) -> None:
        """Check if the API key is valid for any service."""
        if not hasattr(self, "_current_key"):
            raise RuntimeError(
                "Must call is_valid() before checking validity. "
                "Example usage: "
                ">>> validator = APIKeyValidator() "
                ">>> if validator.is_valid(api_key='...'): "
                ">>>     print('Key is valid!')"
                ">>> else: "
                ">>>     print('Key is invalid!')"
            )

    def is_valid(self, api_key: str, model: Optional[str] = None) -> bool:
        """Check if the API key is valid for any service. Validates if not already done."""
        if api_key not in self._validated_already:
            self._validate(api_key=api_key, model=model)

        results = self._validated_already[api_key]
        return any([results.openai, results.anthropic, results.google])

    def get_results_for_api_key(self, api_key: str) -> Dict[str, bool]:
        """Get detailed validation results. Validates if not already done."""
        if api_key not in self._validated_already:
            self._validate(api_key=api_key)

        results = self._validated_already[api_key]
        return {
            "openai": results.openai,
            "anthropic": results.anthropic,
            "google": results.google,
        }

    def get_full_results(self) -> Dict[str, Dict[str, bool]]:
        """Get detailed validation results for all keys."""
        return self._validated_already

    def print_results_for_api_key(self, api_key: str) -> None:
        """Print formatted validation results for a given API key."""
        from academic_metrics.utils.unicode_chars_dict import unicode_chars_dict

        results: Dict[str, bool] = self.get_results_for_api_key(api_key)
        print(f"API Key: {api_key}")
        for service, valid in results.items():
            status = (
                f"{unicode_chars_dict.get('boxed_checkmark', '')} Valid"
                if valid
                else f"{unicode_chars_dict.get('boxed_x', '')} Invalid"
            )
            print(f"{service.title()}: {status}")
        print("-" * 25)

    def print_full_results(self) -> None:
        """Print formatted validation results for all keys."""
        print("\nAPI Key Validation Results:")
        print("-" * 25)
        api_keys = list(self._validated_already.keys())
        for api_key in api_keys:
            self.print_results_for_api_key(api_key)
