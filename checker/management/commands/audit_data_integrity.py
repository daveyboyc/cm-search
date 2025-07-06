from django.core.management.base import BaseCommand
from checker.models import Component
from checker.services.data_access import get_cmu_dataframe

class Command(BaseCommand):
    help = 'Audit database for data integrity issues'

    def handle(self, *args, **options):
        self.stdout.write('=' * 60)
        self.stdout.write('DATA INTEGRITY AUDIT REPORT')
        self.stdout.write('=' * 60)
        
        # 1. Check for CMU ID corruption
        self.stdout.write('\n1. CHECKING FOR CMU ID CORRUPTION...')
        self.stdout.write('-' * 40)
        
        corrupted_components = []
        suspicious_cmu_ids = ['hull road', 'church road', 'TS16', 'lime', 'Drax']
        
        for cmu_id in suspicious_cmu_ids:
            components = Component.objects.filter(cmu_id=cmu_id)[:10]
            
            for comp in components:
                if comp.additional_data and comp.additional_data.get('CMU ID'):
                    stored_cmu = comp.cmu_id
                    actual_cmu = comp.additional_data.get('CMU ID')
                    if stored_cmu != actual_cmu:
                        corrupted_components.append({
                            'id': comp.id,
                            'stored': stored_cmu,
                            'actual': actual_cmu,
                            'company': comp.company_name or '[MISSING]',
                            'location': comp.location[:40] if comp.location else 'No location'
                        })
        
        self.stdout.write(f'Found {len(corrupted_components)} confirmed corruption cases')
        
        if corrupted_components:
            self.stdout.write('\nCorruption examples:')
            for case in corrupted_components[:5]:
                self.stdout.write(f'- ID {case["id"]}: "{case["stored"]}" should be "{case["actual"]}"')
                self.stdout.write(f'  Company: {case["company"]} | Location: {case["location"]}')
        
        # 2. Check company data sources
        self.stdout.write('\n2. CHECKING COMPANY DATA SOURCES...')
        self.stdout.write('-' * 40)
        
        # Check CMU Registry
        cmu_df, _ = get_cmu_dataframe()
        octo13_registry = cmu_df[cmu_df['CMU ID'] == 'OCTO13']
        
        self.stdout.write(f'OCTO13 in CMU Registry: {len(octo13_registry)} entries')
        
        if not octo13_registry.empty:
            first_entry = octo13_registry.iloc[0]
            company = first_entry.get('Name of Applicant', '[MISSING]')
            self.stdout.write(f'Registry company: {company}')
        
        # Check correct components
        correct_octo13 = Component.objects.filter(cmu_id='OCTO13')
        self.stdout.write(f'Correct OCTO13 components: {correct_octo13.count()}')
        
        if correct_octo13.exists():
            sample = correct_octo13.first()
            self.stdout.write(f'Component company: {sample.company_name or "[MISSING]"}')
        
        # 3. Corruption scope
        self.stdout.write('\n3. CORRUPTION SCOPE...')
        self.stdout.write('-' * 25)
        
        total_affected = 0
        for cmu_id in suspicious_cmu_ids:
            count = Component.objects.filter(cmu_id=cmu_id).count()
            total_affected += count
            self.stdout.write(f'"{cmu_id}": {count} components')
        
        total_components = Component.objects.count()
        corruption_rate = (total_affected / total_components) * 100
        
        self.stdout.write(f'\nTotal affected: {total_affected:,} components')
        self.stdout.write(f'Corruption rate: {corruption_rate:.2f}%')
        
        # 4. Recommendations
        self.stdout.write('\n4. CRITICAL ACTIONS NEEDED...')
        self.stdout.write('-' * 30)
        self.stdout.write('1. 🐛 Fix bug in data_access.py line 781')
        self.stdout.write('2. 🔧 Create repair script for corrupted data')
        self.stdout.write('3. ✅ Add validation to prevent future corruption')
        self.stdout.write('4. 🔄 Re-import data with fixed code')
        
        if len(corrupted_components) > 0:
            self.stdout.write(self.style.ERROR(f'\n❌ CRITICAL: {len(corrupted_components)} corruption cases found!'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ No corruption detected in sample'))