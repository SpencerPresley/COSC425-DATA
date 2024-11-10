from . import core
from . import data_models
from . import utils
from . import strategies
from . import mapping
from . import main
from . import enums
from . import digital_measures_verification
from . import data_collection

# Expose commonly used classes/functions at the package level
from .utils import Utilities, FileHandler, WarningManager, configure_logger
from .strategies import StrategyFactory
from .data_models import CategoryInfo, FacultyStats
from .core import (
    CategoryProcessor,
    FacultyDepartmentManager,
    FacultyPostprocessor,
    NameVariation,
)
from .enums import AttributeTypes

from .data_collection.CrossrefWrapper import CrossrefWrapper
