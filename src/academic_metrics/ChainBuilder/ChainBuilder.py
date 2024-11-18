from __future__ import annotations

import json
import logging
import os
import warnings
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.schema.runnable import Runnable, RunnablePassthrough
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import (
    JsonOutputParser,
    PydanticOutputParser,
    StrOutputParser,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError

# ! THIS NEEDS TO BE REMOVED WHEN THIS IS MADE A STANDALONE PACKAGE
from academic_metrics.constants import LOG_DIR_PATH

# Type that represents "Required first time, optional after"
FirstCallRequired = TypeVar("FirsCallRequired", bound=Dict[str, Any])
ParserUnion = Union[PydanticOutputParser, JsonOutputParser, StrOutputParser]
ParserType = TypeVar("ParserType", bound=ParserUnion)
FallbackParserType = TypeVar("FallbackParserType", bound=ParserUnion)


class ChainBuilder:
    """A builder class for constructing and configuring LangChain chains with logging and parsing capabilities.

    This class provides functionality to construct LangChain chains with customizable prompts,
    language models, and output parsers. It includes support for logging, fallback chains,
    and various parser types.

    Attributes:
        log_file_path (Path): Path to the log file.
        logger (logging.Logger): Logger instance for the chain builder.
        chat_prompt (ChatPromptTemplate): Template for chat prompts.
        parser (Optional[ParserType]): Primary output parser.
        fallback_parser (Optional[FallbackParserType]): Fallback output parser.
        llm (Union[ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI]): Language model instance.
        chain (Runnable): Primary chain instance.
        fallback_chain (Runnable): Fallback chain instance.

    Public Methods:
        get_chain(): Returns the primary chain instance.
        get_fallback_chain(): Returns the fallback chain instance.
        __str__(): Returns a string representation of the ChainBuilder.
        __repr__(): Returns a string representation of the ChainBuilder.

    Private Methods:
        _run_pydantic_parser_logging(): Logs Pydantic parser configuration.
        _build_chain(): Constructs the primary chain.
        _build_fallback_chain(): Constructs the fallback chain.
    """

    def __init__(
        self,
        *,
        chat_prompt: ChatPromptTemplate,
        llm: Union[ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI],
        parser: Optional[ParserType] = None,
        fallback_parser: Optional[FallbackParserType] = None,
        logger: Optional[logging.Logger] = None,
        log_to_console: bool = False,
    ) -> None:
        """Initialize a ChainBuilder instance.

        Args:
            chat_prompt (ChatPromptTemplate): Template for structuring chat interactions.
            llm (Union[ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI]): Language model to use.
            parser (Optional[ParserType], optional): Primary output parser. Defaults to None.
            fallback_parser (Optional[FallbackParserType], optional): Fallback output parser.
                Defaults to None.
            logger (Optional[logging.Logger], optional): Custom logger instance.
                Defaults to None.
            log_to_console (bool, optional): Whether to log to console. Defaults to False.
        """
        # Convert string path to Path, respecting the input path
        self.log_file_path: Path = LOG_DIR_PATH / "chain_builder.log"

        # Set up logger
        self.logger: logging.Logger = logger or logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        self.logger.handlers = []

        # Add handler if none exists
        if not self.logger.handlers:
            handler: logging.FileHandler = logging.FileHandler(self.log_file_path)
            formatter: logging.Formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

            console_handler: Optional[logging.StreamHandler] = (
                logging.StreamHandler() if log_to_console else None
            )
            if console_handler:
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)

        self.chat_prompt: ChatPromptTemplate = chat_prompt
        self.parser: Optional[ParserType] = parser
        self.fallback_parser: Optional[FallbackParserType] = fallback_parser
        self.llm: Union[ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI] = llm
        self.chain: Runnable = self._build_chain()
        self.fallback_chain: Runnable = self._build_fallback_chain()

    def __str__(self) -> str:
        """
        Returns a string representation of the ChainBuilder object.

        The string includes the class names of the chat_prompt, llm, and parser attributes.

        Returns:
            str: A string representation of the ChainBuilder object.
        """
        return f"ChainBuilder(chat_prompt={type(self.chat_prompt).__name__}, llm={self.llm.__class__.__name__}, parser={type(self.parser).__name__ if self.parser else 'None'})"

    def __repr__(self) -> str:
        """
        Returns a string representation of the object for debugging purposes.

        This method calls the __str__() method to provide a human-readable
        representation of the object.

        Returns:
            str: A string representation of the object.
        """
        return self.__str__()

    def _run_pydantic_parser_logging(self) -> None:
        """
        Logs the required fields and their default values (if any) for a Pydantic model
        if the parser is an instance of PydanticOutputParser. Additionally, logs the
        JSON schema of the Pydantic model.

        This method performs the following steps:
        1. Checks if the parser is an instance of PydanticOutputParser.
        2. Retrieves the Pydantic model from the parser.
        3. Logs each field's name and whether it is required or optional.
        4. Logs the default value of each field if it is not None.
        5. Logs the JSON schema of the Pydantic model.

        Returns:
            None
        """
        if isinstance(self.parser, PydanticOutputParser):
            pydantic_model: BaseModel = self.parser.pydantic_object
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
        """
        Builds and returns a chain of Runnable objects.

        The chain is constructed by combining a RunnablePassthrough object with
        the chat_prompt and llm attributes. If a parser is provided, it is added
        to the chain and pydantic parser logging is executed.

        Returns:
            Runnable: The constructed chain of Runnable objects.
        """
        # Build the chain
        chain: Runnable = RunnablePassthrough() | self.chat_prompt | self.llm

        if self.parser:
            self._run_pydantic_parser_logging()
            chain: Runnable = chain | self.parser

        return chain

    def _build_fallback_chain(self) -> Runnable:
        """
        Builds the fallback chain for the Runnable.

        This method constructs a fallback chain by combining a RunnablePassthrough
        instance with the chat prompt and language model (llm). If a fallback parser
        is provided, it adds the parser to the chain and logs the parser usage.

        Returns:
            Runnable: The constructed fallback chain.
        """
        fallback_chain: Runnable = RunnablePassthrough() | self.chat_prompt | self.llm

        if self.fallback_parser:
            self._run_pydantic_parser_logging()
            fallback_chain: Runnable = fallback_chain | self.fallback_parser

        return fallback_chain

    def get_chain(self) -> Runnable:
        """
        Retrieves the current chain.

        Returns:
            Runnable: The current chain instance.
        """
        return self.chain

    def get_fallback_chain(self) -> Runnable:
        """
        Retrieve the fallback chain.

        Returns:
            Runnable: The fallback chain instance.
        """
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
    ) -> None:
        """
        Initialize the ChainBuilder.

        Args:
            chain (Runnable): The primary chain to be executed.
            fallback_chain (Runnable): The fallback chain to be executed if the primary chain fails.
            parser (Optional[ParserType], optional): The parser to be used for the primary chain. Defaults to None.
            fallback_parser (Optional[FallbackParserType], optional): The parser to be used for the fallback chain. Defaults to None.
            preprocessor (Optional[Callable[[Dict[str, Any]], Dict[str, Any]]], optional): A function to preprocess input data before passing it to the chain. Defaults to None.
            postprocessor (Optional[Callable[[Any], Any]], optional): A function to postprocess the output data from the chain. Defaults to None.
            logger (Optional[logging.Logger], optional): A logger instance for logging information. Defaults to None.

        Returns:
            None
        """
        # Set up logger
        self.logger: logging.Logger = logger or logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Add handler if none exists
        if not self.logger.handlers:
            handler: logging.StreamHandler = logging.StreamHandler()
            formatter: logging.Formatter = logging.Formatter(
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
        """
        Returns a string representation of the ChainWrapper object.

        The string includes the chain, the type of the parser, and the type of the fallback parser.

        Returns:
            str: A string representation of the ChainWrapper object.
        """
        return f"ChainWrapper(chain={self.chain}, parser={type(self.parser).__name__ if self.parser else 'None'}, fallback_parser={type(self.fallback_parser).__name__ if self.fallback_parser else 'None'})"

    def __repr__(self) -> str:
        """
        Returns a string representation of the object for debugging purposes.

        This method calls the __str__() method to provide a user-friendly string
        representation of the object. It is intended to be used for debugging
        and development, rather than for end-user display.

        Returns:
            str: A string representation of the object.
        """
        return self.__str__()

    def run_chain(
        self, *, input_data: Dict[str, Any] = None, is_last_chain: bool = False
    ) -> Any:
        """
        Executes the primary chain with the provided input data. If an error occurs in the primary chain,
        and a fallback chain is provided, it attempts to execute the fallback chain.

        Args:
            input_data (Dict[str, Any], optional): The input data required to run the chain. Defaults to None.
            is_last_chain (bool, optional): Indicates if this is the last chain in the sequence. Defaults to False.

        Returns:
            Any: The output from the chain execution, potentially processed by a postprocessor.

        Raises:
            ValueError: If no input data is provided.
            json.JSONDecodeError: If a JSON decode error occurs in both the main and fallback chains.
            ValidationError: If a validation error occurs in both the main and fallback chains.
            TypeError: If a type error occurs in both the main and fallback chains.

        Notes:
            - If the output is a Pydantic model and this is not the last chain, the model is converted to a dictionary.
            - If a postprocessor is defined, it processes the output before returning.
        """
        if cast(Any, input_data) is None:
            raise ValueError(
                "No input data provided to ChainWrapper.run_chain(). Input data is required to run the chain."
            )

        if self.preprocessor:
            input_data = self.preprocessor(input_data)
        output = None

        try:
            # Attempt to invoke the primary chain
            output: Any = self.chain.invoke(input_data)
        except (
            json.JSONDecodeError,
            ValidationError,
            ValueError,
            TypeError,
        ) as main_chain_exception:
            self.logger.info(f"Error in main chain: {main_chain_exception}")
            self.logger.info("Attempting to execute fallback chain")
            if self.fallback_chain and not is_last_chain:
                self.logger.info("Fallback chain provided, executing fallback chain")
                try:
                    # Attempt to invoke the fallback chain
                    output: Any = self.fallback_chain.invoke(input_data)
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
                            "A json decode error occurred in the main chain. Executing fallback chain. If you didn't provide a fallback chain it will not be ran, since it was a json decode error you should check how you're telling the LLM to output the json and make sure it matches your pydantic model. Additionally, LLMs will sometimes output invalid characters to json such as Latex code, leading to invalide escape sequences or characters. If this is the case you should try StrOutputParser() if it isn't your last chain layer. If it is your last chain layer, try simplifying your pydantic model and enhancing your prompt to avoid this issue. If you are using a LLM such as 'gpt-4o-mini' or 'claude-3.5-haiku' you may see better results with a larger model such as 'gpt-4o' or 'claude-3.5-sonnet'."
                        )
                        raise fallback_exception
            else:
                if isinstance(main_chain_exception, json.JSONDecodeError):
                    self.logger.debug(
                        "A json decode error occurred in the main chain. Executing fallback chain. If you didn't provide a fallback chain it will not be ran, since it was a json decode error you should check how you're telling the LLM to output the json and make sure it matches your pydantic model. Additionally, LLMs will sometimes output invalid characters to json such as Latex code, leading to invalide escape sequences or characters. If this is the case you should try StrOutputParser() if it isn't your last chain layer. If it is your last chain layer, try simplifying your pydantic model and enhancing your prompt to avoid this issue. If you are using a LLM such as 'gpt-4o-mini' or 'claude-3.5-haiku' you may see better results with a larger model such as 'gpt-4o' or 'claude-3.5-sonnet'."
                    )
                    raise main_chain_exception

        # Only need to handle intermediate chain Pydantic outputs
        # Rest are handled by JsonOutputParser or PydanticOutputParser
        if not is_last_chain and isinstance(output, BaseModel):
            return output.model_dump()

        if self.postprocessor:
            output: Any = self.postprocessor(output)

        return output

    def get_parser_type(self) -> Union[str, None]:
        """
        Returns the type of the parser as a string if the parser exists, otherwise returns None.

        Returns:
            Union[str, None]: The type of the parser as a string, or None if the parser does not exist.
        """
        return type(self.parser).__name__ if self.parser else None

    def get_fallback_parser_type(self) -> Union[str, None]:
        """
        Returns the type name of the fallback parser if it exists, otherwise returns None.

        Returns:
            Union[str, None]: The type name of the fallback parser as a string if it exists,
                              otherwise None.
        """
        return type(self.fallback_parser).__name__ if self.fallback_parser else None


class ChainComposer:
    """
    ChainComposer is a class that manages a sequence of chain operations, allowing for the addition of chains and running them in sequence with provided data.


    Methods:
        __init__(logger: Optional[logging.Logger] = None) -> None:
            Initializes the ChainComposer instance with an optional logger.

        __str__() -> str:
            Returns a string representation of the ChainComposer instance.

        __repr__() -> str:
            Returns a string representation of the ChainComposer instance.

        add_chain(chain_wrapper: ChainWrapper, output_passthrough_key_name: Optional[str] = None) -> None:
            Adds a chain to the chain sequence.

        run(data_dict: Dict[str, Any], data_dict_update_function: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
            Runs the chain sequence with the provided data dictionary and optional update function.
    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Initializes the ChainBuilder instance.

        Args:
            logger (Optional[logging.Logger]): A logger instance to be used for logging.
                                               If not provided, a default logger will be created.

        Attributes:
            logger (logging.Logger): The logger instance used for logging.
            chain_sequence (List[Tuple[ChainWrapper, Optional[str]]]): A list to store the chain sequence.
        """
        # Set up logger
        self.logger: logging.Logger = logger or logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Add handler if none exists
        if not self.logger.handlers:
            handler: logging.StreamHandler = logging.StreamHandler()
            formatter: logging.Formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.chain_sequence: List[Tuple[ChainWrapper, Optional[str]]] = []

    def __str__(self) -> str:
        """
        Returns a string representation of the ChainComposer object.

        The string representation includes the index and the wrapper of each
        element in the chain_sequence.

        Returns:
            str: A string representation of the ChainComposer object.
        """
        chain_info = ", ".join(
            [
                f"{idx}: {wrapper}"
                for idx, (wrapper, _) in enumerate(self.chain_sequence)
            ]
        )
        return f"ChainComposer(chains=[{chain_info}])"

    def __repr__(self) -> str:
        """
        Returns a string representation of the object for debugging purposes.

        This method calls the __str__() method to provide a human-readable
        representation of the object.

        Returns:
            str: A string representation of the object.
        """
        return self.__str__()

    def add_chain(
        self,
        *,
        chain_wrapper: ChainWrapper,
        output_passthrough_key_name: Optional[str] = None,
    ) -> None:
        """
        Adds a chain to the chain sequence.

        Args:
            chain_wrapper (ChainWrapper): The chain wrapper to be added.
            output_passthrough_key_name (Optional[str], optional): The key name for output passthrough. Defaults to None.

        Returns:
            None
        """
        self.chain_sequence.append((chain_wrapper, output_passthrough_key_name))

    def run(
        self,
        *,
        data_dict: Dict[str, Any],
        data_dict_update_function: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a sequence of chains, updating the provided data dictionary with the results of each chain.

        Args:
            data_dict (Dict[str, Any]): The initial data dictionary containing input variables for the chains.
            data_dict_update_function (Optional[Callable[[Dict[str, Any]], None]]): An optional function to update the data dictionary after each chain execution.

        Returns:
            Dict[str, Any]: The updated data dictionary after all chains have been executed.

        Raises:
            UserWarning: If the provided data dictionary is empty.

        Notes:
            - The method iterates over a sequence of chains (`self.chain_sequence`), executing each chain and updating the `data_dict` with the output.
            - If an `output_name` is provided for a chain, the output is stored in `data_dict` under that name; otherwise, it is stored under the key `_last_output`.
            - If `data_dict_update_function` is provided, it is called with the updated `data_dict` after each chain execution.
        """
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
    """
    ChainManager is a class responsible for managing and orchestrating a sequence of chain layers,
    each of which can process input data and produce output data. It supports various types of
    language models (LLMs) and parsers, and allows for pre-processing and post-processing of data.

    Attributes:
        api_key (str): The API key for accessing the LLM service.
        llm_model (str): The name of the LLM model to use.
        llm_model_type (str): The type of the LLM model (e.g., "openai", "anthropic", "google").
        llm_temperature (float): The temperature setting for the LLM model.
        llm_kwargs (Dict[str, Any]): Additional keyword arguments for the LLM model.
        llm (Union[ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI]): The initialized LLM instance.
        chain_composer (ChainComposer): The composer for managing the sequence of chain layers.
        chain_variables (Dict[str, Any]): A dictionary of variables used in the chain layers.
        chain_variables_update_overwrite_warning_counter (int): Counter for tracking variable overwrite warnings.
        preprocessor (Optional[Callable[[Dict[str, Any]], Dict[str, Any]]]): Optional preprocessor function.
        postprocessor (Optional[Callable[[Any], Any]]): Optional postprocessor function.
        logger (logging.Logger): Logger for logging information and debugging.

    Methods:
        __str__() -> str: Returns a string representation of the ChainManager instance.
        __repr__() -> str: Returns a string representation of the ChainManager instance.
        _get_llm_model_type(llm_model: str) -> str: Determines the type of the LLM model based on its name.
        _initialize_llm(api_key: str, llm_model_type: str, llm_model: str, llm_temperature: float, **llm_kwargs) -> Union[ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI]: Initializes the LLM instance based on the model type.
        _create_openai_llm(api_key: str, llm_model: str, llm_temperature: float, **llm_kwargs) -> ChatOpenAI: Creates an OpenAI LLM instance.
        _create_anthropic_llm(api_key: str, llm_model: str, llm_temperature: float, **llm_kwargs) -> ChatAnthropic: Creates an Anthropic LLM instance.
        _create_google_llm(api_key: str, llm_model: str, llm_temperature: float, **llm_kwargs) -> ChatGoogleGenerativeAI: Creates a Google Generative AI LLM instance.
        _initialize_parser(parser_type: str, pydantic_output_model: Optional[BaseModel] = None) -> ParserType: Initializes a parser based on the specified type.
        _create_pydantic_parser(pydantic_output_model: BaseModel) -> PydanticOutputParser: Creates a Pydantic parser.
        _create_json_parser(pydantic_output_model: Optional[BaseModel]) -> JsonOutputParser: Creates a JSON parser.
        _create_str_parser() -> StrOutputParser: Creates a string parser.
        _run_chain_validation_checks(output_passthrough_key_name: Optional[str], ignore_output_passthrough_key_name_error: bool, parser_type: Optional[Literal["pydantic", "json", "str"]], pydantic_output_model: Optional[BaseModel], fallback_parser_type: Optional[Literal["pydantic", "json", "str"]], fallback_pydantic_output_model: Optional[BaseModel]) -> None: Runs validation checks for the chain configuration.
        _format_chain_sequence(chain_sequence: List[Tuple[ChainWrapper, Optional[str]]]) -> None: Formats and prints the chain sequence.
        _run_validation_checks(prompt_variables_dict: Union[FirstCallRequired, None]) -> None: Runs validation checks for the prompt variables.
        add_chain_layer(system_prompt: str, human_prompt: str, output_passthrough_key_name: Optional[str] = None, ignore_output_passthrough_key_name_error: bool = False, preprocessor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None, postprocessor: Optional[Callable[[Any], Any]] = None, parser_type: Optional[Literal["pydantic", "json", "str"]] = None, fallback_parser_type: Optional[Literal["pydantic", "json", "str"]] = None, pydantic_output_model: Optional[BaseModel] = None, fallback_pydantic_output_model: Optional[BaseModel] = None) -> None: Adds a chain layer to the chain composer.
        _format_overwrite_warning(overwrites: Dict[str, Dict[str, Any]]) -> str: Formats a warning message for variable overwrites.
        _check_first_time_overwrites(prompt_variables_dict: Dict[str, Any]) -> None: Checks for first-time overwrites of global variables and issues warnings.
        _update_chain_variables(prompt_variables_dict: Dict[str, Any]) -> None: Updates global variables with new values, warning on first-time overwrites.
        get_chain_sequence() -> List[Tuple[ChainWrapper, Optional[str]]]: Returns the current chain sequence.
        print_chain_sequence() -> None: Prints the current chain sequence.
        get_chain_variables() -> Dict[str, Any]: Returns the current chain variables.
        print_chain_variables() -> None: Prints the current chain variables.
        run(prompt_variables_dict: Union[FirstCallRequired, None] = None) -> str: Runs the chain composer with the provided prompt variables.
    """

    def __init__(
        self,
        llm_model: str,
        api_key: str,
        llm_temperature: float = 0.7,
        preprocessor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        postprocessor: Optional[Callable[[Any], Any]] = None,
        log_to_console: bool = False,
        **llm_kwargs: Dict[str, Any],
    ) -> None:
        """
        Initializes the ChainBuilder class.

        Args:
            llm_model (str): The name of the language model to be used.
            api_key (str): The API key for accessing the language model.
            llm_temperature (float, optional): The temperature setting for the language model. Defaults to 0.7.
            preprocessor (Optional[Callable[[Dict[str, Any]], Dict[str, Any]]], optional): A function to preprocess input data. Defaults to None.
            postprocessor (Optional[Callable[[Any], Any]], optional): A function to postprocess output data. Defaults to None.
            log_to_console (bool, optional): Flag to enable logging to console. Defaults to False.
            **llm_kwargs (Dict[str, Any]): Additional keyword arguments for the language model.

        Returns:
            None
        """
        # Setup logger
        current_dir: Path = Path(os.path.dirname(os.path.abspath(__file__)))
        log_file_path: Path = current_dir / "chain_builder.log"
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []

        # Add handler if none exists
        if not self.logger.handlers:
            handler: logging.FileHandler = logging.FileHandler(log_file_path)
            handler.setLevel(logging.DEBUG)
            formatter: logging.Formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.propagate = False
            console_handler: Optional[logging.StreamHandler] = (
                logging.StreamHandler() if log_to_console else None
            )
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

        self.logger.info("Initializing ChainComposer")
        self.chain_composer: ChainComposer = ChainComposer(logger=self.logger)
        self.logger.info(f"Initialized ChainComposer: {self.chain_composer}")

        self.logger.info("Initializing Chain Variables")
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
        """
        Returns a string representation of the ChainManager object.

        The string includes the values of the 'llm', 'chain_composer', and 'global_variables' attributes.

        Returns:
            str: A string representation of the ChainManager object.
        """
        return (
            f"ChainManager(llm={self.llm}, chain_composer={self.chain_composer}, "
            f"global_variables={self.global_variables})"
        )

    def __repr__(self) -> str:
        """
        Returns a string representation of the object for debugging purposes.

        This method calls the __str__() method to provide a user-friendly string
        representation of the object.

        Returns:
            str: A string representation of the object.
        """
        return self.__str__()

    def _get_llm_model_type(self, *, llm_model: str) -> str:
        """
        Determine the type of LLM (Large Language Model) based on the provided model name.

        Args:
            llm_model (str): The name of the LLM model.

        Returns:
            str: The type of the LLM model. Possible values are "openai", "anthropic", and "google".

        Raises:
            ValueError: If the provided LLM model name does not match any of the supported types.
        """
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
        """
        Initializes a language model based on the specified type.

        Args:
            api_key (str): The API key for accessing the language model service.
            llm_model_type (str): The type of the language model (e.g., "openai", "anthropic", "google").
            llm_model (str): The specific model to use within the chosen type.
            llm_temperature (float): The temperature setting for the language model, affecting randomness.
            **llm_kwargs (Dict[str, Any]): Additional keyword arguments specific to the language model.

        Returns:
            Union[ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI]: An instance of the initialized language model.

        Raises:
            ValueError: If the specified `llm_model_type` is not supported.
        """
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
        """
        Creates an instance of the ChatOpenAI language model.

        Args:
            api_key (str): The API key for authenticating with the OpenAI service.
            llm_model (str): The identifier of the language model to use.
            llm_temperature (float): The temperature setting for the language model, which controls the randomness of the output.
            **llm_kwargs: Additional keyword arguments to pass to the ChatOpenAI constructor.

        Returns:
            ChatOpenAI: An instance of the ChatOpenAI language model configured with the specified parameters.
        """
        return ChatOpenAI(
            model=llm_model, api_key=api_key, temperature=llm_temperature, **llm_kwargs
        )

    def _create_anthropic_llm(
        self, api_key: str, llm_model: str, llm_temperature: float, **llm_kwargs
    ) -> ChatAnthropic:
        """
        Creates an instance of the ChatAnthropic language model.

        Args:
            api_key (str): The API key for authenticating with the Anthropic service.
            llm_model (str): The identifier of the language model to use.
            llm_temperature (float): The temperature setting for the language model, controlling the randomness of the output.
            **llm_kwargs: Additional keyword arguments to pass to the ChatAnthropic constructor.

        Returns:
            ChatAnthropic: An instance of the ChatAnthropic language model.
        """
        return ChatAnthropic(
            model=llm_model, api_key=api_key, temperature=llm_temperature, **llm_kwargs
        )

    def _create_google_llm(
        self, api_key: str, llm_model: str, llm_temperature: float, **llm_kwargs
    ) -> ChatGoogleGenerativeAI:
        """
        Creates an instance of ChatGoogleGenerativeAI with the specified parameters.

        Args:
            api_key (str): The API key for authenticating with the Google LLM service.
            llm_model (str): The model identifier for the Google LLM.
            llm_temperature (float): The temperature setting for the LLM, which controls the randomness of the output.
            **llm_kwargs: Additional keyword arguments to pass to the ChatGoogleGenerativeAI constructor.

        Returns:
            ChatGoogleGenerativeAI: An instance of the ChatGoogleGenerativeAI class configured with the provided parameters.
        """
        return ChatGoogleGenerativeAI(
            model=llm_model, api_key=api_key, temperature=llm_temperature, **llm_kwargs
        )

    def _initialize_parser(
        self, parser_type: str, pydantic_output_model: Optional[BaseModel] = None
    ) -> ParserType:
        """
        Initializes and returns a parser based on the specified parser type.

        Args:
            parser_type (str):
                The type of parser to initialize.
                Must be one of "pydantic", "json", or "str".
            pydantic_output_model (Optional[BaseModel]):
                The Pydantic model to use for the parser,
                required if parser_type is "pydantic".

        Returns:
            ParserType: An instance of the specified parser type.

        Raises:
            ValueError: If an invalid parser_type is provided.
        """
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
        self, *, pydantic_output_model: Optional[BaseModel]
    ) -> PydanticOutputParser:
        """
        Creates a Pydantic output parser.

        Args:
            pydantic_output_model (Optional[BaseModel]): The Pydantic model to be used for parsing output.
                Must be provided for 'pydantic' parser_type.

        Returns:
            PydanticOutputParser: An instance of PydanticOutputParser initialized with the provided Pydantic model.

        Raises:
            ValueError: If pydantic_output_model is not provided.
        """
        if not pydantic_output_model:
            raise ValueError(
                "pydantic_output_model must be provided for 'pydantic' parser_type."
            )
        return PydanticOutputParser(pydantic_object=pydantic_output_model)

    def _create_json_parser(
        self, *, pydantic_output_model: Optional[BaseModel]
    ) -> JsonOutputParser:
        """
        Creates a JSON parser for the chain layer output.

        Args:
            pydantic_output_model (Optional[BaseModel]): An optional Pydantic model to enforce typing on the JSON output.

        Returns:
            JsonOutputParser: An instance of JsonOutputParser. If pydantic_output_model is provided, the parser will enforce the model's schema on the output.

        Raises:
            UserWarning: If pydantic_output_model is not provided, a warning is issued recommending its use for proper typing of the output.
        """
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
        """
        Creates an instance of StrOutputParser.

        Returns:
            StrOutputParser: An instance of the StrOutputParser class.
        """
        return StrOutputParser()

    def _run_chain_validation_checks(
        self,
        *,
        output_passthrough_key_name: Optional[str],
        ignore_output_passthrough_key_name_error: bool,
        parser_type: Optional[Literal["pydantic", "json", "str"]],
        pydantic_output_model: Optional[BaseModel],
        fallback_parser_type: Optional[Literal["pydantic", "json", "str"]],
        fallback_pydantic_output_model: Optional[BaseModel],
    ) -> None:
        """Validates chain configuration parameters before execution.

        Performs validation checks on chain configuration parameters to ensure proper setup
        and compatibility between different components.

        Args:
            output_passthrough_key_name: Optional key name for passing chain output to next layer.
            ignore_output_passthrough_key_name_error: Whether to ignore missing output key name.
            parser_type: Type of parser to use ("pydantic", "json", or "str").
            pydantic_output_model: Pydantic model for output validation.
            fallback_parser_type: Type of fallback parser.
            fallback_pydantic_output_model: Pydantic model for fallback parser.

        Raises:
            ValueError: If validation fails for:
                - Missing output key name when required
                - Invalid parser type combinations
                - Missing required models
                - Duplicate parser types
                - Same models used for main and fallback

        Warns:
            UserWarning: For non-critical issues like:
                - Missing output key name when ignored
                - Missing recommended Pydantic models
                - Unused provided models
        """
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
        """
        Formats and prints the details of each chain in the given chain sequence.

        Args:
            chain_sequence (List[Tuple[ChainWrapper, Optional[str]]]): A list of tuples where each tuple contains a
            ChainWrapper object and an optional output name.

        Returns:
            None
        """
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
        """
        Validates the input parameters for the chain execution.

        Args:
            prompt_variables_dict : Union[FirstCallRequired, None]
                A dictionary containing the variables to be passed to the chain layers.
                - On the first call to `run()`, this parameter must be provided.
                - On subsequent calls, it can be omitted if there are no new variables to pass.

        Raises:
            ValueError:
                If `prompt_variables_dict` is None on the first call to `run()`.
            TypeError:
                If `prompt_variables_dict` is not a dictionary when provided.

        Notes:
            - The `prompt_variables_dict` should contain keys that match the variable names used in the chain layers.
            - The `output_passthrough_key_name` parameter in the `add_chain_layer` method is used to identify the output of the chain layer and assign it to a variable.
            - If `output_passthrough_key_name` is not specified, the output of the chain layer will not be assigned to a variable and will not be available to the next chain layer.
            - The `ignore_output_passthrough_key_name_error` parameter can be set to True if the output of the chain layer is not needed for the next chain layer, such as when running a chain layer solely for its side effects or if it is the last chain layer in a multi-layer chain.
            - Ensure that the placeholder variable names in your prompt strings match the keys in `prompt_variables_dict` passed into the `ChainManager.run()` method.
        """
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
        """Adds a chain layer to the chain composer.

        This method configures and adds a new chain layer to the chain composer,
        allowing for the processing of input data through specified prompts and parsers.

        Args:
            system_prompt (str): The system prompt template for the chain layer.
            human_prompt (str): The human prompt template for the chain layer.
            output_passthrough_key_name (Optional[str]): Key name for passing chain output to the next layer.
            ignore_output_passthrough_key_name_error (bool): Flag to ignore missing output key name errors.
            preprocessor (Optional[Callable[[Dict[str, Any]], Dict[str, Any]]]): Function to preprocess input data.
            postprocessor (Optional[Callable[[Any], Any]]): Function to postprocess output data.
            parser_type (Optional[Literal["pydantic", "json", "str"]]): Type of parser to use.
            fallback_parser_type (Optional[Literal["pydantic", "json", "str"]]): Type of fallback parser.
            pydantic_output_model (Optional[BaseModel]): Pydantic model for output validation.
            fallback_pydantic_output_model (Optional[BaseModel]): Pydantic model for fallback parser.

        Returns:
            None
        """
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

        parser: Optional[ParserType] = None
        fallback_parser: Optional[ParserType] = None
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
        system_prompt_template: PromptTemplate = PromptTemplate(template=system_prompt)
        human_prompt_template: PromptTemplate = PromptTemplate(template=human_prompt)
        system_message_prompt_template: SystemMessagePromptTemplate = (
            SystemMessagePromptTemplate.from_template(system_prompt_template.template)
        )
        human_message_prompt_template: HumanMessagePromptTemplate = (
            HumanMessagePromptTemplate.from_template(human_prompt_template.template)
        )

        chat_prompt_template: ChatPromptTemplate = ChatPromptTemplate.from_messages(
            [system_message_prompt_template, human_message_prompt_template]
        )
        # Build the chain using ChainBuilder
        chain_builder: ChainBuilder = ChainBuilder(
            chat_prompt=chat_prompt_template,
            llm=self.llm,
            parser=parser,
            fallback_parser=fallback_parser,
            logger=self.logger,
        )
        chain: Runnable = chain_builder.get_chain()
        fallback_chain: Runnable = chain_builder.get_fallback_chain()

        # Wrap the chain
        chain_wrapper: ChainWrapper = ChainWrapper(
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
        return self

    def _format_overwrite_warning(self, overwrites: Dict[str, Dict[str, Any]]) -> str:
        """Formats a warning message for overwritten values.

        Args:
            overwrites (Dict[str, Dict[str, Any]]): A dictionary where the key is the name of the
            overwritten item, and the value is another dictionary with 'old' and 'new' keys
            representing the old and new values respectively.

        Returns:
            str: A formatted string that lists each overwritten item with its old and new values.
        """
        return "\n".join(
            f"  {key}:\n    - {details['old']}\n    + {details['new']}"
            for key, details in overwrites.items()
        )

    def _check_first_time_overwrites(
        self, prompt_variables_dict: Dict[str, Any]
    ) -> None:
        """Checks and warns if any global chain variables are being overwritten for the first time.

        This method compares the keys in the provided `prompt_variables_dict` with the existing
        `chain_variables`. If any keys match, it indicates that an overwrite is occurring. A warning
        is issued the first time this happens, detailing the old and new values of the overwritten
        variables. Subsequent overwrites will not trigger warnings.

        Args:
            prompt_variables_dict (Dict[str, Any]):
                A dictionary containing the new values for the
                chain variables that may overwrite existing ones.

        Returns:
            None
        """
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
        """Update global variables with new values, warning on first-time overwrites.

        Args:
            prompt_variables_dict (Dict[str, Any]): A dictionary containing the new values for the global variables.
        """
        """Update global variables with new values, warning on first-time overwrites."""
        self._check_first_time_overwrites(prompt_variables_dict)
        self.chain_variables.update(prompt_variables_dict)

    def get_chain_sequence(self) -> List[Tuple[ChainWrapper, Optional[str]]]:
        """Retrieves the chain sequence from the chain composer.

        Returns:
            List[Tuple[ChainWrapper, Optional[str]]]: A list of tuples where each tuple contains a ChainWrapper object
            and an optional string.
        """
        return self.chain_composer.chain_sequence

    def print_chain_sequence(self) -> None:
        """Prints the chain sequence by formatting it.

        This method retrieves the chain sequence from the chain composer and
        formats it using the _format_chain_sequence method.

        Returns:
            None
        """
        chain_sequence: List[Tuple[ChainWrapper, Optional[str]]] = (
            self.chain_composer.chain_sequence
        )
        self._format_chain_sequence(chain_sequence)

    def get_chain_variables(self) -> Dict[str, Any]:
        """
        Retrieve the chain variables.

        Returns:
            Dict[str, Any]: A dictionary containing the chain variables.
        """
        return self.chain_variables

    def print_chain_variables(self) -> None:
        """Prints the chain variables in a formatted manner.

        This method prints the chain variables stored in the `chain_variables`
        attribute of the class. The output is formatted with a header and
        footer consisting of dashes, and each key-value pair is printed on
        a new line.

        Returns:
            None
        """
        print(f"Chain Variables:\n{'-' * 10}")
        for key, value in self.chain_variables.items():
            print(f"{key}: {value}")
        print(f"{'-' * 10}\n")

    def run(
        self,
        *,
        prompt_variables_dict: Union[FirstCallRequired, None] = None,
    ) -> str:
        """Executes the chain builder process.

        This method performs validation checks, updates chain variables if provided,
        and runs the chain composer with the current chain variables.

        Args:
            prompt_variables_dict (Union[FirstCallRequired, None], optional):
                A dictionary containing prompt variables. If provided, it will be used
                to update the chain variables. Defaults to None.

        Returns:
            str: The result of running the chain composer.
        """
        self._run_validation_checks(
            prompt_variables_dict=prompt_variables_dict,
        )

        if prompt_variables_dict is not None:
            self._update_chain_variables(prompt_variables_dict)

        return self.chain_composer.run(
            data_dict=self.chain_variables,
            data_dict_update_function=self._update_chain_variables,
        )
