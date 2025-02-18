import logging
import sys

import pendulum
import uvicorn
from lnlp.api.app import app

# Configure logging to output to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.info('Starting Libb-NLP API - Comprehensive NLP Services')
    logger.info(f'System timezone: {pendulum.now().timezone_name}')
    uvicorn.run(app, host='0.0.0.0', port=8000)
