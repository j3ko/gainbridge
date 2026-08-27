#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python app/backend_pre_start.py

# Bridge databases created before Alembic tracked schema
python app/stamp_legacy_db.py

# Run migrations
alembic upgrade head
