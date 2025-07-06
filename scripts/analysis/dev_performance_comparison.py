#!/usr/bin/env python
"""
Test script to compare performance between dict-based and direct LocationGroup approaches
"""
import os
import sys
import django
import time
import requests

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from checker.models import LocationGroup


def test_search_performance():
    """Compare performance of both search approaches"""
    
    # Test queries
    test_queries = [
        "battery",
        "gridbeyond", 
        "energy centre",
        "london",
        "SW11"
    ]
    
    print("Performance Comparison: Dict-based vs Direct LocationGroup")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)
        
        # Test current dict-based approach
        start = time.time()
        response1 = requests.get(f"http://localhost:8000/?q={query}&per_page=50")
        dict_time = time.time() - start
        
        # Test optimized direct approach
        start = time.time()
        response2 = requests.get(f"http://localhost:8000/search-optimized/?q={query}&per_page=50")
        direct_time = time.time() - start
        
        # Extract timing from response if available
        print(f"Dict-based approach: {dict_time:.2f}s (Status: {response1.status_code})")
        print(f"Direct LocationGroup: {direct_time:.2f}s (Status: {response2.status_code})")
        print(f"Speed improvement: {(dict_time - direct_time):.2f}s ({(1 - direct_time/dict_time)*100:.1f}% faster)")
        
        # Check LocationGroup count for this query
        from django.db.models import Q
        filter_q = Q(location__icontains=query) | Q(companies__icontains=query) | Q(descriptions__icontains=query)
        lg_count = LocationGroup.objects.filter(filter_q).count()
        print(f"LocationGroups matching query: {lg_count}")


if __name__ == "__main__":
    print("\nNOTE: Make sure the Django development server is running on localhost:8000")
    print("Run with: python manage.py runserver\n")
    
    try:
        test_search_performance()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to localhost:8000. Is the server running?")
    except Exception as e:
        print(f"ERROR: {e}")