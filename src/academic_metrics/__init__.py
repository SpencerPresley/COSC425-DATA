from . import core
from . import utils
from . import strategies
from . import mapping
from . import orchestrators
from . import enums
from . import digital_measures_verification
from . import data_collection

# Expose commonly used classes/functions at the package level
from .utils import Utilities, FileHandler, WarningManager, configure_logger
from .strategies import StrategyFactory
from .factories import DataClassFactory
from .dataclass_models.concrete_dataclasses import (
    CategoryInfo,
    GlobalFacultyStats,
    FacultyInfo,
    FacultyStats,
    CrossrefArticleDetails,
    CrossrefArticleStats,
)
from .core import (
    CategoryProcessor,
    FacultyPostprocessor,
    NameVariation,
)
from .enums import AttributeTypes

from .data_collection.CrossrefWrapper import CrossrefWrapper
