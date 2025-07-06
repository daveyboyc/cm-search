#!/bin/bash
echo "Rebuilding all Redis caches..."
echo "1. Building location mapping (~14.5K locations)"
python manage.py build_location_mapping
echo "2. Building map cache (all technologies and zoom levels)"
python manage.py build_map_cache
echo "3. Verifying Redis cache status"
python manage.py check_cache_status
echo "Redis caches rebuilt successfully!" 