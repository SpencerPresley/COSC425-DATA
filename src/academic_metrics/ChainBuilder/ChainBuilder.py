import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import json
import logging
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
from pydantic import BaseModel
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
from langchain_core.output_parsers import PydanticOutputParser, JsonOutputParser

# Type that represents "Required first time, optional after"
FirstCallRequired = TypeVar("FirsCallRequired", bound=Dict[str, Any])


class ChainBuilder:
    def __init__(
        self,
        *,
        chat_prompt: ChatPromptTemplate,
        llm: Union[ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI],
        parser: Optional[Union[PydanticOutputParser, JsonOutputParser]] = None,
    ):
        self.chat_prompt = chat_prompt
        self.parser = parser
        self.llm = llm
        self.chain = self._build_chain()

    def __str__(self) -> str:
        return f"ChainBuilder(chat_prompt={type(self.chat_prompt).__name__}, llm={self.llm}, parser={self.parser})"

    def __repr__(self) -> str:
        return self.__str__()

    def _build_chain(self) -> Runnable:
        # Build the chain
        chain: Runnable = RunnablePassthrough() | self.chat_prompt | self.llm

        if self.parser:
            if isinstance(self.parser, PydanticOutputParser):
                pydantic_model = self.parser.pydantic_object
                logger.info("Required fields in Pydantic model:")
                for field_name, field in pydantic_model.model_fields.items():
                    logger.info(
                        f"  {field_name}: {'required' if field.is_required else 'optional'}"
                    )
                    if field.default is not None:
                        logger.info(f"    Default: {field.default}")

                logger.info("\nModel Schema:")
                logger.info(pydantic_model.model_json_schema())

            chain: Runnable = chain | self.parser

        return chain

    def get_chain(self) -> Runnable:
        return self.chain


class ChainWrapper:
    def __init__(
        self,
        *,
        chain: Runnable,
        parser: Optional[Union[PydanticOutputParser, JsonOutputParser]] = None,
        preprocessor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        postprocessor: Optional[Callable[[Any], Any]] = None,
    ):
        self.chain: Runnable = chain
        self.parser: Optional[Union[PydanticOutputParser, JsonOutputParser]] = parser
        self.preprocessor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = (
            preprocessor
        )
        self.postprocessor: Optional[Callable[[Any], Any]] = postprocessor

    def __str__(self) -> str:
        return f"ChainWrapper(chain={self.chain}, parser={self.parser}"

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

        output = self.chain.invoke(input_data)

        # Only need to handle intermediate chain Pydantic outputs
        # Rest are handled by JsonOutputParser or PydanticOutputParser
        if not is_last_chain and isinstance(output, BaseModel):
            return output.model_dump()

        if self.postprocessor:
            output = self.postprocessor(output)

        return output

    def get_parser_type(self) -> Union[str, None]:
        return type(self.parser).__name__ if self.parser else None


class ChainComposer:
    def __init__(self):
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
        **llm_kwargs: Dict[str, Any],
    ):
        self.api_key: str = api_key
        self.llm_model: str = llm_model
        self.llm_model_type: str = self._get_llm_model_type(llm_model=llm_model)

        logger.info(f"Initializing LLM: {self.llm_model}")
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
        logger.info(f"Initialized LLM: {self.llm}")

        logger.info(f"Initializing ChainComposer")
        self.chain_composer: ChainComposer = ChainComposer()
        logger.info(f"Initialized ChainComposer: {self.chain_composer}")

        logger.info(f"Initializing Chain Variables")
        self.chain_variables: Dict[str, Any] = {}
        logger.info(f"Initialized Chain Variables: {self.chain_variables}")

        self.chain_variables_update_overwrite_warning_counter: int = 0

        logger.info(f"Initializing Preprocessor {preprocessor}")
        self.preprocessor: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = (
            preprocessor
        )
        logger.info(f"Initialized Preprocessor: {self.preprocessor}")

        logger.info(f"Initializing Postprocessor {postprocessor}")
        self.postprocessor: Optional[Callable[[Any], Any]] = postprocessor
        logger.info(f"Initialized Postprocessor: {self.postprocessor}")

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
    ) -> Union[PydanticOutputParser, JsonOutputParser]:
        if parser_type == "pydantic":
            parser = self._create_pydantic_parser(
                pydantic_output_model=pydantic_output_model
            )
            logger.debug(f"Created Pydantic parser: {parser}")
            return parser
        elif parser_type == "json":
            parser = self._create_json_parser(
                pydantic_output_model=pydantic_output_model
            )
            logger.debug(f"Created JSON parser: {parser}")
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
        return JsonOutputParser(pydantic_object=pydantic_output_model)

    def _run_chain_validation_checks(
        self,
        *,
        output_passthrough_key_name,
        ignore_output_passthrough_key_name_error,
        parser_type,
        pydantic_output_model,
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

        if parser_type is not None:
            if parser_type not in ["pydantic", "json"]:
                raise ValueError(
                    f"Unsupported parser type: {parser_type}. Supported types: 'pydantic', 'json'."
                )
            if parser_type == "pydantic":
                if not pydantic_output_model:
                    raise ValueError(
                        "pydantic_output_model must be specified when parser_type is 'pydantic'."
                    )
        else:
            if pydantic_output_model:
                warnings.warn(
                    "pydantic_output_model is provided but parser_type is None. The pydantic_output_model will not be used."
                )

    def _format_chain_sequence(
        self, chain_sequence: List[Tuple[ChainWrapper, Optional[str]]]
    ) -> None:
        for index, (chain_wrapper, output_name) in enumerate(chain_sequence):
            print(f"Chain {index + 1}:")
            print(f"\tOutput Name: {output_name}")
            print(f"\tParser Type: {chain_wrapper.get_parser_type()}")
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
        parser_type: Optional[Literal["pydantic", "json"]] = None,
        pydantic_output_model: Optional[BaseModel] = None,
    ) -> None:
        logger.info(
            f"Adding chain layer with output_passthrough_key_name: {output_passthrough_key_name}"
        )
        logger.info(
            f"ignore_output_passthrough_key_name_error: {ignore_output_passthrough_key_name_error}"
        )
        logger.info(f"parser_type: {parser_type}")
        logger.info(f"pydantic_output_model: {pydantic_output_model}")
        logger.info(f"preprocessor: {preprocessor}")
        logger.info(f"postprocessor: {postprocessor}")
        logger.info("--------------------------------")
        logger.info(f"system_prompt: {system_prompt}")
        logger.info(f"human_prompt: {human_prompt}")
        logger.info("--------------------------------")

        self._run_chain_validation_checks(
            output_passthrough_key_name=output_passthrough_key_name,
            ignore_output_passthrough_key_name_error=ignore_output_passthrough_key_name_error,
            parser_type=parser_type,
            pydantic_output_model=pydantic_output_model,
        )

        parser = None
        if parser_type:
            parser = self._initialize_parser(
                parser_type=parser_type, pydantic_output_model=pydantic_output_model
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
            chat_prompt=chat_prompt_template, llm=self.llm, parser=parser
        )
        chain = chain_builder.get_chain()

        # Wrap the chain
        chain_wrapper = ChainWrapper(
            chain=chain,
            parser=parser,
            preprocessor=preprocessor or self.preprocessor,
            postprocessor=postprocessor or self.postprocessor,
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
