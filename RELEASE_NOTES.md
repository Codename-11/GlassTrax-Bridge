This release improves the Diagnostics page UX, adds experimental caching controls, and updates the release workflow.

## What's Changed

### Features
- **Collapsible Diagnostics Sections** - System Info always visible, other sections collapsible with manual triggers
- **Experimental Caching UI** - Cache settings in Settings page with experimental badges, conservative 5-minute default TTL
- **Cache Bypass Support** - Clients can request fresh data with `?bypass_cache=true` parameter

### Improvements
- **Login Page** - Added logo and removed default credential hints for cleaner UX
- **Access Logging** - Internal/admin requests now excluded from access logs to show only external API usage
- **Diagnostics UX** - Speed test and cache status no longer auto-trigger on page load
- **Release Workflow** - Switched from AI-generated to committed RELEASE_NOTES.md for consistent release notes

### Documentation
- Updated CLAUDE.md with semantic versioning, conventional commits, and release notes format guidelines
- Added caching documentation with experimental warnings and bypass instructions
