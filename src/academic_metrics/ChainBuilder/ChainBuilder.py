from __future__ import annotations

import logging
import os
import warnings
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    Literal,
    Callable,
)
from pathlib import Path
from pydantic import BaseModel, ValidationError
import json
from langchain.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
    PromptTemplate,
)
from langchain.schema.runnable import Runnable, RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import (
    PydanticOutputParser,
    JsonOutputParser,
    StrOutputParser,
)

# ! THIS NEEDS TO BE REMOVED WHEN THIS IS MADE A STANDALONE PACKAGE
from academic_metrics.constants import LOG_DIR_PATH

# Type that represents "Required first time, optional after"
FirstCallRequired = TypeVar("FirsCallRequired", bound=Dict[str, Any])
ParserUnion = Union[PydanticOutputParser, JsonOutputParser, StrOutputParser]
ParserType = TypeVar("ParserType", bound=ParserUnion)
FallbackParserType = TypeVar("FallbackParserType", bound=ParserUnion)


class ChainBuilder:
    def __init__(
        self,
        *,
        chat_prompt: ChatPromptTemplate,
        llm: Union[ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI],
        parser: Optional[ParserType] = None,
        fallback_parser: Optional[FallbackParserType] = None,
        logger: Optional[logging.Logger] = None,
        log_to_console: bool = False,
    ):
        # Convert string path to Path, respecting the input path
        self.log_file_path = LOG_DIR_PATH / "chain_builder.log"

        # Set up logger
        self.logger = logger or logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        self.logger.handlers = []

        # Add handler if none exists
        if not self.logger.handlers:
            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

            console_handler = logging.StreamHandler() if log_to_console else None
            if console_handler:
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)

        self.chat_prompt = chat_prompt
        self.parser: Optional[ParserType] = parser
        self.fallback_parser: Optional[FallbackParserType] = fallback_parser
        self.llm = llm
        self.chain = self._build_chain()
        self.fallback_chain = self._build_fallback_chain()

    def __str__(self) -> str:
        return f"ChainBuilder(chat_prompt={type(self.chat_prompt).__name__}, llm={self.llm.__class__.__name__}, parser={type(self.parser).__name__ if self.parser else 'None'})"

    def __repr__(self) -> str:
        return self.__str__()

    def _run_pydantic_parser_logging(self) -> None:
        if isinstance(self.parser, PydanticOutputParser):
            pydantic_model = self.parser.pydantic_object
            self.logger.info("Required fields in Pydantic model:")
            for field_name, field in pydantic_model.model_fields.items():
                self.logger.info(
                    f"  {field_name}: {'required' if field.is_required else 'optional'}"
                )
                if field.default is not None:
                    self.logger.info(f"    Default: {field.default}")

            self.logger.info("\nModel Schema:")
            self.logger.info(pydantic_model.model_json_schema())

    def _build_chain(self) -> Runnable:
        # Build the chain
        chain: Runnable = RunnablePassthrough() | self.chat_prompt | self.llm

        if self.parser:
            self._run_pydantic_parser_logging()
            chain: Runnable = chain | self.parser

        return chain

    def _build_fallback_chain(self) -> Runnable:
        fallback_chain: Runnable = RunnablePassthrough() | self.chat_prompt | self.llm

        if self.fallback_parser:
            self._run_pydantic_parser_logging()
            fallback_chain: Runnable = fallback_chain | self.fallback_parser

        return fallback_chain

    def get_chain(self) -> Runnable:
        return self.chain

    def get_fallback_chain(self) -> Runnable:
        return self.fallback_chain


class ChainWrapper:
    def __init__(
        self,
        *,
        chain: Runnable,
        fallback_chain: Runnable,
        parser: Optional[ParserType] = None,
        fallback_parser: Optional[FallbackParserType] = None,
        preprocessor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        postprocessor: Optional[Callable[[Any], Any]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        # Set up logger
        self.logger = logger or logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Add handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.parser: Optional[ParserType] = parser
        self.fallback_parser: Optional[FallbackParserType] = fallback_parser
        self.preprocessor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = (
            preprocessor
        )

        self.chain: Runnable = chain
        self.fallback_chain: Runnable = fallback_chain
        self.postprocessor: Optional[Callable[[Any], Any]] = postprocessor

    def __str__(self) -> str:
        return f"ChainWrapper(chain={self.chain}, parser={type(self.parser).__name__ if self.parser else 'None'}, fallback_parser={type(self.fallback_parser).__name__ if self.fallback_parser else 'None'})"

    def __repr__(self) -> str:
        return self.__str__()

    def run_chain(
        self, *, input_data: Dict[str, Any] = None, is_last_chain: bool = False
    ) -> Any:
        if cast(Any, input_data) is None:
            raise ValueError(
                "No input data provided to ChainWrapper.run_chain(). Input data is required to run the chain."
            )

        if self.preprocessor:
            input_data = self.preprocessor(input_data)
        output = None

        try:
            # Attempt to invoke the primary chain
            output = self.chain.invoke(input_data)
        except (
            json.JSONDecodeError,
            ValidationError,
            ValueError,
            TypeError,
        ) as main_chain_exception:
            self.logger.info(f"Error in main chain: {main_chain_exception}")
            self.logger.info(f"Attempting to execute fallback chain")
            if self.fallback_chain and not is_last_chain:
                self.logger.info(f"Fallback chain provided, executing fallback chain")
                try:
                    # Attempt to invoke the fallback chain
                    output = self.fallback_chain.invoke(input_data)
                except (
                    json.JSONDecodeError,
                    ValidationError,
                    ValueError,
                    TypeError,
                ) as fallback_exception:
                    if isinstance(fallback_exception, json.JSONDecodeError):
                        self.logger.debug(
                            f"Error in fallback chain: {fallback_exception.errors()}"
                        )
                        self.logger.debug(
                            f"A json decode error occurred in the main chain. Executing fallback chain. If you didn't provide a fallback chain it will not be ran, since it was a json decode error you should check how you're telling the LLM to output the json and make sure it matches your pydantic model. Additionally, LLMs will sometimes output invalid characters to json such as Latex code, leading to invalide escape sequences or characters. If this is the case you should try StrOutputParser() if it isn't your last chain layer. If it is your last chain layer, try simplifying your pydantic model and enhancing your prompt to avoid this issue. If you are using a LLM such as 'gpt-4o-mini' or 'claude-3.5-haiku' you may see better results with a larger model such as 'gpt-4o' or 'claude-3.5-sonnet'."
                        )
                        raise fallback_exception
            else:
                if isinstance(main_chain_exception, json.JSONDecodeError):
                    self.logger.debug(
                        f"A json decode error occurred in the main chain. Executing fallback chain. If you didn't provide a fallback chain it will not be ran, since it was a json decode error you should check how you're telling the LLM to output the json and make sure it matches your pydantic model. Additionally, LLMs will sometimes output invalid characters to json such as Latex code, leading to invalide escape sequences or characters. If this is the case you should try StrOutputParser() if it isn't your last chain layer. If it is your last chain layer, try simplifying your pydantic model and enhancing your prompt to avoid this issue. If you are using a LLM such as 'gpt-4o-mini' or 'claude-3.5-haiku' you may see better results with a larger model such as 'gpt-4o' or 'claude-3.5-sonnet'."
                    )
                    raise main_chain_exception

        # Only need to handle intermediate chain Pydantic outputs
        # Rest are handled by JsonOutputParser or PydanticOutputParser
        if not is_last_chain and isinstance(output, BaseModel):
            return output.model_dump()

        if self.postprocessor:
            output = self.postprocessor(output)

        return output

    def get_parser_type(self) -> Union[str, None]:
        return type(self.parser).__name__ if self.parser else None

    def get_fallback_parser_type(self) -> Union[str, None]:
        return type(self.fallback_parser).__name__ if self.fallback_parser else None


class ChainComposer:
    def __init__(self, logger: Optional[logging.Logger] = None):
        # Set up logger
        self.logger = logger or logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Add handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.chain_sequence: List[Tuple[ChainWrapper, Optional[str]]] = []

    def __str__(self) -> str:
        chain_info = ", ".join(
            [
                f"{idx}: {wrapper}"
                for idx, (wrapper, _) in enumerate(self.chain_sequence)
            ]
        )
        return f"ChainComposer(chains=[{chain_info}])"

    def __repr__(self) -> str:
        return self.__str__()

    def add_chain(
        self,
        *,
        chain_wrapper: ChainWrapper,
        output_passthrough_key_name: Optional[str] = None,
    ):
        self.chain_sequence.append((chain_wrapper, output_passthrough_key_name))

    def run(
        self,
        *,
        data_dict: Dict[str, Any],
        data_dict_update_function: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        if not data_dict:
            warnings.warn(
                "No variables provided for the chain. Please ensure you have provided the necessary variables. If you have variable placeholders and do not pass them in it will result in an error."
            )

        num_chains: int = len(self.chain_sequence)
        for index, (chain_wrapper, output_name) in enumerate(self.chain_sequence):
            is_last_chain: bool = index == num_chains - 1
            output: Union[BaseModel, Dict[str, Any], str] = chain_wrapper.run_chain(
                input_data=data_dict, is_last_chain=is_last_chain
            )

            # Update data with the output
            if output_name:
                data_dict[output_name] = output
            else:
                data_dict["_last_output"] = output

            if data_dict_update_function:
                data_dict_update_function(data_dict)

        return data_dict


class ChainManager:
    def __init__(
        self,
        llm_model: str,
        api_key: str,
        llm_temperature: float = 0.7,
        preprocessor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        postprocessor: Optional[Callable[[Any], Any]] = None,
        log_to_console: bool = False,
        **llm_kwargs: Dict[str, Any],
    ):
        # Setup logger
        current_dir = os.path.dirname(os.path.abspath(__file__))
        log_file_path = os.path.join(current_dir, "chain_builder.log")
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []

        # Add handler if none exists
        if not self.logger.handlers:
            handler = logging.FileHandler(log_file_path)
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.propagate = False
            console_handler = logging.StreamHandler() if log_to_console else None
            if console_handler:
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)

        self.api_key: str = api_key
        self.llm_model: str = llm_model
        self.llm_model_type: str = self._get_llm_model_type(llm_model=llm_model)

        self.logger.info(f"Initializing LLM: {self.llm_model}")
        self.llm_kwargs: Dict[str, Any] = llm_kwargs or {}
        self.llm_temperature: float = llm_temperature
        self.llm: Union[ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI] = (
            self._initialize_llm(
                api_key=self.api_key,
                llm_model_type=self.llm_model_type,
                llm_model=self.llm_model,
                llm_temperature=self.llm_temperature,
                **self.llm_kwargs,
            )
        )
        self.logger.info(f"Initialized LLM: {self.llm}")

        self.logger.info(f"Initializing ChainComposer")
        self.chain_composer: ChainComposer = ChainComposer(logger=self.logger)
        self.logger.info(f"Initialized ChainComposer: {self.chain_composer}")

        self.logger.info(f"Initializing Chain Variables")
        self.chain_variables: Dict[str, Any] = {}
        self.logger.info(f"Initialized Chain Variables: {self.chain_variables}")

        self.chain_variables_update_overwrite_warning_counter: int = 0

        self.logger.info(f"Initializing Preprocessor {preprocessor}")
        self.preprocessor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = (
            preprocessor
        )
        self.logger.info(f"Initialized Preprocessor: {self.preprocessor}")

        self.logger.info(f"Initializing Postprocessor {postprocessor}")
        self.postprocessor: Optional[Callable[[Any], Any]] = postprocessor
        self.logger.info(f"Initialized Postprocessor: {self.postprocessor}")

    def __str__(self) -> str:
        return (
            f"ChainManager(llm={self.llm}, chain_composer={self.chain_composer}, "
            f"global_variables={self.global_variables})"
        )

    def __repr__(self) -> str:
        return self.__str__()

    def _get_llm_model_type(self, *, llm_model: str) -> str:
        if llm_model.lower().startswith("gpt"):
            return "openai"
        elif llm_model.lower().startswith("claude"):
            return "anthropic"
        elif llm_model.lower().startswith("gemini"):
            return "google"
        else:
            raise ValueError(
                f"Unsupported LLM model: {llm_model}. Supported types: gpt, claude, gemini."
            )

    def _initialize_llm(
        self,
        *,
        api_key: str,
        llm_model_type: str,
        llm_model: str,
        llm_temperature: float,
        **llm_kwargs: Dict[str, Any],
    ) -> Union[ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI]:
        if llm_model_type == "openai":
            return self._create_openai_llm(
                api_key, llm_model, llm_temperature, **llm_kwargs
            )
        elif llm_model_type == "anthropic":
            return self._create_anthropic_llm(
                api_key, llm_model, llm_temperature, **llm_kwargs
            )
        elif llm_model_type == "google":
            return self._create_google_llm(
                api_key, llm_model, llm_temperature, **llm_kwargs
            )
        else:
            raise ValueError(
                f"Unsupported LLM model type: {llm_model_type}. Supported types: openai, anthropic, google."
            )

    def _create_openai_llm(
        self, api_key: str, llm_model: str, llm_temperature: float, **llm_kwargs
    ) -> ChatOpenAI:
        return ChatOpenAI(
            model=llm_model, api_key=api_key, temperature=llm_temperature, **llm_kwargs
        )

    def _create_anthropic_llm(
        self, api_key: str, llm_model: str, llm_temperature: float, **llm_kwargs
    ) -> ChatAnthropic:
        return ChatAnthropic(
            model=llm_model, api_key=api_key, temperature=llm_temperature, **llm_kwargs
        )

    def _create_google_llm(
        self, api_key: str, llm_model: str, llm_temperature: float, **llm_kwargs
    ) -> ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(
            model=llm_model, api_key=api_key, temperature=llm_temperature, **llm_kwargs
        )

    def _initialize_parser(
        self, parser_type: str, pydantic_output_model: Optional[BaseModel] = None
    ) -> ParserType:
        if parser_type == "pydantic":
            parser: PydanticOutputParser = self._create_pydantic_parser(
                pydantic_output_model=pydantic_output_model
            )
            self.logger.debug(f"Created Pydantic parser: {parser}")
            return parser
        elif parser_type == "json":
            parser: JsonOutputParser = self._create_json_parser(
                pydantic_output_model=pydantic_output_model
            )
            self.logger.debug(f"Created JSON parser: {parser}")
            return parser
        elif parser_type == "str":
            parser: StrOutputParser = self._create_str_parser()
            self.logger.debug(f"Created Str parser: {parser}")
            return parser
        else:
            raise ValueError(f"Invalid parser_type: {parser_type}")

    def _create_pydantic_parser(
        self, *, pydantic_output_model: BaseModel
    ) -> PydanticOutputParser:
        if not pydantic_output_model:
            raise ValueError(
                "pydantic_output_model must be provided for 'pydantic' parser_type."
            )
        return PydanticOutputParser(pydantic_object=pydantic_output_model)

    def _create_json_parser(
        self, *, pydantic_output_model: Optional[BaseModel]
    ) -> JsonOutputParser:
        json_parser: Optional[JsonOutputParser] = None
        if not pydantic_output_model:
            warnings.warn(
                "It is highly recommended to provide a pydantic_output_model when parser_type is 'json'. "
                "This will ensure that the output of the chain layer is properly typed and can be used in downstream chain layers."
            )
            self.logger.debug("Creating JSON parser without pydantic_output_model. ")
            json_parser = JsonOutputParser()
        else:
            self.logger.debug(
                f"Creating JSON parser with pydantic_output_model: {pydantic_output_model}"
            )
            json_parser = JsonOutputParser(pydantic_object=pydantic_output_model)
        return json_parser

    def _create_str_parser(self) -> StrOutputParser:
        return StrOutputParser()

    def _run_chain_validation_checks(
        self,
        *,
        output_passthrough_key_name,
        ignore_output_passthrough_key_name_error,
        parser_type,
        pydantic_output_model,
        fallback_parser_type,
        fallback_pydantic_output_model,
    ) -> None:
        if (
            len(self.chain_composer.chain_sequence) > 0
            and not output_passthrough_key_name
        ):
            if not ignore_output_passthrough_key_name_error:
                raise ValueError(
                    "output_passthrough_key_name not provided and ignore_output_passthrough_key_name_error is False. output_passthrough_key_name is required to identify the output of the chain layer in order to pass the output to the next chain layer. If you do not specify output_passthrough_key_name, the output of the chain layer will not be assigned to a variable and thus will not be available to the next chain layer. If you do not need the output of the chain layer to be passed to the next chain layer, you can set ignore_output_passthrough_key_name_error to True."
                )
            else:
                warnings.warn(
                    "output_passthrough_key_name not provided when adding a chain layer after another. Output of the chain layer will not be assigned to a variable."
                )

        if parser_type is None and fallback_parser_type is not None:
            raise ValueError(
                "parser_type is None when fallback_parser_type is not None. This is not allowed."
            )

        if (parser_type is not None and pydantic_output_model is not None) and (
            fallback_parser_type is not None
            and fallback_pydantic_output_model is not None
        ):
            if pydantic_output_model == fallback_pydantic_output_model:
                raise ValueError(
                    "pydantic_output_model and fallback_pydantic_output_model are the same. This is not allowed."
                )

        if parser_type is not None:
            if parser_type not in ["pydantic", "json", "str"]:
                raise ValueError(
                    f"Unsupported parser type: {parser_type}. Supported types:\n"
                    f"\t'{PydanticOutputParser.__name__}'\n"
                    f"\t'{JsonOutputParser.__name__}'\n"
                    f"\t'{StrOutputParser.__name__}'"
                )
            if parser_type == "pydantic":
                if not pydantic_output_model:
                    raise ValueError(
                        "pydantic_output_model must be specified when parser_type is 'pydantic'."
                    )
            elif parser_type == "json":
                if not pydantic_output_model:
                    warnings.warn(
                        "It is highly recommended to provide a pydantic_output_model when parser_type is 'json'. "
                        "This will ensure that the output of the chain layer is properly typed and can be used in downstream chain layers."
                    )
        else:
            if pydantic_output_model:
                warnings.warn(
                    "pydantic_output_model is provided but parser_type is None. The pydantic_output_model will not be used."
                )

        if fallback_parser_type is not None:
            if parser_type is not None and fallback_parser_type == parser_type:
                raise ValueError(
                    "parser_type and fallback_parser_type are the same. This is not allowed."
                )

            if fallback_parser_type not in ["pydantic", "json", "str"]:
                raise ValueError(
                    f"Unsupported fallback_parser_type: {fallback_parser_type}"
                )
            if fallback_parser_type == "pydantic":
                if not fallback_pydantic_output_model:
                    raise ValueError(
                        "fallback_pydantic_output_model must be specified when fallback_parser_type is 'pydantic'."
                    )
            elif fallback_parser_type == "json":
                if not fallback_pydantic_output_model:
                    warnings.warn(
                        "It is highly recommended to provide a fallback_pydantic_output_model when fallback_parser_type is 'json'. "
                        "This will ensure that the output of the fallback chain layer is properly typed and can be used in downstream chain layers."
                    )
        else:
            if fallback_pydantic_output_model:
                warnings.warn(
                    "fallback_pydantic_output_model is provided but fallback_parser_type is None. The fallback_pydantic_output_model will not be used."
                )

    def _format_chain_sequence(
        self, chain_sequence: List[Tuple[ChainWrapper, Optional[str]]]
    ) -> None:
        for index, (chain_wrapper, output_name) in enumerate(chain_sequence):
            print(f"Chain {index + 1}:")
            print(f"\tOutput Name: {output_name}")
            print(f"\tParser Type: {chain_wrapper.get_parser_type()}")
            print(f"\tFallback Parser Type: {chain_wrapper.get_fallback_parser_type()}")
            print(f"\tPreprocessor: {chain_wrapper.preprocessor}")
            print(f"\tPostprocessor: {chain_wrapper.postprocessor}")

    def _run_validation_checks(
        self,
        *,
        prompt_variables_dict: Union[FirstCallRequired, None],
    ) -> None:
        if (
            self.chain_variables_update_overwrite_warning_counter == 0
            and prompt_variables_dict is None
        ):
            raise ValueError(
                "First call to run() must provide a prompt_variables_dict, otherwise there are no variables to pass to the chain layers. "
                "If you do not need to pass variables to the chain layers, you can set prompt_variables_dict to an empty dictionary. "
                "Subsequent calls to run() can omit prompt_variables_dict if you have no new variables to pass to the chain layers. "
                "This is because a global_variables dictionary is maintained in the ChainManager instance and is updated with each call to the class instance method _update_global_variables(), which is automatically called by run() when a new prompt_variables_dict is provided. "
            )

        if prompt_variables_dict is not None and not isinstance(
            cast(Any, prompt_variables_dict), dict
        ):
            raise TypeError(
                "prompt_variables_dict must be a dictionary. "
                "Each key should match the variable names used in your chain layers. "
                "output_passthrough_key_name parameter in add_chain_layer method is used to identify the output of the chain layer "
                "and assign it to a variable. If you do not specify output_passthrough_key_name, the output of the chain layer will not be assigned to a variable and thus will not be available to the next chain layer. "
                "If you do not need the output of the chain layer to be passed to the next chain layer, you can set ignore_output_passthrough_key_name_error to True. "
                "A time to set ignore_output_passthrough_key_name_error to True is when you are running a chain layer solely for its side effects (e.g. printing, saving to a database, etc.) without needing the output of the chain layer to be passed to the next chain layer. "
                "Another reason to set ignore_output_passthrough_key_name_error to True is if you have a multi-layer chain and this is your last chain layer. "
                "Check your prompt strings for your placeholder variables, these names should match the keys in prompt_variables_dict passed into the ChainManager.run() method."
            )

    def add_chain_layer(
        self,
        *,
        system_prompt: str,
        human_prompt: str,
        output_passthrough_key_name: Optional[str] = None,
        ignore_output_passthrough_key_name_error: bool = False,
        preprocessor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        postprocessor: Optional[Callable[[Any], Any]] = None,
        parser_type: Optional[Literal["pydantic", "json", "str"]] = None,
        fallback_parser_type: Optional[Literal["pydantic", "json", "str"]] = None,
        pydantic_output_model: Optional[BaseModel] = None,
        fallback_pydantic_output_model: Optional[BaseModel] = None,
    ) -> None:
        self.logger.info(
            f"Adding chain layer with output_passthrough_key_name: {output_passthrough_key_name}"
        )
        self.logger.info(
            f"ignore_output_passthrough_key_name_error: {ignore_output_passthrough_key_name_error}"
        )
        self.logger.info(f"parser_type: {parser_type}")
        self.logger.info(f"pydantic_output_model: {pydantic_output_model}")
        self.logger.info(f"preprocessor: {preprocessor}")
        self.logger.info(f"postprocessor: {postprocessor}")
        self.logger.info("--------------------------------")
        self.logger.info(f"system_prompt: {system_prompt}")
        self.logger.info(f"human_prompt: {human_prompt}")
        self.logger.info("--------------------------------")

        self._run_chain_validation_checks(
            output_passthrough_key_name=output_passthrough_key_name,
            ignore_output_passthrough_key_name_error=ignore_output_passthrough_key_name_error,
            parser_type=parser_type,
            pydantic_output_model=pydantic_output_model,
            fallback_parser_type=fallback_parser_type,
            fallback_pydantic_output_model=fallback_pydantic_output_model,
        )

        parser = None
        fallback_parser = None
        if parser_type:
            parser = self._initialize_parser(
                parser_type=parser_type, pydantic_output_model=pydantic_output_model
            )
        if fallback_parser_type:
            fallback_parser = self._initialize_parser(
                parser_type=fallback_parser_type,
                pydantic_output_model=fallback_pydantic_output_model,
            )
        # Create prompt templates without specifying input_variables
        system_prompt_template = PromptTemplate(template=system_prompt)
        human_prompt_template = PromptTemplate(template=human_prompt)
        system_message_prompt_template = SystemMessagePromptTemplate.from_template(
            system_prompt_template.template
        )
        human_message_prompt_template = HumanMessagePromptTemplate.from_template(
            human_prompt_template.template
        )
        chat_prompt_template = ChatPromptTemplate.from_messages(
            [system_message_prompt_template, human_message_prompt_template]
        )
        # Build the chain using ChainBuilder
        chain_builder = ChainBuilder(
            chat_prompt=chat_prompt_template,
            llm=self.llm,
            parser=parser,
            fallback_parser=fallback_parser,
            logger=self.logger,
        )
        chain = chain_builder.get_chain()
        fallback_chain = chain_builder.get_fallback_chain()

        # Wrap the chain
        chain_wrapper = ChainWrapper(
            chain=chain,
            fallback_chain=fallback_chain,
            parser=parser,
            fallback_parser=fallback_parser,
            preprocessor=preprocessor or self.preprocessor,
            postprocessor=postprocessor or self.postprocessor,
            logger=self.logger,
        )

        # Add the chain to the composer
        self.chain_composer.add_chain(
            chain_wrapper=chain_wrapper,
            output_passthrough_key_name=output_passthrough_key_name,
        )

        # Return the ChainManager instance to allow for method chaining
        # Returning the instance shouldn't have any side effects, it should allow for method chaining
        return self

    def _format_overwrite_warning(self, overwrites: Dict[str, Dict[str, Any]]) -> str:
        return "\n".join(
            f"  {key}:\n    - {details['old']}\n    + {details['new']}"
            for key, details in overwrites.items()
        )

    def _check_first_time_overwrites(
        self, prompt_variables_dict: Dict[str, Any]
    ) -> None:
        if self.chain_variables_update_overwrite_warning_counter == 0:
            overwrites = {
                key: {
                    "old": self.chain_variables[key],
                    "new": prompt_variables_dict[key],
                }
                for key in prompt_variables_dict
                if key in self.chain_variables
            }
            if overwrites:
                warnings.warn(
                    f"Overwriting existing global variables:\n"
                    f"{self._format_overwrite_warning(overwrites)}\n"
                    "Subsequent overwrites will not trigger warnings."
                )
            self.chain_variables_update_overwrite_warning_counter += 1

    def _update_chain_variables(self, prompt_variables_dict: Dict[str, Any]) -> None:
        """Update global variables with new values, warning on first-time overwrites."""
        self._check_first_time_overwrites(prompt_variables_dict)
        self.chain_variables.update(prompt_variables_dict)

    def get_chain_sequence(self) -> List[Tuple[ChainWrapper, Optional[str]]]:
        return self.chain_composer.chain_sequence

    def print_chain_sequence(self) -> None:
        chain_sequence = self.chain_composer.chain_sequence
        self._format_chain_sequence(chain_sequence)

    def get_chain_variables(self) -> Dict[str, Any]:
        return self.chain_variables

    def print_chain_variables(self) -> None:
        print(f"Chain Variables:\n{'-' * 10}")
        for key, value in self.chain_variables.items():
            print(f"{key}: {value}")
        print(f"{'-' * 10}\n")

    def run(
        self,
        *,
        prompt_variables_dict: Union[FirstCallRequired, None] = None,
    ) -> str:
        self._run_validation_checks(
            prompt_variables_dict=prompt_variables_dict,
        )

        if prompt_variables_dict is not None:
            self._update_chain_variables(prompt_variables_dict)

        return self.chain_composer.run(
            data_dict=self.chain_variables,
            data_dict_update_function=self._update_chain_variables,
        )
