from django.core.management.base import BaseCommand
from django.db import transaction
from checker.models import Component

class Command(BaseCommand):
    help = 'Repair corrupted CMU IDs using data from additional_data field'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )
        parser.add_argument(
            '--cmu-id',
            type=str,
            help='Fix only components with this specific corrupted CMU ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_cmu = options['cmu_id']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        self.stdout.write('=' * 60)
        self.stdout.write('CMU ID CORRUPTION REPAIR TOOL')
        self.stdout.write('=' * 60)
        
        # Define suspected corrupted CMU IDs
        corrupted_cmu_ids = ['hull road', 'church road', 'TS16', 'lime', 'Drax', 'T_ABERTHAW-1', 'TS24_3']
        
        if specific_cmu:
            corrupted_cmu_ids = [specific_cmu]
            self.stdout.write(f'Targeting specific CMU ID: {specific_cmu}')
        
        repairs_needed = []
        company_updates = []
        
        # 1. Identify components needing repair
        self.stdout.write('\n1. IDENTIFYING CORRUPTED COMPONENTS...')
        self.stdout.write('-' * 40)
        
        for corrupted_cmu in corrupted_cmu_ids:
            components = Component.objects.filter(cmu_id=corrupted_cmu)
            
            for comp in components:
                if comp.additional_data and comp.additional_data.get('CMU ID'):
                    stored_cmu = comp.cmu_id
                    actual_cmu = comp.additional_data.get('CMU ID')
                    
                    if stored_cmu != actual_cmu:
                        # Check if we can get company name from a component with correct CMU ID
                        correct_components = Component.objects.filter(cmu_id=actual_cmu).exclude(company_name__isnull=True).exclude(company_name='')
                        correct_company = None
                        
                        if correct_components.exists():
                            correct_company = correct_components.first().company_name
                        
                        repair_info = {
                            'component_id': comp.id,
                            'current_cmu': stored_cmu,
                            'correct_cmu': actual_cmu,
                            'current_company': comp.company_name,
                            'correct_company': correct_company,
                            'location': comp.location[:50] if comp.location else 'No location'
                        }
                        repairs_needed.append(repair_info)
                        
                        if correct_company and not comp.company_name:
                            company_updates.append(repair_info)
        
        self.stdout.write(f'Found {len(repairs_needed)} components needing CMU ID repair')
        self.stdout.write(f'Found {len(company_updates)} components that will get company names')
        
        if not repairs_needed:
            self.stdout.write(self.style.SUCCESS('✅ No corrupted components found!'))
            return
        
        # 2. Show sample of what will be fixed
        self.stdout.write('\n2. SAMPLE REPAIRS...')
        self.stdout.write('-' * 20)
        
        for repair in repairs_needed[:5]:
            self.stdout.write(f'Component {repair["component_id"]}:')
            self.stdout.write(f'  CMU: "{repair["current_cmu"]}" → "{repair["correct_cmu"]}"')
            if repair['correct_company']:
                company_change = f'"{repair["current_company"] or "[MISSING]"}" → "{repair["correct_company"]}"'
                self.stdout.write(f'  Company: {company_change}')
            self.stdout.write(f'  Location: {repair["location"]}')
            self.stdout.write('')
        
        if len(repairs_needed) > 5:
            self.stdout.write(f'... and {len(repairs_needed) - 5} more')
        
        # 3. Perform repairs
        if not dry_run:
            self.stdout.write('\n3. PERFORMING REPAIRS...')
            self.stdout.write('-' * 25)
            
            with transaction.atomic():
                success_count = 0
                error_count = 0
                
                for repair in repairs_needed:
                    try:
                        component = Component.objects.get(id=repair['component_id'])
                        
                        # Update CMU ID
                        component.cmu_id = repair['correct_cmu']
                        
                        # Update company name if we have correct data
                        if repair['correct_company'] and not component.company_name:
                            component.company_name = repair['correct_company']
                        
                        component.save()
                        success_count += 1
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error fixing component {repair["component_id"]}: {e}'))
                        error_count += 1
                
                self.stdout.write(f'✅ Successfully repaired: {success_count} components')
                if error_count > 0:
                    self.stdout.write(self.style.ERROR(f'❌ Errors: {error_count} components'))
        
        # 4. Summary
        self.stdout.write('\n4. SUMMARY...')
        self.stdout.write('-' * 12)
        
        cmu_summary = {}
        for repair in repairs_needed:
            correct_cmu = repair['correct_cmu']
            if correct_cmu not in cmu_summary:
                cmu_summary[correct_cmu] = 0
            cmu_summary[correct_cmu] += 1
        
        self.stdout.write('Components by correct CMU ID:')
        for cmu_id, count in sorted(cmu_summary.items()):
            self.stdout.write(f'  {cmu_id}: {count} components')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN COMPLETE - Run without --dry-run to apply fixes'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ REPAIR COMPLETE'))
            self.stdout.write('Recommendation: Clear cache and rebuild indexes after repair')