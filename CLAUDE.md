# Project Setup & Architecture
- Stack: Supabase (database), Heroku (hosting), Redis (caching), Mailgun (email), Stripe (payments)
- Database: Supabase on free tier - MUST optimize for 5GB/month egress limit
- Always check README.md, TODO.md, or PLAN.md before making changes

# Critical Design Patterns
- Homepage (http://localhost:8000/) has UNIQUE navigation/hamburger menu with central search bar
- All other pages use UNIVERSAL navbar with integrated search bar
- When updating navigation, MUST update both homepage and universal navbar separately
- Maintain consistent design and fonts throughout the site
- Map pages MUST have: map, satellite, hybrid, and street view options enabled

# Data Model Rules
- Technologies have strict parent-child hierarchy (reference: map-explorer)
- Parent categories: Battery, CHP, Interconnector, Wind, EV Charging
- Parent-child hierarchy MUST be maintained at database level
- Color inheritance: Child technologies use same color as parent (e.g., Battery=green, Storage=green, Storage (1hr)=green)
- NEVER modify established parent-child relationships or color schemes

# Before Making ANY Changes
1. Check existing implementation first
2. Review relevant README/TODO/PLAN files
3. Verify database schema before modifying
4. Consider Supabase egress limits for all queries
5. Test impact on both navigation systems if touching nav

# Common Mistakes to Avoid
- DO NOT create new databases or external services
- DO NOT implement features that increase database egress significantly
- DO NOT change technology hierarchy or color coding
- DO NOT assume both navigation systems are the same
- DO NOT modify core architecture without checking existing patterns

## Project Context
This project uses Supabase (free tier with 5GB/month limit), Heroku, Redis, Mailgun, and Stripe. The site has two different navigation systems - homepage has its own, all other pages share a universal navbar.

## Key Learnings
- Navigation updates are tricky - homepage and rest of site use different nav components
- Database efficiency is critical due to Supabase free tier limits
- Technology hierarchy is foundational - don't modify parent-child relationships
- Color coding for technologies is inherited from parents and shouldn't be changed

## Things to Remember
- Always look for README.md, TODO.md, or PLAN.md files first
- The homepage search bar is part of the page design, not in the nav
- Map pages need all view options (map, satellite, hybrid, street view)
- Keep design and fonts consistent across all pages
- Optimize queries to minimize Supabase egress usage

## Project-Specific Gotchas
- Homepage navigation is intentionally different - this is by design
- Technology categories and colors are set in stone - reference map-explorer
- We're intentionally staying on free tier until user base grows
- Don't add new external services or databases

## Development Workflow
- ALWAYS search the codebase before implementing new features - check if similar functionality exists
- Use grep, find, or IDE search to understand existing patterns and avoid duplication
- Before creating new files or functions, verify they don't already exist
- Clean up after yourself: remove all test files, temporary files, and debug code before completion
- Document any cleanup needed in TODO.md if you can't complete it immediately

## Code Quality & Refactoring
- Actively identify and remove dead code, unused functions, and unnecessary files
- When modifying features, check for orphaned code that can be removed
- Consolidate duplicate functionality when found
- Document refactoring opportunities in REFACTOR.md (create if doesn't exist)
- Keep the codebase lean - if something isn't being used, remove it

## Documentation Standards
- README.md must be comprehensive and up-to-date
- Update README.md whenever you add features, change architecture, or modify setup steps
- Include: setup instructions, architecture overview, key features, API documentation
- Document all environment variables and configuration options
- Add troubleshooting section for common issues

## Git Commit Rules
- 
- Always show a summary of changes before committing
- Ask user for commit message preferences
- Group related changes into logical commits
- If unsure about including a change, ask first

## Testing & Cleanup Checklist
Before considering any task complete:
1. Remove all console.logs, debug statements, and test code
2. Delete any temporary or test files created
3. Verify no hardcoded test data remains
4. Check for and remove commented-out code
5. Ensure all new code is properly documented
6. Update relevant documentation (README.md, etc.)
7. Ask user to review changes before committing