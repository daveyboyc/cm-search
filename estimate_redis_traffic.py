#!/usr/bin/env python3
"""
Estimate the Redis network traffic from startup cache loading
"""
import sys
import pickle
import base64

# Estimate sizes based on what we know:

# 1. CMU Dataframe (15,980 records)
# Each record has multiple fields, serialized with pickle + base64
cmu_records = 15980
cmu_fields_per_record = 6  # CMU ID, Company Name, etc.
cmu_avg_field_size = 50  # bytes
cmu_raw_size = cmu_records * cmu_fields_per_record * cmu_avg_field_size
cmu_pickle_overhead = 1.5  # pickle adds overhead
cmu_base64_overhead = 1.33  # base64 encoding adds 33%
cmu_total_size = cmu_raw_size * cmu_pickle_overhead * cmu_base64_overhead

print("CMU Dataframe:")
print(f"  Records: {cmu_records:,}")
print(f"  Raw size: {cmu_raw_size / (1024**2):.2f} MB")
print(f"  With pickle + base64: {cmu_total_size / (1024**2):.2f} MB")

# 2. Company Index (1,557 companies)
company_count = 1557
company_data_size = 500  # bytes per company (name, URLs, etc.)
company_raw_size = company_count * company_data_size
company_pickle_overhead = 1.5
company_base64_overhead = 1.33
company_total_size = company_raw_size * company_pickle_overhead * company_base64_overhead

print("\nCompany Index:")
print(f"  Companies: {company_count:,}")
print(f"  Raw size: {company_raw_size / (1024**2):.2f} MB")
print(f"  With pickle + base64: {company_total_size / (1024**2):.2f} MB")

# 3. Location Mapping (14,593 locations)
location_count = 14593
postcodes_per_location = 10  # average
postcode_size = 10  # bytes
location_name_size = 30  # bytes
location_raw_size = location_count * (location_name_size + (postcodes_per_location * postcode_size))
location_pickle_overhead = 1.5
location_base64_overhead = 1.33
location_total_size = location_raw_size * location_pickle_overhead * location_base64_overhead

print("\nLocation Mapping:")
print(f"  Locations: {location_count:,}")
print(f"  Raw size: {location_raw_size / (1024**2):.2f} MB")
print(f"  With pickle + base64: {location_total_size / (1024**2):.2f} MB")

# Total per startup
total_per_startup = cmu_total_size + company_total_size + location_total_size
print(f"\nTOTAL PER STARTUP: {total_per_startup / (1024**2):.2f} MB")

# Estimate dyno restarts
# Free/Basic dynos restart at least once per day
# Plus restarts on deploy, errors, etc.
restarts_per_day = 50  # Conservative estimate based on logs
days_active = 3  # Since deployment
total_restarts = restarts_per_day * days_active

total_traffic = total_per_startup * total_restarts
print(f"\nESTIMATED TRAFFIC:")
print(f"  Restarts: {total_restarts}")
print(f"  Traffic per restart: {total_per_startup / (1024**2):.2f} MB")
print(f"  Total traffic: {total_traffic / (1024**3):.2f} GB")

# Add search result caching
print("\nADDITIONAL TRAFFIC SOURCES:")
print("  - Search result caching (disabled in emergency mode)")
print("  - Map data caching (disabled in emergency mode)")
print("  - Session data")
print("  - Each page request may trigger multiple cache checks")