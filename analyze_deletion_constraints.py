#!/usr/bin/env python
"""
Script to analyze what might prevent user deletion.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'capacity_checker.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile, RegistrationEmailRecord
from django.db import connection

def analyze_user_constraints(email):
    """Analyze what might prevent deletion of a user"""
    
    print(f"=== Analyzing deletion constraints for {email} ===\n")
    
    try:
        user = User.objects.get(username=email)
        print(f"✓ User found: {user.username} (ID: {user.id})")
    except User.DoesNotExist:
        print(f"✗ No user found with username: {email}")
        return
    
    # Check related objects that might prevent deletion
    print("\n=== Checking related objects ===")
    
    # 1. UserProfile (should cascade delete)
    try:
        profile = user.profile
        print(f"✓ UserProfile exists: {profile}")
        print(f"  - Relationship: CASCADE (should delete automatically)")
    except UserProfile.DoesNotExist:
        print("- No UserProfile found")
    
    # 2. Check for any other potential foreign key relationships
    print("\n=== Checking for other foreign key references ===")
    
    # Get all models that might reference User
    from django.apps import apps
    
    user_references = []
    for model in apps.get_models():
        for field in model._meta.get_fields():
            if hasattr(field, 'related_model') and field.related_model == User:
                # This field references User
                if hasattr(field, 'on_delete'):
                    on_delete_behavior = getattr(field, 'on_delete', 'UNKNOWN')
                else:
                    on_delete_behavior = 'N/A (many-to-many or reverse relation)'
                
                # Check if this user has any records in this model
                if hasattr(field, 'name'):
                    field_name = field.name
                else:
                    field_name = field.related_name or 'user'
                
                try:
                    related_objects = model.objects.filter(**{field_name: user})
                    count = related_objects.count()
                    if count > 0:
                        user_references.append({
                            'model': model.__name__,
                            'field': field_name,
                            'count': count,
                            'on_delete': str(on_delete_behavior),
                            'objects': list(related_objects[:5])  # Show first 5
                        })
                except Exception as e:
                    # Skip if field doesn't work as expected
                    pass
    
    if user_references:
        print(f"Found {len(user_references)} model(s) with references to this user:")
        for ref in user_references:
            print(f"  ➤ {ref['model']}.{ref['field']}: {ref['count']} record(s)")
            print(f"    On Delete: {ref['on_delete']}")
            if ref['count'] < 6:
                for obj in ref['objects']:
                    print(f"    - {obj}")
            else:
                for obj in ref['objects']:
                    print(f"    - {obj}")
                print(f"    ... and {ref['count'] - 5} more")
            print()
    else:
        print("No other foreign key references found")
    
    # 3. Check database constraints directly
    print("\n=== Checking database constraints ===")
    
    with connection.cursor() as cursor:
        # Check for foreign key constraints in PostgreSQL
        if 'postgresql' in connection.settings_dict['ENGINE']:
            cursor.execute("""
                SELECT 
                    tc.constraint_name,
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM 
                    information_schema.table_constraints AS tc 
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                  AND ccu.table_name = 'auth_user'
            """)
            
            constraints = cursor.fetchall()
            if constraints:
                print("Foreign key constraints referencing auth_user:")
                for constraint in constraints:
                    print(f"  - {constraint[1]}.{constraint[2]} → auth_user.{constraint[4]} ({constraint[0]})")
            else:
                print("No foreign key constraints found referencing auth_user")
        else:
            print("Database constraint analysis only available for PostgreSQL")

def test_deletion_safety(email):
    """Test if the user can be safely deleted"""
    print(f"\n=== Testing deletion safety for {email} ===")
    
    try:
        user = User.objects.get(username=email)
        
        # Try a dry run to see what would be deleted
        print("Performing dry-run deletion check...")
        
        from django.db.models.deletion import Collector
        from django.db import DEFAULT_DB_ALIAS
        
        collector = Collector(using=DEFAULT_DB_ALIAS)
        collector.collect([user])
        
        print(f"Objects that would be deleted:")
        for model, instances in collector.data.items():
            print(f"  - {model.__name__}: {len(instances)} instance(s)")
            for instance in list(instances)[:3]:  # Show first 3
                print(f"    * {instance}")
            if len(instances) > 3:
                print(f"    ... and {len(instances) - 3} more")
        
        if collector.protected:
            print(f"\n⚠️  PROTECTED objects (would prevent deletion):")
            for obj in collector.protected:
                print(f"  - {obj}")
        else:
            print("\n✅ No protected objects - deletion should be safe")
            
    except User.DoesNotExist:
        print(f"✗ User {email} not found")

if __name__ == "__main__":
    email = "davidcrawford83@gmail.com"
    analyze_user_constraints(email)
    test_deletion_safety(email)