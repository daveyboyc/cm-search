from django.core.management.base import BaseCommand
from ads.models import AdPlacement

class Command(BaseCommand):
    help = 'Set up new ad placement configurations'

    def handle(self, *args, **options):
        placements = [
            {
                'name': 'header_banner',
                'placement_type': 'banner_top',
                'size': 'responsive',
                'show_on_search': True,
                'show_on_map': True,
                'show_on_list': True,
                'show_on_detail': True,
            },
            {
                'name': 'sidebar_banner',
                'placement_type': 'search_sidebar',
                'size': '300x250',
                'show_on_search': True,
                'show_on_map': True,
                'show_on_list': True,
                'show_on_detail': True,
            },
            {
                'name': 'footer_banner',
                'placement_type': 'banner_bottom',
                'size': 'responsive',
                'show_on_search': True,
                'show_on_map': True,
                'show_on_list': True,
                'show_on_detail': True,
            },
            {
                'name': 'mobile_banner',
                'placement_type': 'banner_top',
                'size': 'responsive',
                'show_on_search': True,
                'show_on_map': True,
                'show_on_list': True,
                'show_on_detail': True,
            },
            {
                'name': 'technology_detail',
                'placement_type': 'list_inline',
                'size': 'responsive',
                'show_on_search': False,
                'show_on_map': False,
                'show_on_list': True,
                'show_on_detail': True,
            },
            {
                'name': 'company_detail',
                'placement_type': 'list_inline',
                'size': 'responsive',
                'show_on_search': False,
                'show_on_map': False,
                'show_on_list': True,
                'show_on_detail': True,
            },
            {
                'name': 'list_bottom',
                'placement_type': 'banner_bottom',
                'size': 'responsive',
                'show_on_search': True,
                'show_on_map': False,
                'show_on_list': True,
                'show_on_detail': False,
            },
            {
                'name': 'nav_banner',
                'placement_type': 'banner_top',
                'size': 'responsive',
                'show_on_search': True,
                'show_on_map': True,
                'show_on_list': True,
                'show_on_detail': True,
            },
            {
                'name': 'header_compact',
                'placement_type': 'banner_top',
                'size': '728x90',
                'show_on_search': True,
                'show_on_map': True,
                'show_on_list': True,
                'show_on_detail': True,
            },
            {
                'name': 'map_popup',
                'placement_type': 'map_overlay',
                'size': '300x250',
                'show_on_search': True,
                'show_on_map': True,
                'show_on_list': False,
                'show_on_detail': False,
            },
            # Detail page specific ads
            {
                'name': 'component_takeover',
                'placement_type': 'map_overlay',
                'size': '400x300',
                'show_on_search': False,
                'show_on_map': False,
                'show_on_list': False,
                'show_on_detail': True,
            },
            {
                'name': 'location_takeover',
                'placement_type': 'map_overlay',
                'size': '400x300',
                'show_on_search': False,
                'show_on_map': False,
                'show_on_list': False,
                'show_on_detail': True,
            },
            {
                'name': 'detail_sidebar_left',
                'placement_type': 'search_sidebar',
                'size': '160x600',
                'show_on_search': False,
                'show_on_map': False,
                'show_on_list': False,
                'show_on_detail': True,
            },
            {
                'name': 'detail_sidebar_right',
                'placement_type': 'search_sidebar',
                'size': '160x600',
                'show_on_search': False,
                'show_on_map': False,
                'show_on_list': False,
                'show_on_detail': True,
            },
            {
                'name': 'detail_banner',
                'placement_type': 'banner_top',
                'size': '728x90',
                'show_on_search': False,
                'show_on_map': False,
                'show_on_list': False,
                'show_on_detail': True,
            },
        ]

        created_count = 0
        updated_count = 0

        for placement_data in placements:
            placement, created = AdPlacement.objects.get_or_create(
                name=placement_data['name'],
                defaults={
                    'placement_type': placement_data['placement_type'],
                    'size': placement_data['size'],
                    'ad_unit_id': '',  # Will be set when real AdSense units are created
                    'is_active': True,
                    'show_on_search': placement_data['show_on_search'],
                    'show_on_map': placement_data['show_on_map'],
                    'show_on_list': placement_data['show_on_list'],
                    'show_on_detail': placement_data['show_on_detail'],
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created ad placement: {placement.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Ad placement already exists: {placement.name}')
                )

        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'📊 Summary:')
        self.stdout.write(f'   Created: {created_count} new placements')
        self.stdout.write(f'   Existing: {updated_count} placements')
        self.stdout.write(f'   Total: {len(placements)} placements configured')
        
        if created_count > 0:
            self.stdout.write('\n🔧 Next steps:')
            self.stdout.write('   1. Create corresponding AdSense ad units in Google AdSense')
            self.stdout.write('   2. Update ad_unit_id fields with real AdSense unit IDs')
            self.stdout.write('   3. Add placement template tags to relevant pages')
            self.stdout.write('   4. Test with ADSENSE_ENABLED=true locally')
            
        self.stdout.write('\n📖 For more information, see: AD_PLACEMENT_GUIDE.md')