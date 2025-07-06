# General Project Plans

This file contains high-level strategic plans and roadmaps for the CMR project development.

## Performance & Cost Optimization

### Comprehensive Egress & Redis Optimization
- **Status**: ✅ **Phase 1 Complete** - Deployment egress eliminated (2025-01-21)
- **Achievement**: Removed 1-10MB egress per deployment by moving cache building to post-data-update workflow
- **Reference**: [EGRESS_OPTIMIZATION.md](EGRESS_OPTIMIZATION.md) for complete optimization strategy
- **Monitoring**: Use Supabase MCP tools for tracking database usage
  - `mcp__supabase__get_logs --service=postgres`
  - `mcp__supabase__execute_sql` for database size queries
  - `mcp__supabase__get_advisors --type=performance`
- **Target**: Keep under 5GB/month egress limit on free Supabase tier
- **Next Phase**: Analyze Component table fallback patterns in production

## Other Plans

- [SIMPLE_2TIER_PLAN.md](SIMPLE_2TIER_PLAN.md) - Simplified access control system
- [TRADING_BOARD_PLAN.md](TRADING_BOARD_PLAN.md) - Trading board functionality