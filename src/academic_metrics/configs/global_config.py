import logging
from typing import Dict, Any, cast
import warnings
import os

from academic_metrics.constants import LOG_DIR_PATH


class ColorFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels

    Attributes:
        COLOR_MAP (Dict[str, str]): A dictionary mapping log levels to their corresponding colors.

    Methods:
        Public Methods:
            format: Format the log record with colors.
    """

    COLOR_MAP: Dict[str, str] = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[41m",  # Red background
        "RESET": "\033[0m",  # Reset color
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: The formatted log record with colors.
        """
        # Color only for console output (StreamHandler)
        for handler in logging.getLogger(record.name).handlers:
            if type(handler) is logging.StreamHandler:
                levelname = record.levelname
                if levelname in self.COLOR_MAP:
                    record.levelname = f"{self.COLOR_MAP[levelname]}{levelname}{self.COLOR_MAP['RESET']}"
                break
        return super().format(record)


# Default = True (i.e. log messages will be displayed in the console).
# True is the default to eliminate the need to jump between log files
# to monitor the program's output during pre-release development.
#
# ! If the package is no longer in pre-release development,
# ! this should be set to False to reduce program runtime overhead.
# ! and to not overwhelm potential non-technical end-users.
LOG_TO_CONSOLE = True

# Default = DEBUG (i.e. all log messages will be displayed)
LOG_LEVEL = logging.DEBUG

# Keep track of configured loggers to
# avoid re-configuring the same logger multiple times
# for seperate class instances.
#
# Implements a singleton pattern for loggers of each unique name.
#
# Results in only one logger instance per unique name (i.e. a class object)
# per runtime instance of the program.
_configured_loggers: Dict[str, logging.Logger] = {}

# Log levels for export across the package
# so that other modules can use them without
# needing to import the logging module.
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

# Used to validate the log_level argument is
# a valid python logging log level
# in the configure_logging() function.
VALID_LOG_LEVELS = {DEBUG, INFO, WARNING, ERROR, CRITICAL}

# Configure the config module's logger prior to
# any calls to configure_logging() or set_log_to_console()
_config_logger = logging.getLogger(__name__)
_config_logger.setLevel(LOG_LEVEL)

if os.environ.get("READTHEDOCS") != "True":
    _config_log_file_path = LOG_DIR_PATH / "config.log"
    _file_handler = logging.FileHandler(_config_log_file_path)
    _file_handler.setLevel(LOG_LEVEL)
    _config_file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    _config_color_formatter = ColorFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    _file_handler.setFormatter(_config_file_formatter)
    _config_logger.addHandler(_file_handler)

    if LOG_TO_CONSOLE:
        _console_handler = logging.StreamHandler()
        _console_handler.setLevel(LOG_LEVEL)
        _console_handler.setFormatter(_config_color_formatter)
        _config_logger.addHandler(_console_handler)


def set_log_to_console(value: bool) -> None:
    """Set the global LOG_TO_CONSOLE variable.

    Void function which sets the global LOG_TO_CONSOLE to the provided boolean value
    or issues a warning and leaves the current value unchanged if the provided value is not a boolean.

    Args:
        value (bool): The new boolean True/False value for LOG_TO_CONSOLE.

    Warning:
        If the value is not a boolean, a warning is issued and the current value remains unchanged.
    """
    global LOG_TO_CONSOLE
    if not isinstance(cast(Any, value), bool):
        # The stacklevel=2 argument specifies the level in the stack trace where the warning originates.
        # By setting stacklevel to 2, the warning will point to the caller of the function that issued the warning,
        # rather than the line inside the function itself. This makes it easier for the individual who called the function to locate the source of the issue in their code.
        warnings.warn(
            "LOG_TO_CONSOLE must be a boolean value",
            f"Current `LOG_TO_CONSOLE` value of: {LOG_TO_CONSOLE} will remain unchanged",
            stacklevel=2,
        )
        return

    LOG_TO_CONSOLE = value

    # Update this config logger's console handler
    if LOG_TO_CONSOLE == False:
        # Find and remove any console handlers
        for handler in _config_logger.handlers[
            :
        ]:  # Copy list to avoid modification during iteration
            # If the handler is a StreamHandler (log to console handler)
            # and not a FileHandler (log to file handler)
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                _config_logger.removeHandler(handler)
                _config_logger.info(f"Removed console handler: {handler}")
                _config_logger.debug(f"Removed handler is of type: {type(handler)}")
                _config_logger.debug(f"Current handlers: {_config_logger.handlers}")


def configure_logging(
    module_name: str,
    log_file_name: str | None = None,
    log_level: int | None = LOG_LEVEL,
    force: bool | None = False,
) -> logging.Logger:
    """Configure a logger for a specific module.

    Configures logging for a module if not already configured.
    Acts as a singleton per module_name.

    Args:
        module_name (str): The name of the module to configure logging for.
        - This should be passed in as the `__name__` variable of the module.

        log_file_name (str): The name of the log file to use for the module.
        - This should be a valid file name with no file extension.

        - It should only be the file name desired for that module, not the full path.

        log_level (int): The log level to use for the module.
        - This should be a valid python logging log level.

        force (bool): Whether to force the creation of a new logger instance.
        - If a logger instance for the module already exists and `force` is False, the existing instance will be returned.

        - If a logger instance for the module already exists and `force` is True, a new instance will be created.

    Returns:
        logging.Logger: The configured logger for the module.

    """
    if module_name in _configured_loggers and not force:
        _config_logger.debug(
            f"Logger for module `{module_name}` already configured. "
            "Returning existing instance."
            "To create a new instance, set `force=True`."
        )
        return _configured_loggers[module_name]
    elif module_name in _configured_loggers and force:
        _config_logger.debug(
            f"Logger for module `{module_name}` already configured. "
            f"But `force` flag is set to `{force}`. "
            "Therefore, creating a new instance."
        )
        _configured_loggers[module_name] = None

    if log_file_name is None:
        # The stacklevel=2 argument specifies the level in the stack trace where the warning originates.
        # By setting stacklevel to 2, the warning will point to the caller of the function that issued the warning,
        # rather than the line inside the function itself. This makes it easier for the individual who called the function to locate the source of the warning in their code.
        # And determine if they meant not to pass in log_file_name.
        _config_logger.info(
            "`log_file_name` was not provided. "
            f"`log_file_name` is of value: `{log_file_name}`. "
            f"It will be replaced with: `{module_name}`.",
            stacklevel=2,
        )
        log_file_name = module_name

    # Validate the log_level argument is a valid log level
    if log_level is not None:
        if log_level not in VALID_LOG_LEVELS:
            _config_logger.warning(
                f"Invalid log level provided: `{log_level}`. "
                f"Must be one of: {VALID_LOG_LEVELS}. "
                f"Using default log level: `{LOG_LEVEL}` instead.",
                stacklevel=2,
            )
            log_level = LOG_LEVEL

    _config_logger.info(f"Creating new logger configuration for {module_name}")

    logger = logging.getLogger(module_name)
    logger.setLevel(log_level)

    # Prevent the logger from propagating to the root logger.
    # This should avoid duplicate log messages in the console.
    logger.propagate = False

    console_formatter = ColorFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    log_file_path = LOG_DIR_PATH / f"{log_file_name}.log"
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    if LOG_TO_CONSOLE:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        _config_logger.info(f"Added console handler for {module_name}")

    _configured_loggers[module_name] = logger
    return logger
