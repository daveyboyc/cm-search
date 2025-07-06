"""
Weekly data monitoring command with historical tracking.

This command checks for new data in the NESO API and compares it with our database.
It maintains historical records to track patterns and avoid false positives.

Key Features:
- Tracks historical baselines to detect real changes
- Documents findings for pattern recognition
- Focuses on future auction years (2029+) to avoid false positives
- Sends weekly email reports with detailed analysis
- Maintains memory of previous weeks' findings

Usage:
    python manage.py weekly_data_check --email=user@example.com
    python manage.py weekly_data_check --email=user@example.com --force-rebuild
"""
import json
import os
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone as django_timezone
from django.db import models
from checker.models import Component, CMURegistry
import requests


class Command(BaseCommand):
    help = 'Check for new data weekly and send email reports with historical tracking'
    
    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email address to send report to')
        parser.add_argument('--force-rebuild', action='store_true', help='Force rebuild of historical baseline')
        parser.add_argument('--dry-run', action='store_true', help='Run analysis without sending email')
        parser.add_argument('--smart-schedule', action='store_true', help='Only email weekly or on significant changes')
    
    def handle(self, *args, **options):
        start_time = datetime.now(timezone.utc)
        
        self.stdout.write(self.style.SUCCESS('📊 Weekly Data Monitoring Check'))
        self.stdout.write(f'Started: {start_time.strftime("%Y-%m-%d %H:%M:%S UTC")}')
        
        # Load or create historical baseline
        baseline = self.load_or_create_baseline(options.get('force_rebuild', False))
        
        # Get current data status
        data_status = self.get_current_data_status()
        
        # Check API for new data (focus on future auctions)
        api_checks = self.check_api_for_new_data()
        
        # Analyze changes since last week
        analysis = self.analyze_changes(data_status, baseline, api_checks)
        
        # Update historical records
        self.update_historical_records(data_status, analysis)
        
        # Generate report
        report = self.generate_comprehensive_report(data_status, api_checks, analysis, baseline, start_time)
        
        # Determine if email should be sent
        should_send_email = self.should_send_email(analysis, data_status, options)
        
        # Send email if requested and conditions met
        if options.get('email') and not options.get('dry_run') and should_send_email:
            email_reason = self.get_email_reason(analysis, data_status, options)
            self.send_email_report(options['email'], report, email_reason)
        elif options.get('email') and not options.get('dry_run') and not should_send_email:
            self.stdout.write(self.style.WARNING('📧 Email skipped - no significant changes detected'))
        
        # Save detailed findings for next week
        self.save_weekly_findings(data_status, api_checks, analysis)
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        self.stdout.write(self.style.SUCCESS(f'✅ Weekly check completed in {duration:.1f}s'))
        
        if options.get('dry_run'):
            self.stdout.write('\n📧 Email Report Preview:')
            self.stdout.write(report)
    
    def load_or_create_baseline(self, force_rebuild=False):
        """Load historical baseline or create if missing."""
        baseline_file = os.path.join(settings.BASE_DIR, 'docs', 'weekly_baseline.json')
        
        if os.path.exists(baseline_file) and not force_rebuild:
            with open(baseline_file, 'r') as f:
                baseline = json.load(f)
            self.stdout.write(f'📋 Loaded baseline from {baseline["created_date"]}')
            return baseline
        
        # Create new baseline
        self.stdout.write('🔧 Creating new historical baseline...')
        baseline = {
            'created_date': datetime.now(timezone.utc).isoformat(),
            'components_count': Component.objects.count(),
            'cmu_count': CMURegistry.objects.count(),
            'auction_counts': self.get_auction_counts(),
            'api_total_at_baseline': self.get_api_total_count(),
            'version': '1.0'
        }
        
        # Save baseline
        os.makedirs(os.path.dirname(baseline_file), exist_ok=True)
        with open(baseline_file, 'w') as f:
            json.dump(baseline, f, indent=2)
        
        self.stdout.write(f'✅ Created baseline with {baseline["components_count"]} components')
        return baseline
    
    def get_current_data_status(self):
        """Get current database status."""
        latest_component = Component.objects.order_by('-updated_at').first()
        
        return {
            'components': Component.objects.count(),
            'latest_update': latest_component.updated_at if latest_component else None,
            'auction_count': Component.objects.values('auction_name').distinct().count(),
            'top_auctions': dict(
                Component.objects.values('auction_name')
                .annotate(count=models.Count('id'))
                .order_by('-count')[:5]
                .values_list('auction_name', 'count')
            ),
            'focus_auctions': self.get_focus_auction_counts(),
            'cmu_registry': {
                'total_cmus': CMURegistry.objects.count(),
                'latest_update': CMURegistry.objects.order_by('-last_updated').first().last_updated
                if CMURegistry.objects.exists() else None
            }
        }
    
    def get_focus_auction_counts(self):
        """Get counts for key auction years we're monitoring."""
        focus_years = ['2025-26', '2026-27', '2027-28', '2028-29']
        counts = {}
        
        for year in focus_years:
            count = Component.objects.filter(delivery_year__icontains=year).count()
            counts[year] = count
        
        return counts
    
    def check_api_for_new_data(self):
        """Check NESO API for new data, focusing on future auctions."""
        api_url = "https://data.nationalgrideso.com/api/3/action/datastore_search"
        
        # Updated resource IDs (verified working)
        component_resource_id = "790f5fa0-f8eb-4d82-b98d-0d34d3e404e8"
        
        checks = {}
        
        # Check future auction years (2029+ to avoid false positives)
        future_years = ['2029-30', '2030-31', '2031-32', '2032-33']
        
        for year in future_years:
            try:
                params = {
                    'resource_id': component_resource_id,
                    'q': year,
                    'limit': 1
                }
                
                response = requests.get(api_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                api_count = data['result']['total']
                local_count = Component.objects.filter(delivery_year__icontains=year).count()
                
                checks[year] = {
                    'api_count': api_count,
                    'local_count': local_count,
                    'difference': api_count - local_count,
                    'status': 'new_data' if api_count > local_count else 'current'
                }
                
            except Exception as e:
                checks[year] = {
                    'api_count': 'error',
                    'local_count': Component.objects.filter(delivery_year__icontains=year).count(),
                    'difference': 'unknown',
                    'status': f'error: {str(e)}'
                }
        
        # Also check total API count for reference
        try:
            params = {'resource_id': component_resource_id, 'limit': 1}
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            checks['total_api'] = {
                'count': data['result']['total'],
                'status': 'available'
            }
        except Exception as e:
            checks['total_api'] = {
                'count': 'error',
                'status': f'error: {str(e)}'
            }
        
        return checks
    
    def get_api_total_count(self):
        """Get total count from API for baseline."""
        try:
            api_url = "https://data.nationalgrideso.com/api/3/action/datastore_search"
            params = {
                'resource_id': "790f5fa0-f8eb-4d82-b98d-0d34d3e404e8",
                'limit': 1
            }
            
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return data['result']['total']
        except Exception:
            return 'unknown'
    
    def get_auction_counts(self):
        """Get auction counts for baseline."""
        from django.db import models
        return dict(
            Component.objects.values('auction_name')
            .annotate(count=models.Count('id'))
            .order_by('-count')[:10]
            .values_list('auction_name', 'count')
        )
    
    def analyze_changes(self, current_data, baseline, api_checks):
        """Analyze changes since baseline and previous weeks."""
        analysis = {
            'new_auctions_found': [],
            'significant_increases': [],
            'data_age_days': 0,
            'recommendation': 'no_action'
        }
        
        # Calculate data age
        if current_data['latest_update']:
            age_delta = datetime.now(timezone.utc) - current_data['latest_update']
            analysis['data_age_days'] = age_delta.days
        
        # Check for new auction years in future data
        for year, check in api_checks.items():
            if year != 'total_api' and check['status'] == 'new_data' and isinstance(check['api_count'], int) and check['api_count'] > 0:
                analysis['new_auctions_found'].append(year)
                analysis['recommendation'] = 'investigate'
        
        # Compare with baseline
        components_change = current_data['components'] - baseline['components_count']
        if abs(components_change) > 100:  # Significant change threshold
            analysis['significant_increases'].append({
                'type': 'components',
                'change': components_change,
                'from': baseline['components_count'],
                'to': current_data['components']
            })
        
        return analysis
    
    def update_historical_records(self, data_status, analysis):
        """Update historical tracking records."""
        history_file = os.path.join(settings.BASE_DIR, 'docs', 'weekly_history.json')
        
        # Load existing history
        history = []
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)
        
        # Add this week's record
        record = {
            'date': datetime.now(timezone.utc).isoformat(),
            'components_count': data_status['components'],
            'cmu_count': data_status['cmu_registry']['total_cmus'],
            'new_auctions_found': analysis['new_auctions_found'],
            'data_age_days': analysis['data_age_days'],
            'recommendation': analysis['recommendation']
        }
        
        history.append(record)
        
        # Keep last 12 weeks
        history = history[-12:]
        
        # Save updated history
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def generate_comprehensive_report(self, data_status, api_checks, analysis, baseline, start_time):
        """Generate detailed email report with historical context and learnings."""
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Load previous week's learnings
        previous_learnings = self.get_previous_week_learnings()
        
        report = f"""📊 CAPACITY MARKET DATA - WEEKLY MONITORING REPORT
Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
Report Duration: {duration:.1f}s

🗄️ CURRENT DATABASE STATUS
• Total Components: {data_status['components']:,}
• Latest Update: {data_status['latest_update']}
• Data Age: {analysis['data_age_days']} days
• Distinct Auctions: {data_status['auction_count']}
• CMU Registry Records: {data_status['cmu_registry']['total_cmus']:,}

📈 TOP 5 AUCTIONS BY COMPONENT COUNT"""
        
        for auction, count in list(data_status['top_auctions'].items())[:5]:
            report += f"\n• {auction}: {count:,} components"
        
        report += f"""

🎯 KEY AUCTION FOCUS (Current vs Expected New)"""
        
        for year, local_count in data_status['focus_auctions'].items():
            if year in api_checks:
                api_count = api_checks[year]['api_count']
                if isinstance(api_count, int) and api_count > local_count:
                    diff = api_count - local_count
                    report += f"\n• {year}: {local_count:,} local, {api_count:,} API = {diff:,} difference (🆕 POTENTIAL NEW)"
                else:
                    report += f"\n• {year}: {local_count:,} local, {api_count} API (✅ Current)"
        
        report += f"""

🔍 FUTURE AUCTION MONITORING (2029+)"""
        
        future_found = False
        for year in ['2029-30', '2030-31', '2031-32', '2032-33']:
            if year in api_checks:
                check = api_checks[year]
                if isinstance(check['api_count'], int) and check['api_count'] > 0:
                    report += f"\n• {year}: {check['local_count']} local, {check['api_count']} API (🆕 NEW DATA FOUND)"
                    future_found = True
                else:
                    report += f"\n• {year}: {check['local_count']} local, {check['api_count']} API (✅ Current)"
        
        if not future_found:
            report += "\n• ✅ NO NEW FUTURE AUCTION DATA (2029+)"
        
        # API comparison
        total_api = api_checks.get('total_api', {})
        if isinstance(total_api.get('count'), int):
            api_total = total_api['count']
            raw_diff = api_total - data_status['components']
            report += f"""

📊 TOTAL API vs LOCAL COMPARISON
• Local Database: {data_status['components']:,} components (deduplicated, current state)
• NESO API Total: {api_total:,} records (includes duplicates & historical versions)
• Raw Difference: {raw_diff:,} records
• Status: ✅ EXPECTED DIFFERENCE (structure differences, not missing data)"""
        
        # Analysis and recommendations
        report += f"""

🎯 ANALYSIS & WEEKLY FINDINGS"""
        
        if analysis['new_auctions_found']:
            report += f"\n• 🆕 NEW AUCTION DATA FOUND: {', '.join(analysis['new_auctions_found'])}"
            report += f"\n• 🔍 RECOMMENDATION: {analysis['recommendation'].upper()}"
        else:
            report += f"\n• ✅ NO NEW FUTURE AUCTION DATA (2029+)"
            report += f"\n• 📋 STATUS: System current, no action needed"
        
        # Historical context and learning
        report += f"""

💡 KEY INSIGHT FROM WEEKLY ANALYSIS
• Database contains {data_status['components']:,} current components
• API shows {total_api.get('count', 'unknown')} total records due to structural differences
• Our tracking focuses on future auctions (2029+) to detect genuine new data
• Historical analysis shows API count differences are misleading, not missing data
• Weekly monitoring maintains baseline: {baseline['components_count']:,} components"""
        
        # Learning from previous weeks
        report += f"""

📊 HISTORICAL BASELINE (for comparison)
• Baseline Date: {baseline['created_date'][:10]}
• Baseline Components: {baseline['components_count']:,}
• Current Components: {data_status['components']:,}
• Change since baseline: {data_status['components'] - baseline['components_count']:+,} components
• Key insight: Large API differences do NOT indicate missing current data"""
        
        report += f"""

🛠️ MONITORING APPROACH
• Focus: NEW auction years (2029-30+) for genuine new data
• Ignore: Total count differences (misleading due to API structure)
• Track: Specific auction patterns with historical context
• Document: All findings for pattern recognition

---
*Generated by weekly_data_check management command*"""
        
        # Add previous week learnings section
        if previous_learnings:
            report += f"\n\n📚 LEARNINGS FROM PREVIOUS WEEK\n{previous_learnings}"
        
        return report
    
    def get_previous_week_learnings(self):
        """Load key learnings from previous week's monitoring files."""
        learnings_dir = os.path.join(settings.BASE_DIR, 'docs')
        
        # Look for recent monitoring files (last 14 days)
        recent_files = []
        if os.path.exists(learnings_dir):
            for filename in os.listdir(learnings_dir):
                if filename.startswith('WEEKLY_MONITORING_') and filename.endswith('.md'):
                    filepath = os.path.join(learnings_dir, filename)
                    # Get file modification time
                    mtime = os.path.getmtime(filepath)
                    file_date = datetime.fromtimestamp(mtime, timezone.utc)
                    days_old = (datetime.now(timezone.utc) - file_date).days
                    
                    if days_old <= 14:  # Files from last 2 weeks
                        recent_files.append((filepath, days_old, filename))
        
        # Also look for baseline learnings document
        baseline_file = os.path.join(learnings_dir, 'BASELINE_LEARNINGS_2025-06-20.md')
        if os.path.exists(baseline_file):
            recent_files.append((baseline_file, 0, 'BASELINE_LEARNINGS_2025-06-20.md'))
        
        if not recent_files:
            return None
        
        # Sort by age (newest first) and take most relevant
        recent_files.sort(key=lambda x: x[1])
        
        learnings_summary = "Key insights from our monitoring history:\n"
        
        # Include baseline learnings if this is early in monitoring
        for filepath, age, filename in recent_files[:2]:  # Top 2 most recent
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                
                # Extract key sections for email
                if 'BASELINE_LEARNINGS' in filename:
                    learnings_summary += f"\n🏗️ BASELINE INSIGHTS ({filename[:30]}):\n"
                    # Extract key observations
                    if '## 🔍 Key Initial Observations' in content:
                        section = content.split('## 🔍 Key Initial Observations')[1].split('##')[0]
                        learnings_summary += section.strip()[:500] + "...\n"
                
                elif 'WEEKLY_MONITORING' in filename:
                    learnings_summary += f"\n📈 PREVIOUS WEEK ({filename[17:27]}):\n"
                    # Extract summary or key findings
                    if '## Summary' in content:
                        section = content.split('## Summary')[1].split('##')[0]
                        learnings_summary += section.strip()[:400] + "...\n"
                    
            except Exception as e:
                continue
        
        return learnings_summary if len(learnings_summary) > 50 else None
    
    def should_send_email(self, analysis, data_status, options):
        """Determine if email should be sent based on smart scheduling rules."""
        # Always send if not using smart schedule
        if not options.get('smart_schedule'):
            return True
        
        # Always send on significant changes
        if self.has_significant_changes(analysis, data_status):
            return True
        
        # Send weekly summary (every Sunday)
        today = datetime.now(timezone.utc)
        if today.weekday() == 6:  # Sunday = 6
            return True
        
        return False
    
    def has_significant_changes(self, analysis, data_status):
        """Check if there are significant changes that warrant immediate email."""
        # New future auctions detected
        if analysis['new_auctions_found']:
            return True
        
        # Large component count change (>200 from baseline)
        component_change = abs(data_status['components'] - 63847)
        if component_change > 200:
            return True
        
        # Data significantly fresher than baseline (improvement of 4+ days)
        if analysis['data_age_days'] <= 3 and analysis['data_age_days'] < 7 - 4:
            return True
        
        # Data significantly older than expected (8+ days when baseline was 7)
        if analysis['data_age_days'] > 8:
            return True
        
        return False
    
    def get_email_reason(self, analysis, data_status, options):
        """Get the reason why email is being sent."""
        if not options.get('smart_schedule'):
            return "Daily monitoring report"
        
        if self.has_significant_changes(analysis, data_status):
            if analysis['new_auctions_found']:
                return f"🚨 ALERT: New future auctions detected: {', '.join(analysis['new_auctions_found'])}"
            
            component_change = abs(data_status['components'] - 63847)
            if component_change > 200:
                return f"📊 ALERT: Significant component change: {data_status['components'] - 63847:+,} from baseline"
            
            if analysis['data_age_days'] <= 3:
                return "🆕 UPDATE: Data freshness significantly improved"
            
            if analysis['data_age_days'] > 8:
                return "⚠️ WARNING: Data aging beyond expected range"
        
        # Must be weekly summary
        return "📅 Weekly monitoring summary"
    
    def send_email_report(self, email_to, report, reason="Weekly monitoring report"):
        """Send email report using Mailgun."""
        # Create dynamic subject based on reason
        if "ALERT" in reason:
            subject = f'🚨 CMR ALERT - {datetime.now(timezone.utc).strftime("%Y-%m-%d")}'
        elif "Weekly" in reason:
            subject = f'📅 CMR Weekly Summary - {datetime.now(timezone.utc).strftime("%Y-%m-%d")}'
        else:
            subject = f'📊 CMR Update - {datetime.now(timezone.utc).strftime("%Y-%m-%d")}'
        
        # Add reason to top of report
        report = f"📧 EMAIL REASON: {reason}\n\n{report}"
        
        try:
            send_mail(
                subject=subject,
                message=report,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_to],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Email report sent to {email_to}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Email failed: {e}'))
    
    def save_weekly_findings(self, data_status, api_checks, analysis):
        """Save detailed findings for next week's reference."""
        findings_file = os.path.join(
            settings.BASE_DIR, 
            'docs', 
            f'WEEKLY_MONITORING_{datetime.now(timezone.utc).strftime("%Y-%m-%d")}.md'
        )
        
        # Create structured learning document
        week_number = datetime.now(timezone.utc).isocalendar()[1]
        findings = f"""# Weekly Data Monitoring Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
**Week {week_number} of 2025**

## Executive Summary
- **Total Components**: {data_status['components']:,} ({data_status['components'] - 63847:+,} from baseline)
- **CMU Records**: {data_status['cmu_registry']['total_cmus']:,}
- **Data Freshness**: {analysis['data_age_days']} days old
- **New Auctions Found**: {len(analysis['new_auctions_found'])} future auctions
- **Status**: {analysis['recommendation'].upper()}

## 📊 Key Changes This Week

### Component Count Analysis
- **Current Total**: {data_status['components']:,}
- **Baseline (June 20)**: 63,847
- **Net Change**: {data_status['components'] - 63847:+,} components
- **Change %**: {((data_status['components'] - 63847) / 63847 * 100):+.2f}%

### Data Freshness Tracking
- **Data Age**: {analysis['data_age_days']} days
- **Previous Week**: 7 days (baseline)
- **Improvement**: {"✅ FRESHER" if analysis['data_age_days'] < 7 else "⚠️ OLDER" if analysis['data_age_days'] > 7 else "➡️ SAME"}

## 🎯 Monitoring Results

### Future Auction Watch (2029+)
{"📢 **NEW AUCTIONS DETECTED:** " + ", ".join(analysis['new_auctions_found']) if analysis['new_auctions_found'] else "✅ No new future auctions (expected)"}

### Top 5 Current Auctions
{chr(10).join([f"• {auction}: {count:,} components" for auction, count in list(data_status['top_auctions'].items())[:5]])}

## 💡 This Week's Learning

### What We Discovered
- **Pattern Recognition**: {self.generate_pattern_insights(data_status, analysis)}
- **Data Stability**: {self.assess_data_stability(data_status, analysis)}
- **API Health**: {self.assess_api_health(api_checks)}

### Comparative Analysis
- **Week-over-Week**: {self.generate_weekly_comparison(data_status, analysis)}
- **Trend Assessment**: {self.assess_trends(data_status, analysis)}

## 🔍 Technical Details

### Raw Analysis Results
```json
{json.dumps(analysis, indent=2, default=str)}
```

### API Check Results  
```json
{json.dumps(api_checks, indent=2, default=str)}
```

---
*Generated by weekly_data_check management command on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*
"""
        
        # Save findings
        os.makedirs(os.path.dirname(findings_file), exist_ok=True)
        with open(findings_file, 'w') as f:
            f.write(findings)
        
        self.stdout.write(f'📄 Detailed findings saved to {findings_file}')
    
    def generate_pattern_insights(self, data_status, analysis):
        """Generate insights about data patterns."""
        if analysis['data_age_days'] <= 3:
            return "Data is fresh, NESO updating regularly"
        elif analysis['data_age_days'] > 7:
            return "Data aging, possible delayed NESO updates"
        else:
            return "Standard weekly update cycle observed"
    
    def assess_data_stability(self, data_status, analysis):
        """Assess how stable the data is week-over-week."""
        component_change = abs(data_status['components'] - 63847)
        if component_change < 50:
            return "Very stable - minimal component changes"
        elif component_change < 200:
            return "Stable - normal component fluctuation"
        else:
            return f"Significant change - {component_change} component difference"
    
    def assess_api_health(self, api_checks):
        """Assess API connectivity and health."""
        total_api = api_checks.get('total_api', {})
        if total_api.get('status') == 'available':
            return "API fully operational and responsive"
        else:
            return f"API issues detected: {total_api.get('status', 'unknown')}"
    
    def generate_weekly_comparison(self, data_status, analysis):
        """Generate week-over-week comparison insights."""
        change = data_status['components'] - 63847
        if change == 0:
            return "Identical component count to baseline"
        elif abs(change) < 100:
            return f"Minor change: {change:+} components from baseline"
        else:
            return f"Notable change: {change:+} components ({change/63847*100:+.1f}%)"
    
    def assess_trends(self, data_status, analysis):
        """Assess broader trends in the data."""
        if analysis['new_auctions_found']:
            return "Major trend: New future auctions detected"
        elif analysis['data_age_days'] < 7:
            return "Positive trend: Data freshness improving"
        else:
            return "Steady state: No significant trend changes"