# Troubleshooting Guide for Exa-MA Documentation

This guide covers common issues when building and developing the Exa-MA documentation site.

## Card Catalog System Not Displaying

### Problem

Cards are not appearing on catalog pages (home page, work packages page, etc.) even though pages are properly tagged.

### Symptoms

- Pages have `:page-layout: manuals` in the document header
- Build shows warnings: `Page layout specified by page not found: manuals (reverting to default layout)`
- Rendered HTML has `<body class="article">` instead of `<body class="article docs-manuals-catalog docs-cards-layout">`
- No `<div class="catalogs">` or `<div class="manuals">` sections in the output

### Root Cause

The **Antora UI bundle cache is outdated** and missing required components:
- `layouts/manuals.hbs` layout file
- `helpers/get-page-cards.js` helper
- `helpers/get-page-cards-multi.js` helper

Antora caches the UI bundle (downloaded from GitHub releases) in `cache/ui/` to speed up builds. If the cache was created before September 2025, it won't have the card catalog system components.

### Solution

**Quick Fix:**
```bash
# Clear the UI cache
npm run clean-cache

# Rebuild the site
npm run antora
```

**Alternative (clear all caches):**
```bash
# Clear all Antora caches (UI + content)
npm run clean-cache-all

# Rebuild
npm run antora
```

**Manual cache clearing:**
```bash
rm -rf cache/ui
npm run antora
```

### Verification

After rebuilding, check:

1. **No layout warnings in build output:**
   ```bash
   npm run antora 2>&1 | grep "Page layout"
   # Should show no warnings
   ```

2. **Body class includes card-related classes:**
   ```bash
   grep 'class="article docs-manuals-catalog docs-cards-layout' public/exama/index.html
   # Should find the line
   ```

3. **Cards are rendered:**
   ```bash
   grep '<div class="catalogs">' public/exama/index.html
   # Should find card containers
   ```

### Prevention

The `npm run build` script now automatically clears the UI cache before building:
```bash
npm run build  # Runs: clean-cache + antora
```

The CI/CD workflow (GitHub Actions) also clears the UI cache before each build.

## Card Configuration

### Required Page Attributes for Cards

**For pages that should appear as cards:**
```asciidoc
= Page Title
:page-layout: default
:page-tags: manual,wp,catalog        # Tags for categorization
:parent-catalogs: wp-catalog         # Which catalog(s) this belongs to
:page-illustration: fa-solid fa-icon # Font Awesome icon
:description: Brief description      # Card description text
```

**For catalog pages that display cards:**
```asciidoc
= Catalog Page
:page-layout: manuals                          # REQUIRED: Use manuals layout
:page-tags: wp-catalog,catalog                 # This page's tags
:page-cards-tag: manual,report,wp              # Which tags to show as cards
:page-cards-within-module: true                # Limit to same module
:page-cards-across-components: false           # Limit to same component
:page-cards-title: Card Section Title          # Optional section title
```

### Card Filtering Logic

Pages appear as cards when:
1. They have at least one tag matching the catalog's `:page-cards-tag:`
2. Their `:parent-catalogs:` includes a tag from the catalog page's `:page-tags:`
3. They don't have `:page-cards-exclude: true`

### Example: Work Packages Catalog

**Catalog page** (`workpackages.adoc`):
```asciidoc
= Work Packages
:page-layout: manuals
:page-tags: wp-catalog,catalog
:page-cards-tag: manual,wp
```

**Individual WP page** (`workpackages/wp1.adoc`):
```asciidoc
= WP1: Discretization
:page-layout: default
:page-tags: manual,wp
:parent-catalogs: wp-catalog
```

This WP1 page will appear as a card on the Work Packages catalog because:
- It has `:page-tags: manual,wp` (matches catalog's `:page-cards-tag:`)
- It has `:parent-catalogs: wp-catalog` (matches catalog's `:page-tags:`)

## Other Common Issues

### Missing Cross-References

**Problem:** Build shows `target of xref not found: software/index.adoc`

**Solution:** Ensure the referenced file exists or update the xref.

### Attribute Not Found Warnings

**Problem:** `skipping reference to missing attribute: exama`

**Solution:** Check that attributes are defined in `site.yml` or `antora.yml`:
```yaml
asciidoc:
  attributes:
    exama: Exa-MA
    numpex: NumPEx
```

### Unterminated Open Blocks

**Problem:** `unterminated open block` warnings in AsciiDoc files

**Solution:** Ensure all open blocks are properly closed:
```asciidoc
====
Content here
====
```

Must have matching delimiters (same number of `=` signs).

### Images Not Found

**Problem:** `target of image not found: wp7-workflow.png`

**Solution:** Place images in `modules/MODULE/images/` directory and reference as:
```asciidoc
image::wp7-workflow.png[]
```

## Build Performance

### Speed Up Local Builds

For iterative development, use:
```bash
# Fast build (uses cache)
npm run antora

# Clean build (clears UI cache)
npm run build
```

### Cache Locations

- **UI Bundle Cache:** `cache/ui/` - Downloaded UI bundle
- **Content Cache:** `cache/content/` - Processed content cache

Clearing just the UI cache is faster than clearing everything.

## Getting Help

If issues persist:

1. Check the [Antora documentation](https://docs.antora.org/)
2. Review the [Feel++ Antora UI repository](https://github.com/feelpp/antora-ui)
3. Open an issue on the [Exa-MA repository](https://github.com/numpex/exama/issues)

## Technical Reference

### UI Bundle Source

The site uses the Feel++ Antora UI:
- **Repository:** https://github.com/feelpp/antora-ui
- **Latest Release:** https://github.com/feelpp/antora-ui/releases/latest
- **Bundle URL:** https://github.com/feelpp/antora-ui/releases/latest/download/ui-bundle.zip

### Required UI Components for Card System

The card catalog system requires these files in the UI bundle:

**Layouts:**
- `layouts/manuals.hbs` - Main catalog layout
- `layouts/catalog.hbs` - Alternative catalog layout
- `layouts/default.hbs` - Default page layout

**Helpers:**
- `helpers/get-page-cards.js` - Single-tag card finder
- `helpers/get-page-cards-multi.js` - Multi-tag card finder  
- `helpers/get-attr.js` - Attribute accessor
- `helpers/category-from-tags.js` - Tag categorization

**Partials:**
- `partials/page-card.hbs` - Individual card template
- `partials/_cards-list.hbs` - Card list template

**CSS:**
- `css/cards-layout.css` - Card grid styling
- Body class: `docs-cards-layout` enables card styles

### Version History

- **September 2025:** Card catalog system added to Antora UI
- **February 2025 and earlier:** UI bundles lack card system
- **January 2026:** Cache clearing added to CI/CD and npm scripts
