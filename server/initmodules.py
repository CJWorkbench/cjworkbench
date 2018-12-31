import glob
import logging
import os
import json
from cjworkbench.settings import BASE_DIR
from server.models import ModuleVersion


logger = logging.getLogger(__name__)


# Top level call, (re)load module definitions from files.
# Raises on error.
def init_modules():
    module_path = os.path.join(BASE_DIR, 'server/modules')

    json_paths = glob.glob(f'{module_path}/*.json')

    for json_path in json_paths:
        # Raises OSError
        with open(json_path, 'rb') as json_bytes:
            # Raises ValueError
            spec = json.load(json_bytes)

        # Raises all sorts of exceptions
        ModuleVersion.create_or_replace_from_spec(spec,
                                                  source_version_hash='1.0',
                                                  js_module='')

    logger.info('Loaded %d modules', len(json_paths))
