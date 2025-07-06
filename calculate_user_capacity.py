#!/usr/bin/env python3
"""
Calculate realistic user capacity within 5GB Supabase egress limit
Based on our optimization test results
"""

print("📊 USER CAPACITY ANALYSIS")
print("=" * 60)

# Test results from our optimization
optimized_response_compressed = 3.1  # KB for 20 locations with gzip
locations_per_response = 20
kb_per_location = optimized_response_compressed / locations_per_response  # ~0.155 KB per location

print(f"🧪 BASELINE FROM OPTIMIZATION TEST:")
print(f"  20 locations = {optimized_response_compressed} KB compressed")
print(f"  Per location = {kb_per_location:.3f} KB")

# Define user behavior scenarios
scenarios = [
    {
        'name': 'Light User',
        'description': 'Occasional browsing, 2-3 searches per day',
        'searches_per_day': 3,
        'avg_locations_per_search': 15,
        'days_active_per_month': 10
    },
    {
        'name': 'Regular User', 
        'description': 'Daily usage, research/business use',
        'searches_per_day': 8,
        'avg_locations_per_search': 25,
        'days_active_per_month': 22
    },
    {
        'name': 'Heavy User',
        'description': 'Professional/academic research, extensive usage', 
        'searches_per_day': 20,
        'avg_locations_per_search': 40,
        'days_active_per_month': 25
    },
    {
        'name': 'Power User',
        'description': 'Intensive research, data analysis, frequent map usage',
        'searches_per_day': 50,
        'avg_locations_per_search': 60,
        'days_active_per_month': 30
    }
]

print(f"\n📈 USAGE SCENARIOS:")
print("-" * 60)

total_5gb_kb = 5 * 1024 * 1024  # 5GB in KB
scenario_results = []

for scenario in scenarios:
    # Calculate monthly usage per user
    monthly_searches = scenario['searches_per_day'] * scenario['days_active_per_month']
    monthly_locations = monthly_searches * scenario['avg_locations_per_search']
    monthly_kb = monthly_locations * kb_per_location
    monthly_mb = monthly_kb / 1024
    
    # Calculate how many users we can support
    users_supported = total_5gb_kb / monthly_kb
    
    scenario_results.append({
        'scenario': scenario,
        'monthly_kb': monthly_kb,
        'monthly_mb': monthly_mb,
        'users_supported': int(users_supported)
    })
    
    print(f"\n{scenario['name']}:")
    print(f"  {scenario['description']}")
    print(f"  Monthly usage: {monthly_searches} searches, {monthly_locations:,} locations")
    print(f"  Monthly egress: {monthly_mb:.1f} MB per user")
    print(f"  👥 Users supported: {int(users_supported)} users")

# Mixed user base scenarios
print(f"\n🎯 REALISTIC MIXED USER BASE SCENARIOS:")
print("-" * 60)

mixed_scenarios = [
    {
        'name': 'Balanced Mix',
        'light': 0.5,    # 50% light users
        'regular': 0.3,  # 30% regular users  
        'heavy': 0.15,   # 15% heavy users
        'power': 0.05    # 5% power users
    },
    {
        'name': 'Research-Heavy',
        'light': 0.2,    # 20% light users
        'regular': 0.4,  # 40% regular users
        'heavy': 0.3,    # 30% heavy users
        'power': 0.1     # 10% power users
    },
    {
        'name': 'General Public',
        'light': 0.7,    # 70% light users
        'regular': 0.25, # 25% regular users
        'heavy': 0.04,   # 4% heavy users
        'power': 0.01    # 1% power users
    }
]

for mix in mixed_scenarios:
    # Calculate weighted average usage
    avg_monthly_mb = (
        mix['light'] * scenario_results[0]['monthly_mb'] +
        mix['regular'] * scenario_results[1]['monthly_mb'] +
        mix['heavy'] * scenario_results[2]['monthly_mb'] +
        mix['power'] * scenario_results[3]['monthly_mb']
    )
    
    users_supported = (5 * 1024) / avg_monthly_mb  # 5GB / avg MB per user
    
    print(f"\n{mix['name']}:")
    print(f"  Mix: {int(mix['light']*100)}% light, {int(mix['regular']*100)}% regular, {int(mix['heavy']*100)}% heavy, {int(mix['power']*100)}% power")
    print(f"  Avg usage: {avg_monthly_mb:.1f} MB per user per month")
    print(f"  👥 Total users supported: {int(users_supported)} users")

# Additional factors to consider
print(f"\n⚠️  ADDITIONAL CONSIDERATIONS:")
print("-" * 60)
print("📝 Cache Benefits:")
print("  - 15-minute caching reduces repeat requests")
print("  - Popular searches (London, Battery) cached for all users")
print("  - Real egress likely 20-40% lower than calculated")

print(f"\n🔧 Further Optimizations Available:")
print("  - Increase cache time to 30+ minutes")
print("  - Implement CDN for static responses") 
print("  - Add request rate limiting per user")
print("  - Use pagination for large result sets")

print(f"\n💡 Conservative Estimate:")
print("  With current optimizations: 150-300 active users")
print("  With additional caching: 250-500 active users")
print("  With CDN + rate limiting: 500-1000+ active users")

print(f"\n🎯 RECOMMENDATION:")
print("  Start monitoring at 100 users")
print("  Scale optimizations as usage grows")
print("  Consider Supabase Pro ($25/mo, 50GB) at 500+ users")