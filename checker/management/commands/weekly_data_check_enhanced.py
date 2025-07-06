"""
Enhanced weekly data monitoring command with actual crawl attempts.

This enhanced version actually attempts to crawl a small sample of data
to verify if there are real updates available, not just count differences.

Features:
- Performs targeted crawl of specific auction years
- Actually downloads sample records to verify new data
- Provides detailed results about what was found
- Much more informative email reports

Usage:
    python manage.py weekly_data_check_enhanced --email=user@example.com
    python manage.py weekly_data_check_enhanced --email=user@example.com --crawl-sample=10
"""
import json
import os
import time
from datetime import datetime, timezone, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone as django_timezone
from django.db import models
from checker.models import Component, CMURegistry
import requests
import pandas as pd


class Command(BaseCommand):
    help = 'Enhanced weekly data check that performs actual crawl attempts'
    
    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email address to send report to')
        parser.add_argument('--crawl-sample', type=int, default=5, help='Number of sample records to crawl')
        parser.add_argument('--dry-run', action='store_true', help='Run analysis without sending email')
        parser.add_argument('--focus-years', nargs='+', default=['2029-30', '2030-31'], 
                          help='Auction years to focus on for crawl attempts')
    
    def handle(self, *args, **options):
        start_time = datetime.now(timezone.utc)
        
        self.stdout.write(self.style.SUCCESS('📊 Enhanced Weekly Data Check with Crawl Attempts'))
        self.stdout.write(f'Started: {start_time.strftime("%Y-%m-%d %H:%M:%S UTC")}')
        
        # Get current database status
        data_status = self.get_current_data_status()
        
        # Check API for new data counts
        api_checks = self.check_api_for_new_data(options.get('focus_years'))
        
        # Perform actual crawl attempts
        crawl_results = self.perform_crawl_attempts(
            options.get('focus_years'),
            options.get('crawl_sample')
        )
        
        # Analyze all findings
        analysis = self.analyze_all_findings(data_status, api_checks, crawl_results)
        
        # Generate comprehensive report
        report = self.generate_enhanced_report(
            data_status, api_checks, crawl_results, analysis, start_time
        )
        
        # Send email if requested
        if options.get('email') and not options.get('dry_run'):
            self.send_enhanced_email(options['email'], report, analysis)
        
        # Save findings
        self.save_enhanced_findings(data_status, api_checks, crawl_results, analysis)
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        self.stdout.write(self.style.SUCCESS(f'✅ Enhanced check completed in {duration:.1f}s'))
        
        if options.get('dry_run'):
            self.stdout.write('\n📧 Email Report Preview:')
            self.stdout.write(report)
    
    def get_current_data_status(self):
        """Get current database status with more detail."""
        latest_component = Component.objects.order_by('-updated_at').first()
        
        # Get status for each auction year
        auction_details = {}
        for auction in Component.objects.values('auction_name', 'delivery_year').distinct():
            count = Component.objects.filter(
                auction_name=auction['auction_name'],
                delivery_year=auction['delivery_year']
            ).count()
            auction_details[f"{auction['auction_name']} ({auction['delivery_year']})"] = count
        
        return {
            'components': Component.objects.count(),
            'latest_update': latest_component.updated_at if latest_component else None,
            'auction_count': Component.objects.values('auction_name').distinct().count(),
            'auction_details': auction_details,
            'top_auctions': dict(
                Component.objects.values('auction_name')
                .annotate(count=models.Count('id'))
                .order_by('-count')[:10]
                .values_list('auction_name', 'count')
            ),
            'cmu_registry': {
                'total_cmus': CMURegistry.objects.count(),
                'latest_update': CMURegistry.objects.order_by('-last_updated').first().last_updated
                if CMURegistry.objects.exists() else None
            }
        }
    
    def check_api_for_new_data(self, focus_years):
        """Check NESO API for new data counts."""
        api_url = "https://data.nationalgrideso.com/api/3/action/datastore_search"
        component_resource_id = "790f5fa0-f8eb-4d82-b98d-0d34d3e404e8"
        
        checks = {}
        
        for year in focus_years:
            try:
                params = {
                    'resource_id': component_resource_id,
                    'q': year,
                    'limit': 5  # Get a few records to check
                }
                
                response = requests.get(api_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                api_count = data['result']['total']
                local_count = Component.objects.filter(delivery_year__icontains=year).count()
                
                # Extract sample records for comparison
                sample_records = []
                if data['result']['records']:
                    for record in data['result']['records'][:3]:
                        sample_records.append({
                            'cmu_id': record.get('CMU ID', 'Unknown'),
                            'company': record.get('Name of Applicant', 'Unknown'),
                            'technology': record.get('Technology Type', 'Unknown'),
                            'capacity': record.get('Adjusted De-rated Capacity (MW)', 0)
                        })
                
                checks[year] = {
                    'api_count': api_count,
                    'local_count': local_count,
                    'difference': api_count - local_count,
                    'status': 'new_data' if api_count > local_count else 'current',
                    'sample_records': sample_records
                }
                
            except Exception as e:
                checks[year] = {
                    'api_count': 'error',
                    'local_count': Component.objects.filter(delivery_year__icontains=year).count(),
                    'difference': 'unknown',
                    'status': f'error: {str(e)}',
                    'sample_records': []
                }
        
        return checks
    
    def perform_crawl_attempts(self, focus_years, sample_size):
        """Actually attempt to crawl sample data to verify availability."""
        self.stdout.write(self.style.WARNING(f'\n🔍 Attempting to crawl {sample_size} sample records...'))
        
        api_url = "https://data.nationalgrideso.com/api/3/action/datastore_search"
        component_resource_id = "790f5fa0-f8eb-4d82-b98d-0d34d3e404e8"
        
        crawl_results = {
            'attempted': 0,
            'successful': 0,
            'new_records': [],
            'updated_records': [],
            'errors': [],
            'details_by_year': {}
        }
        
        for year in focus_years:
            self.stdout.write(f'  Crawling {year}...')
            year_results = {
                'attempted': 0,
                'found_new': 0,
                'found_updated': 0,
                'sample_data': []
            }
            
            try:
                # Get sample records from API
                params = {
                    'resource_id': component_resource_id,
                    'filters': json.dumps({'Delivery Year': year}),
                    'limit': sample_size
                }
                
                response = requests.get(api_url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                if not data['result']['records']:
                    year_results['status'] = 'no_records'
                    crawl_results['details_by_year'][year] = year_results
                    continue
                
                # Process each record
                for record in data['result']['records']:
                    crawl_results['attempted'] += 1
                    year_results['attempted'] += 1
                    
                    # Extract key fields
                    cmu_id = record.get('CMU ID', '')
                    auction_name = record.get('Auction', '')
                    delivery_year = record.get('Delivery Year', '')
                    company = record.get('Name of Applicant', '')
                    technology = record.get('Technology Type', '')
                    capacity = record.get('Adjusted De-rated Capacity (MW)', 0)
                    
                    # Check if this record exists in our database
                    existing = Component.objects.filter(
                        cmu_id=cmu_id,
                        auction_name=auction_name,
                        delivery_year=delivery_year
                    ).first()
                    
                    record_info = {
                        'cmu_id': cmu_id,
                        'auction': f"{auction_name} ({delivery_year})",
                        'company': company[:50] + '...' if len(company) > 50 else company,
                        'technology': technology,
                        'capacity': capacity
                    }
                    
                    if not existing:
                        # This is a new record!
                        crawl_results['new_records'].append(record_info)
                        year_results['found_new'] += 1
                        record_info['status'] = 'NEW'
                    else:
                        # Check if it's been updated
                        if (existing.technology_type != technology or 
                            abs(float(existing.capacity_mw or 0) - float(capacity or 0)) > 0.01):
                            crawl_results['updated_records'].append(record_info)
                            year_results['found_updated'] += 1
                            record_info['status'] = 'UPDATED'
                        else:
                            record_info['status'] = 'UNCHANGED'
                    
                    year_results['sample_data'].append(record_info)
                    crawl_results['successful'] += 1
                
                year_results['status'] = 'success'
                
            except Exception as e:
                year_results['status'] = f'error: {str(e)}'
                crawl_results['errors'].append(f"{year}: {str(e)}")
            
            crawl_results['details_by_year'][year] = year_results
        
        return crawl_results
    
    def analyze_all_findings(self, data_status, api_checks, crawl_results):
        """Analyze all findings to determine actions needed."""
        analysis = {
            'summary': '',
            'action_needed': False,
            'new_data_confirmed': False,
            'recommendations': [],
            'priority': 'low'
        }
        
        # Check if we found actual new records
        if crawl_results['new_records']:
            analysis['new_data_confirmed'] = True
            analysis['action_needed'] = True
            analysis['priority'] = 'high'
            analysis['summary'] = f"🆕 CONFIRMED: {len(crawl_results['new_records'])} new records found!"
            analysis['recommendations'].append(
                f"Run full crawl for auction years: {', '.join([r['auction'] for r in crawl_results['new_records'][:3]])}"
            )
        
        # Check if we found updated records
        elif crawl_results['updated_records']:
            analysis['action_needed'] = True
            analysis['priority'] = 'medium'
            analysis['summary'] = f"📝 {len(crawl_results['updated_records'])} records have been updated"
            analysis['recommendations'].append("Consider running update crawl for modified records")
        
        # Check API count differences
        else:
            significant_diffs = []
            for year, check in api_checks.items():
                if isinstance(check.get('difference'), int) and check['difference'] > 0:
                    significant_diffs.append(f"{year}: +{check['difference']}")
            
            if significant_diffs:
                analysis['priority'] = 'medium'
                analysis['summary'] = f"📊 API shows more records: {', '.join(significant_diffs)}"
                analysis['recommendations'].append("Monitor next week for confirmation")
            else:
                analysis['summary'] = "✅ Database appears current with API"
        
        # Add data freshness analysis
        if data_status['latest_update']:
            age_days = (datetime.now(timezone.utc) - data_status['latest_update']).days
            if age_days > 14:
                analysis['recommendations'].append(f"⚠️ Data is {age_days} days old - consider refresh")
                analysis['priority'] = max(analysis['priority'], 'medium')
        
        return analysis
    
    def generate_enhanced_report(self, data_status, api_checks, crawl_results, analysis, start_time):
        """Generate detailed report with crawl results."""
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        report = f"""📊 ENHANCED WEEKLY DATA CHECK WITH CRAWL VERIFICATION
Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
Duration: {duration:.1f}s

🎯 EXECUTIVE SUMMARY
{analysis['summary']}
Priority: {analysis['priority'].upper()}
Action Needed: {'YES' if analysis['action_needed'] else 'NO'}

🗄️ CURRENT DATABASE STATUS
• Total Components: {data_status['components']:,}
• Latest Update: {data_status['latest_update']}
• Distinct Auctions: {data_status['auction_count']}
• CMU Registry Records: {data_status['cmu_registry']['total_cmus']:,}

🔍 CRAWL ATTEMPT RESULTS
• Records Attempted: {crawl_results['attempted']}
• Successfully Processed: {crawl_results['successful']}
• NEW Records Found: {len(crawl_results['new_records'])} 🆕
• UPDATED Records Found: {len(crawl_results['updated_records'])} 📝
• Errors: {len(crawl_results['errors'])}"""

        # Add new records details if found
        if crawl_results['new_records']:
            report += "\n\n🆕 NEW RECORDS DISCOVERED:"
            for i, record in enumerate(crawl_results['new_records'][:5], 1):
                report += f"""
{i}. CMU: {record['cmu_id']}
   Auction: {record['auction']}
   Company: {record['company']}
   Technology: {record['technology']}
   Capacity: {record['capacity']} MW"""

        # Add updated records if found
        if crawl_results['updated_records']:
            report += "\n\n📝 UPDATED RECORDS:"
            for i, record in enumerate(crawl_results['updated_records'][:3], 1):
                report += f"""
{i}. CMU: {record['cmu_id']} - {record['technology']} ({record['capacity']} MW)"""

        # Add year-by-year crawl details
        report += "\n\n📅 DETAILED RESULTS BY YEAR:"
        for year, details in crawl_results['details_by_year'].items():
            report += f"""
            
{year}:
• Status: {details['status']}
• Attempted: {details['attempted']} records
• New Found: {details['found_new']}
• Updated Found: {details['found_updated']}"""
            
            if details['sample_data']:
                report += "\n• Sample Records:"
                for rec in details['sample_data'][:2]:
                    report += f"\n  - {rec['cmu_id']}: {rec['status']} ({rec['technology']})"

        # Add API comparison
        report += "\n\n📊 API vs DATABASE COMPARISON:"
        for year, check in api_checks.items():
            if isinstance(check.get('api_count'), int):
                report += f"""
{year}: {check['local_count']} local vs {check['api_count']} API ({check['difference']:+} difference)"""

        # Add recommendations
        if analysis['recommendations']:
            report += "\n\n💡 RECOMMENDATIONS:"
            for rec in analysis['recommendations']:
                report += f"\n• {rec}"

        # Add top auctions
        report += "\n\n📈 TOP 10 AUCTIONS BY COMPONENT COUNT:"
        for i, (auction, count) in enumerate(list(data_status['top_auctions'].items())[:10], 1):
            report += f"\n{i}. {auction}: {count:,} components"

        report += """

---
This enhanced report includes actual crawl attempts to verify data availability.
Unlike the basic check, this confirms whether new data actually exists."""

        return report
    
    def send_enhanced_email(self, email_to, report, analysis):
        """Send enhanced email with priority indicators."""
        # Determine subject based on findings
        priority_emoji = {
            'high': '🚨',
            'medium': '⚠️',
            'low': '✅'
        }
        
        emoji = priority_emoji.get(analysis['priority'], '📊')
        
        if analysis['new_data_confirmed']:
            subject = f"{emoji} CMR ALERT: New Data Confirmed - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        elif analysis['action_needed']:
            subject = f"{emoji} CMR Update Required - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        else:
            subject = f"{emoji} CMR Weekly Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        
        try:
            send_mail(
                subject=subject,
                message=report,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_to],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Enhanced report sent to {email_to}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Email failed: {e}'))
    
    def save_enhanced_findings(self, data_status, api_checks, crawl_results, analysis):
        """Save detailed findings including crawl results."""
        findings_file = os.path.join(
            settings.BASE_DIR, 
            'docs', 
            f'ENHANCED_CHECK_{datetime.now(timezone.utc).strftime("%Y-%m-%d")}.json'
        )
        
        findings = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data_status': {
                'components': data_status['components'],
                'latest_update': data_status['latest_update'].isoformat() if data_status['latest_update'] else None,
                'auction_count': data_status['auction_count']
            },
            'api_checks': api_checks,
            'crawl_results': {
                'attempted': crawl_results['attempted'],
                'successful': crawl_results['successful'],
                'new_records_count': len(crawl_results['new_records']),
                'updated_records_count': len(crawl_results['updated_records']),
                'new_records': crawl_results['new_records'][:10],  # Save up to 10 examples
                'errors': crawl_results['errors']
            },
            'analysis': analysis
        }
        
        os.makedirs(os.path.dirname(findings_file), exist_ok=True)
        with open(findings_file, 'w') as f:
            json.dump(findings, f, indent=2, default=str)
        
        self.stdout.write(f'📄 Enhanced findings saved to {findings_file}')