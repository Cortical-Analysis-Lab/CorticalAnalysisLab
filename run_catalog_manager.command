#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m pip install -r scripts/requirements.txt
exec python3 local_catalog_manager.py
