#!/bin/bash
# Test API performance with the new fast location lookups

echo "🚀 Testing API Performance"
echo "=========================="

# Test server URL (adjust if needed)
BASE_URL="http://localhost:8000"

echo -e "\n📍 Testing SW11 search (the problematic one)..."
time curl -s "$BASE_URL/search/?q=SW11" -o /dev/null -w "Status: %{http_code}, Time: %{time_total}s\n"

echo -e "\n📍 Testing location searches..."
for location in "nottingham" "peckham" "battersea"; do
    echo -n "  $location: "
    time curl -s "$BASE_URL/search/?q=$location" -o /dev/null -w "Status: %{http_code}, Time: %{time_total}s\n"
done

echo -e "\n📍 Testing map API..."
echo -n "  Map data: "
time curl -s "$BASE_URL/api/map/technology/" -o /dev/null -w "Status: %{http_code}, Time: %{time_total}s\n"

echo -e "\n✅ All tests complete!"