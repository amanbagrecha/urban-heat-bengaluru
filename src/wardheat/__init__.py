"""wardheat — ward-level urban heat risk mapping and early response (Bengaluru workshop)."""

import os as _os

# Sensible GDAL defaults for reading cloud-optimised data over flaky networks:
# never hang forever on one HTTP request, retry transient failures, and skip
# directory listings that COG reads do not need.
for _k, _v in {
    "GDAL_HTTP_TIMEOUT": "60",
    "GDAL_HTTP_CONNECTTIMEOUT": "20",
    "GDAL_HTTP_MAX_RETRY": "4",
    "GDAL_HTTP_RETRY_DELAY": "2",
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_HTTP_MULTIRANGE": "YES",
}.items():
    _os.environ.setdefault(_k, _v)

__version__ = "0.1.0"
