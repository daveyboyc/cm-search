from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Count, Sum, Q
from checker.models import Component, LocationGroup
import time

class Command(BaseCommand):
    help = 'Build LocationGroup records using optimized bulk operations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch',
            type=int,
            default=100,
            help='Number of locations to process in this run (default: 100)',
        )

    def handle(self, *args, **options):
        start_time = time.time()
        batch_size = options['batch']
        
        # Get existing locations using raw SQL for speed
        with connection.cursor() as cursor:
            cursor.execute("SELECT location FROM checker_locationgroup")
            existing_locations = set(row[0] for row in cursor.fetchall())
        
        self.stdout.write(f"Found {len(existing_locations)} existing LocationGroups")
        
        # Get new locations to process using raw SQL
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT location 
                FROM checker_component 
                WHERE location IS NOT NULL 
                AND location != '' 
                AND location != 'None' 
                AND location != 'N/A'
                AND location != 'NA'
                AND location NOT LIKE '%%TBC%%'
                AND location NOT LIKE '%%to be confirmed%%'
                AND location NOT IN (SELECT location FROM checker_locationgroup)
                LIMIT %s
            """, [batch_size])
            
            locations_to_process = [row[0] for row in cursor.fetchall()]
        
        if not locations_to_process:
            self.stdout.write(self.style.SUCCESS("All locations already have LocationGroups!"))
            return
        
        self.stdout.write(f"Processing {len(locations_to_process)} new locations...")
        
        # Process all locations and prepare bulk insert data
        location_groups_to_create = []
        
        for i, location in enumerate(locations_to_process):
            if i % 10 == 0 and i > 0:
                self.stdout.write(f"Preparing {i}/{len(locations_to_process)}...")
            
            # Get aggregated data using raw SQL for speed
            with connection.cursor() as cursor:
                # Get basic counts and capacity
                cursor.execute("""
                    SELECT 
                        COUNT(*) as count,
                        SUM(derated_capacity_mw) as total_capacity,
                        MIN(id) as first_id
                    FROM checker_component 
                    WHERE location = %s
                """, [location])
                
                row = cursor.fetchone()
                if not row or row[0] == 0:
                    continue
                
                component_count = row[0]
                total_capacity = row[1] or 0.0
                first_id = row[2]
                
                # Get first component details for representative data
                cursor.execute("""
                    SELECT latitude, longitude, county, outward_code
                    FROM checker_component 
                    WHERE id = %s
                """, [first_id])
                
                comp_data = cursor.fetchone()
                lat, lon, county, outward = comp_data if comp_data else (None, None, None, None)
                
                # Get aggregated data as JSON (much faster than multiple queries)
                cursor.execute("""
                    SELECT 
                        array_to_json(array_agg(DISTINCT description)) as descriptions,
                        array_to_json(array_agg(DISTINCT technology)) as technologies,
                        array_to_json(array_agg(DISTINCT company_name)) as companies,
                        array_to_json(array_agg(DISTINCT auction_name ORDER BY auction_name DESC)) as auctions,
                        array_to_json(array_agg(DISTINCT cmu_id ORDER BY cmu_id)) as cmu_ids
                    FROM checker_component 
                    WHERE location = %s
                    AND description IS NOT NULL
                """, [location])
                
                agg_row = cursor.fetchone()
                
                # Parse the JSON results
                import json
                descriptions = agg_row[0] or []
                if isinstance(descriptions, str):
                    descriptions = json.loads(descriptions)
                descriptions = descriptions[:5]  # Limit to 5
                
                technologies = agg_row[1] or []
                if isinstance(technologies, str):
                    technologies = json.loads(technologies)
                    
                companies = agg_row[2] or []
                if isinstance(companies, str):
                    companies = json.loads(companies)
                    
                auctions = agg_row[3] or []
                if isinstance(auctions, str):
                    auctions = json.loads(auctions)
                auctions = auctions[:10]  # Limit to 10
                
                cmu_ids = agg_row[4] or []
                if isinstance(cmu_ids, str):
                    cmu_ids = json.loads(cmu_ids)
                
                # Convert to required format
                tech_dict = {t: 1 for t in technologies if t}  # Simple count
                company_dict = {c: 1 for c in companies if c}
            
            # Create LocationGroup instance (but don't save yet)
            lg = LocationGroup(
                location=location,
                component_count=component_count,
                descriptions=descriptions,
                technologies=tech_dict,
                companies=company_dict,
                auction_years=auctions,
                cmu_ids=cmu_ids,
                displayed_capacity_mw=total_capacity,
                normalized_capacity_mw=total_capacity,
                capacity_confidence='low' if total_capacity == 0 else 'medium',
                capacity_source='derated_capacity_mw',
                latitude=lat,
                longitude=lon,
                county=county,
                outward_code=outward
            )
            location_groups_to_create.append(lg)
        
        # Bulk create all LocationGroups in one transaction
        if location_groups_to_create:
            self.stdout.write(f"Bulk creating {len(location_groups_to_create)} LocationGroups...")
            with transaction.atomic():
                LocationGroup.objects.bulk_create(location_groups_to_create)
        
        # Final statistics
        new_total = LocationGroup.objects.count()
        
        # Get coverage using raw SQL for speed
        with connection.cursor() as cursor:
            cursor.execute("SELECT SUM(component_count) FROM checker_locationgroup")
            total_covered = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM checker_component")
            total_components = cursor.fetchone()[0] or 0
        
        coverage = (total_covered / total_components * 100) if total_components > 0 else 0
        
        elapsed = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(
                f"\nCompleted in {elapsed:.2f}s\n"
                f"Created: {len(location_groups_to_create)} new LocationGroups\n"
                f"Total LocationGroups: {new_total}\n"
                f"Component coverage: {coverage:.1f}%"
            )
        )
        
        if coverage >= 80:
            self.stdout.write(self.style.SUCCESS("🎉 LocationGroups are now ACTIVE! (80% coverage reached)"))