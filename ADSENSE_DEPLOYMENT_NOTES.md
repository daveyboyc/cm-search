# AdSense Deployment Critical Notes

## ⚠️ CRITICAL DATABASE SCHEMA ISSUE ⚠️

### Problem Encountered (July 2025):
When deploying AdSense features from `feature/google-adsense` branch to production, there's a **MAJOR database schema mismatch risk** that caused 500 errors during user registration.

### Root Cause:
- AdSense development added `ad_preference` and `show_ads` fields to UserProfile model
- During development, these fields may have been accidentally migrated to production database
- When production code doesn't include these fields, Django signals fail with IntegrityError
- **Error**: `null value in column "ad_preference" of relation "accounts_userprofile" violates not-null constraint`

### What Happened:
1. AdSense branch added new UserProfile fields: `ad_preference` (CharField, NOT NULL), `show_ads` (BooleanField, NOT NULL)
2. Production database somehow got these columns (possibly from earlier testing)
3. Current production code (trades_branch) doesn't have these fields in model
4. User registration failed because Django signals tried to create UserProfile without required fields

### Fix Applied (July 2025):
**Production Fix:**
```sql
-- Dropped orphaned columns from production database
ALTER TABLE accounts_userprofile DROP COLUMN IF EXISTS ad_preference;
ALTER TABLE accounts_userprofile DROP COLUMN IF EXISTS show_ads;
```

**Local Development Fix (when testing AdSense branch):**
```sql
-- Added missing columns for AdSense development
ALTER TABLE accounts_userprofile ADD COLUMN show_ads boolean DEFAULT true;
ALTER TABLE accounts_userprofile ADD COLUMN ad_preference varchar(10) DEFAULT 'default';
```

## 🚨 BEFORE DEPLOYING ADSENSE TO PRODUCTION:

### Pre-Deployment Checklist:
1. **Check Current Production Schema**:
   ```bash
   heroku run "python -c \"
   from django.db import connection
   cursor = connection.cursor()
   cursor.execute('SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name=\'accounts_userprofile\' ORDER BY column_name;')
   for row in cursor.fetchall(): print(f'{row[0]:25} {row[1]:15} {row[2]}')
   \""
   ```

2. **Compare with AdSense Model**:
   - Check what fields the AdSense branch adds to UserProfile
   - Ensure migrations are properly created and tested

3. **Migration Strategy Options**:
   
   **Option A: Clean Migration (Recommended)**
   - Create proper Django migration for new fields
   - Set sensible defaults for existing users
   - Test migration on staging first
   
   **Option B: Manual Schema Fix**
   - If columns already exist from earlier testing, ensure they match the model exactly
   - Check constraints and defaults
   
   **Option C: Clean Slate**
   - Drop any existing orphaned columns first
   - Run fresh migrations

### AdSense Model Changes to Expect:
```python
# In accounts/models.py - UserProfile class
ad_preference = models.CharField(
    max_length=20, 
    choices=[('minimal', 'Minimal'), ('standard', 'Standard'), ('none', 'No Ads')],
    default='standard',
    help_text="User's advertising preference"
)
show_ads = models.BooleanField(
    default=True,
    help_text="Whether to show ads to this user"
)
```

### Deployment Steps:
1. **Backup Production Database** (always!)
2. **Check for existing orphaned columns** (use query above)
3. **If orphaned columns exist**: Drop them before migration
4. **Create migration**: `python manage.py makemigrations accounts`
5. **Test migration locally** with production-like data
6. **Apply migration on Heroku**: `heroku run python manage.py migrate`
7. **Test user registration** immediately after deployment
8. **Monitor logs** for any UserProfile creation errors

### Testing Checklist Post-Deployment:
- [ ] User registration works for new users
- [ ] Existing users can log in without errors  
- [ ] UserProfile creation in signals works properly
- [ ] Ad preference settings display correctly
- [ ] Ad display logic functions as expected

### Rollback Plan:
If deployment fails:
1. **Remove new columns**:
   ```sql
   ALTER TABLE accounts_userprofile DROP COLUMN IF EXISTS ad_preference;
   ALTER TABLE accounts_userprofile DROP COLUMN IF EXISTS show_ads;
   ```
2. **Revert to previous commit**
3. **Clear any cached migrations**

### Files to Monitor:
- `accounts/models.py` - UserProfile model changes
- `accounts/migrations/` - New migration files
- `accounts/signals.py` - UserProfile creation logic
- `ads/` - All AdSense-related files
- `templates/` - Ad template changes

## Environment Variables for AdSense:
```bash
# Required for production
ADSENSE_ENABLED=true
ADSENSE_CLIENT_ID=ca-pub-XXXXXXXXXX
ADSENSE_TEST_MODE=false  # Set to true for testing

# Already set (confirmed working):
SITE_DOMAIN=capacitymarket.co.uk
SITE_SCHEME=https
```

## Contact/Reference:
- Issue discovered and fixed: July 5, 2025
- Fixed by Claude Code in conversation about registration 500 errors
- Production deployment was successful after schema cleanup
- AdSense features remain safely isolated on `feature/google-adsense` branch

**REMEMBER**: Always test schema changes on staging first and have a rollback plan ready!