# ruleid: smarthome-no-print-in-prod
print("debug")

import logging
logger = logging.getLogger(__name__)

# ok: smarthome-no-print-in-prod
logger.info("structured log")