#!/usr/bin/env python3
import redis
import os
import json
from urllib.parse import urlparse

# Parse Redis URL
redis_url = os.environ.get('REDISCLOUD_URL', '')
if not redis_url:
    print("No REDISCLOUD_URL found")
    exit(1)

parsed = urlparse(redis_url)

# Connect to Redis
r = redis.Redis(
    host=parsed.hostname,
    port=parsed.port,
    password=parsed.password,
    decode_responses=True
)

# Get info
info = r.info()
memory_info = r.info('memory')
stats_info = r.info('stats')
keyspace_info = r.info('keyspace')

print("=== REDIS USAGE REPORT ===\n")

print("MEMORY:")
print(f"  Used Memory: {memory_info.get('used_memory_human', 'N/A')}")
print(f"  Memory RSS: {memory_info.get('used_memory_rss_human', 'N/A')}")
print(f"  Memory Peak: {memory_info.get('used_memory_peak_human', 'N/A')}")
print(f"  Memory Fragmentation: {memory_info.get('mem_fragmentation_ratio', 'N/A')}")

print("\nNETWORK STATS:")
print(f"  Total Commands Processed: {stats_info.get('total_commands_processed', 0):,}")
print(f"  Network Traffic In: {stats_info.get('total_net_input_bytes', 0) / (1024**3):.2f} GB")
print(f"  Network Traffic Out: {stats_info.get('total_net_output_bytes', 0) / (1024**3):.2f} GB")
print(f"  Total Network Traffic: {(stats_info.get('total_net_input_bytes', 0) + stats_info.get('total_net_output_bytes', 0)) / (1024**3):.2f} GB")

print("\nKEYSPACE:")
total_keys = 0
for db_name, db_info in keyspace_info.items():
    if db_name.startswith('db'):
        keys = int(db_info.get('keys', 0))
        total_keys += keys
        print(f"  {db_name}: {keys} keys")
print(f"  Total Keys: {total_keys}")

print("\nKEY PATTERNS:")
# Sample some keys to understand what's taking space
sample_keys = r.randomkey() if total_keys > 0 else None
if sample_keys:
    keys_sample = []
    for _ in range(min(20, total_keys)):
        key = r.randomkey()
        if key:
            key_type = r.type(key)
            if key_type == 'string':
                size = len(r.get(key) or '')
            elif key_type == 'hash':
                size = r.hlen(key)
            elif key_type == 'list':
                size = r.llen(key)
            elif key_type == 'set':
                size = r.scard(key)
            elif key_type == 'zset':
                size = r.zcard(key)
            else:
                size = 0
            keys_sample.append((key, key_type, size))
    
    print("\n  Sample Keys (name, type, size):")
    for key, key_type, size in sorted(keys_sample, key=lambda x: x[2], reverse=True)[:10]:
        print(f"    {key[:50]}... ({key_type}): {size:,}")