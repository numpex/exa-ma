# Commit Message

## Fix card catalog system and add cache management

### Problem
Card catalog system was not displaying on the exa-ma website due to stale Antora UI bundle cache from February 2025, which was missing the required `manuals.hbs` layout and card helper functions.

### Root Cause Analysis
- Antora caches UI bundle in `cache/ui/` directory
- Cached bundle (from Feb 2025) only had 7 basic layouts
- Missing components:
  - `layouts/manuals.hbs`
  - `helpers/get-page-cards.js`
  - `helpers/get-page-cards-multi.js`
  - Card-related CSS and partials
- Build warnings: "Page layout specified by page not found: manuals"
- Pages with `:page-layout: manuals` reverted to default layout

### Solution Implemented

1. **Cleared stale cache** - Removed outdated UI bundle cache

2. **Added cache management scripts** (`package.json`):
   - `npm run clean-cache` - Clear UI cache only (fast)
   - `npm run clean-cache-all` - Clear all caches
   - `npm run build` - Clean UI cache + build (recommended)

3. **Updated CI/CD** (`.github/workflows/ci.yml`):
   - Added automatic UI cache clearing before each build
   - Prevents stale cache in production deployments

4. **Enhanced documentation**:
   - Expanded `README.md` with setup, troubleshooting, card system docs
   - Created comprehensive `TROUBLESHOOTING.md` guide
   - Documented card configuration requirements
   - Added technical reference for UI components

### Verification
- ✅ Body class: `article docs-manuals-catalog docs-cards-layout`
- ✅ Cards rendering on index.html and workpackages.html
- ✅ `<div class="catalogs">` and `<div class="manuals">` sections present
- ✅ No layout warnings in build output
- ✅ Card helpers working correctly

### Files Changed
- `.github/workflows/ci.yml` - Added cache clearing to CI
- `README.md` - Comprehensive documentation
- `package.json` - Added cache management scripts
- `TROUBLESHOOTING.md` - New troubleshooting guide

### Impact
- Cards now display correctly on catalog pages
- Future builds will automatically use latest UI bundle
- Contributors have clear documentation for setup and troubleshooting
- CI/CD prevents cache-related issues in production

### Testing
```bash
# Test cache clearing
npm run clean-cache

# Test build with clean cache
npm run build

# Verify cards in output
grep 'docs-cards-layout' public/exama/index.html
grep '<div class="catalogs">' public/exama/index.html
```

### Related
- UI Bundle: https://github.com/feelpp/antora-ui/releases/latest
- Card system added to antora-ui in September 2025
- Issue: Stale cache from February 2025
