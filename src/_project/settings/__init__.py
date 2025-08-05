from .core_settings import *

try:
    from .local_settings import *
except ImportError:
    from .logging_settings import *