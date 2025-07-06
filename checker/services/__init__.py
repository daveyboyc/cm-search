# Import fast versions to override slow ones
try:
    # Try to import fast versions first
    from .postcode_helpers_fast import *
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Using FAST postcode helpers with static JSON files")
except ImportError:
    # Fall back to original if fast version not available
    from .postcode_helpers import *
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("Using slow postcode helpers - consider deploying static files")

# Import other services
from .component_search import *
from .company_search import *
from .location_search import *
from .data_access import *