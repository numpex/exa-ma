# Exa-MA Documentation Generator Makefile
#
# Usage:
#   make generate          - Generate all documentation pages
#   make generate-antora   - Generate pages into Antora module structure
#   make preview           - Dry run to preview what will be generated
#   make clean             - Remove generated pages
#   make help              - Show this help message

# Default Google Sheets ID for Exa-MA software data
SHEET_ID ?= 19v57jpek52nQV2V0tBBON5ivGCz7Bqf3Gw-fHroVHkA

# Output directories
OUTPUT_DIR ?= /tmp/exa-ma-pages
ANTORA_PAGES_DIR ?= docs/modules/software/pages
ANTORA_NAV_DIR ?= docs/modules/software

# Command
HARVEST_CMD = exa-ma-harvest-software

.PHONY: help generate generate-antora preview clean install init-config

help:
	@echo "Exa-MA Documentation Generator"
	@echo ""
	@echo "Usage:"
	@echo "  make generate          - Generate all pages to $(OUTPUT_DIR)"
	@echo "  make generate-antora   - Generate pages into Antora module structure"
	@echo "  make preview           - Dry run to preview what will be generated"
	@echo "  make clean             - Remove generated pages"
	@echo "  make install           - Install the harvest package"
	@echo "  make init-config       - Create a default configuration file"
	@echo ""
	@echo "Configuration:"
	@echo "  SHEET_ID=$(SHEET_ID)"
	@echo "  OUTPUT_DIR=$(OUTPUT_DIR)"
	@echo "  ANTORA_PAGES_DIR=$(ANTORA_PAGES_DIR)"

# Install the harvest package
install:
	uv pip install -e .

# Generate pages to output directory
generate:
	$(HARVEST_CMD) generate -s sheets:$(SHEET_ID) -o $(OUTPUT_DIR)

# Generate pages directly into Antora module structure
generate-antora:
	@echo "Generating pages to Antora module..."
	$(HARVEST_CMD) generate -s sheets:$(SHEET_ID) -o $(ANTORA_PAGES_DIR) --antora
	@echo ""
	@echo "Pages generated to $(ANTORA_PAGES_DIR)"
	@echo "Navigation generated to $(ANTORA_NAV_DIR)/nav.adoc"

# Generate with config file
generate-config:
	@if [ -f harvest-config.yaml ]; then \
		$(HARVEST_CMD) generate -s sheets:$(SHEET_ID) -o $(ANTORA_PAGES_DIR) --antora -c harvest-config.yaml; \
	else \
		echo "No harvest-config.yaml found. Run 'make init-config' to create one."; \
		exit 1; \
	fi

# Preview what would be generated (dry run)
preview:
	$(HARVEST_CMD) generate -s sheets:$(SHEET_ID) -o $(OUTPUT_DIR) --dry-run

# Preview Antora structure
preview-antora:
	$(HARVEST_CMD) generate -s sheets:$(SHEET_ID) -o $(ANTORA_PAGES_DIR) --antora --dry-run

# Filter by work package
generate-wp%:
	$(HARVEST_CMD) generate -s sheets:$(SHEET_ID) -o $(OUTPUT_DIR) --filter-wp $*

# Create default configuration file
init-config:
	$(HARVEST_CMD) init-config -o harvest-config.yaml

# Clean generated pages
clean:
	rm -rf $(OUTPUT_DIR)
	@echo "Cleaned $(OUTPUT_DIR)"

# Clean Antora pages (be careful with this!)
clean-antora:
	@echo "This will remove generated pages from $(ANTORA_PAGES_DIR)"
	@echo "Are you sure? (Press Ctrl+C to cancel, Enter to continue)"
	@read confirm
	rm -rf $(ANTORA_PAGES_DIR)/frameworks
	rm -rf $(ANTORA_PAGES_DIR)/applications
	rm -f $(ANTORA_PAGES_DIR)/frameworks.adoc
	rm -f $(ANTORA_PAGES_DIR)/applications.adoc
	@echo "Cleaned Antora pages (kept index.adoc and concepts.adoc)"

# List available frameworks
list-frameworks:
	$(HARVEST_CMD) list -s sheets:$(SHEET_ID)

# List available applications
list-applications:
	$(HARVEST_CMD) applications -s sheets:$(SHEET_ID)

# Export data to JSON
export-json:
	$(HARVEST_CMD) export -s sheets:$(SHEET_ID) -f json -o software-data.json
	@echo "Exported to software-data.json"

# Show cache statistics
cache-stats:
	$(HARVEST_CMD) cache stats

# Clear cache
cache-clear:
	$(HARVEST_CMD) cache clear
