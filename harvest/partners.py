"""
External partners data harvesting.

Fetches external partners (industry, academic) from Google Sheets.

Supports configuration from:
- Command line arguments (highest priority)
- Unified exama.yaml config file
- Default values (fallback)
"""

from __future__ import annotations

import io
import math
import urllib.request
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# Import unified config (conditional to avoid circular imports)
try:
    from .config import ExaMAConfig, load_config as load_exama_config
    HAS_UNIFIED_CONFIG = True
except ImportError:
    HAS_UNIFIED_CONFIG = False


def is_nan(value: Any) -> bool:
    """Check if value is NaN or empty."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def clean_string(value: Any) -> str | None:
    """Clean and return string value, or None if empty."""
    if is_nan(value):
        return None
    return str(value).strip()


class CompanySize(str, Enum):
    """Company size categories."""
    LARGE = "Large Group"
    MIDCAP = "Mid Cap"
    SME = "SME"
    RESEARCH = "Research Organization"
    UNKNOWN = "Unknown"


class PartnerType(str, Enum):
    """Types of external partners."""
    ENTREPRISE = "Entreprise"
    EPIC = "EPIC"
    ACADEMIC = "Academic"
    PUBLIC_RESEARCH = "Public Research"
    LARGE_SCALE_RESEARCH_INFRA = "Large scale Research Infrastructure"
    OTHER = "Other"

    @classmethod
    def from_string(cls, value: str | None) -> tuple["PartnerType", "CompanySize"]:
        """Parse partner type and size from string.

        Handles formats like:
        - "Entreprise - Large group"
        - "Entreprise - SME"
        - "EPIC"
        - "Academic"
        - "Public Research"

        Returns:
            Tuple of (PartnerType, CompanySize)
        """
        if not value:
            return cls.OTHER, CompanySize.UNKNOWN

        value_lower = value.lower().strip()

        # Extract company size if present
        size = CompanySize.UNKNOWN
        if "large group" in value_lower:
            size = CompanySize.LARGE
        elif "sme" in value_lower:
            size = CompanySize.SME
        elif "mid cap" in value_lower or "midcap" in value_lower:
            size = CompanySize.MIDCAP

        # Determine partner type
        if "entreprise" in value_lower or "company" in value_lower:
            return cls.ENTREPRISE, size
        elif "epic" in value_lower:
            return cls.EPIC, CompanySize.RESEARCH
        elif "academic" in value_lower or "university" in value_lower or "université" in value_lower:
            return cls.ACADEMIC, CompanySize.RESEARCH
        elif "public research" in value_lower:
            return cls.PUBLIC_RESEARCH, CompanySize.RESEARCH
        elif "large scale research infrastructure" in value_lower or "research infrastructure" in value_lower:
            return cls.LARGE_SCALE_RESEARCH_INFRA, CompanySize.RESEARCH
        else:
            return cls.OTHER, size


class CollaborationType(str, Enum):
    """Types of collaboration."""
    RESEARCH = "Research Collaborations"
    COFUNDING = "Co-funding"
    PHD_COFUNDING = "PhD co-funding"
    ENGINEER_COFUNDING = "Engineer co-funding"
    POSTDOC_COFUNDING = "Postdoc co-funding"
    FUNDED_PROJECTS = "Funded Projects"
    OTHER = "Other"


class PartnerStatus(str, Enum):
    """Status of partner relationship."""
    POSITIVE_RESPONSE = "Positive Response"
    WORK_PROGRAMME_DISCUSSED = "Work programme discussed"
    INITIAL_EMAIL_SENT = "Initial email sent"
    NOT_CONTACTED = "Not contacted yet"
    UNKNOWN = "Unknown"

    @classmethod
    def from_string(cls, value: str | None) -> "PartnerStatus":
        """Parse status from string."""
        if not value:
            return cls.UNKNOWN
        value_lower = value.lower().strip()
        if "positive" in value_lower:
            return cls.POSITIVE_RESPONSE
        if "work programme" in value_lower:
            return cls.WORK_PROGRAMME_DISCUSSED
        if "initial email" in value_lower:
            return cls.INITIAL_EMAIL_SENT
        if "not contacted" in value_lower:
            return cls.NOT_CONTACTED
        return cls.UNKNOWN


# Icon mapping for common partners (Font Awesome icons)
PARTNER_ICONS = {
    "safran": "rocket",
    "edf": "bolt",
    "onera": "plane",
    "airbus": "plane-departure",
    "cerfacs": "server",
    "ifpen": "gas-pump",
    "totalenergies": "oil-can",
    "total": "oil-can",
    "u luxembourg": "university",
    "luxembourg": "university",
    "default": "handshake",
}


def get_partner_icon(partner_name: str) -> str:
    """Get Font Awesome icon for a partner."""
    if not partner_name:
        return PARTNER_ICONS["default"]

    name_lower = partner_name.lower().strip()
    for key, icon in PARTNER_ICONS.items():
        if key in name_lower:
            return icon
    return PARTNER_ICONS["default"]


# Partners to exclude (collaborative projects, not partners)
EXCLUDED_PARTNERS = {"hidalgo2", "coe-hidalgo2"}

# Invalid department names (partner types, generic terms)
INVALID_DEPARTMENTS = {
    "entreprise", "epic", "academic", "public research",
    "large scale research infrastructure", "other",
    "company", "organization"
}


def is_valid_department(dept: str | None) -> bool:
    """Check if a department name is valid (not a partner type or generic term)."""
    if not dept or not dept.strip():
        return False
    dept_lower = dept.lower().strip()
    return dept_lower not in INVALID_DEPARTMENTS


class ExternalPartner(BaseModel):
    """An external partner organization."""

    name: str
    partner_type: PartnerType = PartnerType.OTHER
    partner_type_raw: str | None = None
    departments: list[str] = Field(default_factory=list)  # Changed from single department
    contact_partner: str | None = None
    contact_exama: str | None = None
    exama_partner: str | None = None
    collaboration_types: list[str] = Field(default_factory=list)  # Changed to list
    status: PartnerStatus = PartnerStatus.UNKNOWN
    status_raw: str | None = None
    topics: list[str] = Field(default_factory=list)
    comments: list[str] = Field(default_factory=list)  # Changed to list
    icon: str | None = None
    company_size: CompanySize = CompanySize.UNKNOWN

    model_config = {"arbitrary_types_allowed": True}

    @property
    def department(self) -> str | None:
        """Backward compatibility: return first department."""
        return self.departments[0] if self.departments else None

    @property
    def collaboration_type(self) -> str | None:
        """Backward compatibility: return all collaboration types joined."""
        return ", ".join(self.collaboration_types) if self.collaboration_types else None

    @property
    def partner_type_display(self) -> str:
        """Return display-friendly partner type string."""
        return self.partner_type.value

    @property
    def status_display(self) -> str:
        """Return display-friendly status string."""
        return self.status.value

    @property
    def is_private(self) -> bool:
        """Check if partner is a private entity (Entreprise)."""
        return self.partner_type == PartnerType.ENTREPRISE

    @property
    def is_public(self) -> bool:
        """Check if partner is a public entity (EPIC, Academic, Public Research, Large scale Research Infrastructure)."""
        return self.partner_type in [PartnerType.EPIC, PartnerType.ACADEMIC, PartnerType.PUBLIC_RESEARCH, PartnerType.LARGE_SCALE_RESEARCH_INFRA]

    @property
    def has_cofunding(self) -> bool:
        """Check if partner has co-funding arrangement (any type)."""
        if self.collaboration_type:
            collab_lower = self.collaboration_type.lower()
            return "co-funding" in collab_lower or "cofunding" in collab_lower or "co funding" in collab_lower
        return False

    @property
    def has_phd_cofunding(self) -> bool:
        """Check if partner has PhD co-funding arrangement."""
        if self.collaboration_type:
            collab_lower = self.collaboration_type.lower()
            return "phd" in collab_lower and ("co-funding" in collab_lower or "cofunding" in collab_lower or "co funding" in collab_lower)
        return False

    @property
    def has_funded_projects(self) -> bool:
        """Check if partner has funded projects collaboration (ANR PRCI, etc.)."""
        if self.collaboration_type:
            collab_lower = self.collaboration_type.lower()
            return "funded project" in collab_lower or "funded projects" in collab_lower
        return False

    @property
    def topics_display(self) -> str:
        """Return formatted topics string."""
        if not self.topics:
            return ""
        return ", ".join(self.topics)

    @property
    def slug(self) -> str:
        """Return URL-safe slug for the partner."""
        import re
        name = self.name.lower()
        # Remove special chars
        name = re.sub(r"[^a-z0-9-]", "-", name)
        # Remove multiple dashes
        name = re.sub(r"-+", "-", name)
        return name.strip("-")


class PartnersCollection(BaseModel):
    """Collection of external partners."""

    partners: list[ExternalPartner] = Field(default_factory=list)
    source: str = "unknown"
    fetched_at: datetime = Field(default_factory=datetime.now)

    def deduplicate(self) -> "PartnersCollection":
        """Deduplicate partners by merging entries with the same name.

        Merges departments, collaboration types, topics, and comments.
        Uses case-insensitive matching for partner names.
        """
        merged: dict[str, ExternalPartner] = {}
        name_map: dict[str, str] = {}  # lowercase name -> actual name

        for partner in self.partners:
            name_lower = partner.name.lower()

            # Skip excluded partners (like Hidalgo2)
            if name_lower in EXCLUDED_PARTNERS:
                continue

            # Check if we've seen this partner before (case-insensitive)
            if name_lower not in name_map:
                # First occurrence - just add it
                name_map[name_lower] = partner.name
                merged[partner.name] = partner
            else:
                # Merge with existing entry (use the canonical name)
                canonical_name = name_map[name_lower]
                existing = merged[canonical_name]

                # Merge departments (unique, filter out invalid entries)
                if partner.departments:
                    for dept in partner.departments:
                        if dept and dept not in existing.departments and is_valid_department(dept):
                            existing.departments.append(dept)

                # Merge collaboration types (unique)
                if partner.collaboration_types:
                    for collab in partner.collaboration_types:
                        if collab and collab not in existing.collaboration_types:
                            existing.collaboration_types.append(collab)

                # Merge topics (unique)
                if partner.topics:
                    for topic in partner.topics:
                        if topic and topic not in existing.topics:
                            existing.topics.append(topic)

                # Merge comments (unique)
                if partner.comments:
                    for comment in partner.comments:
                        if comment and comment not in existing.comments:
                            existing.comments.append(comment)

        return PartnersCollection(
            partners=list(merged.values()),
            source=self.source,
            fetched_at=self.fetched_at,
        )

    @property
    def by_type(self) -> dict[PartnerType, list[ExternalPartner]]:
        """Group partners by type."""
        result: dict[PartnerType, list[ExternalPartner]] = {}
        for partner in self.partners:
            if partner.partner_type not in result:
                result[partner.partner_type] = []
            result[partner.partner_type].append(partner)
        return result

    @property
    def by_size(self) -> dict[CompanySize, list[ExternalPartner]]:
        """Group partners by company size."""
        result: dict[CompanySize, list[ExternalPartner]] = {}
        for partner in self.partners:
            if partner.company_size not in result:
                result[partner.company_size] = []
            result[partner.company_size].append(partner)
        return result

    @property
    def cofunding_partners(self) -> list[ExternalPartner]:
        """Return only partners with co-funding arrangements."""
        return [p for p in self.partners if p.has_cofunding]

    @property
    def by_status(self) -> dict[PartnerStatus, list[ExternalPartner]]:
        """Group partners by status."""
        result: dict[PartnerStatus, list[ExternalPartner]] = {}
        for partner in self.partners:
            if partner.status not in result:
                result[partner.status] = []
            result[partner.status].append(partner)
        return result


# Default sheet ID for external partners
DEFAULT_SHEET_ID = "1bigC5N-5Zg2SGfUvpyMvYQPHvrSCqY2K"
DEFAULT_SHEET_NAME = "Overview"


class PartnersFetcher:
    """Fetch external partners data from Google Sheets."""

    EXPORT_URL_TEMPLATE = (
        "https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    )

    def __init__(
        self,
        sheet_id: str,
        sheet_name: str = DEFAULT_SHEET_NAME,
    ):
        """Initialize partners fetcher."""
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        self._excel_data: bytes | None = None

    def _fetch_excel(self) -> bytes:
        """Fetch the spreadsheet as XLSX bytes."""
        if self._excel_data is not None:
            return self._excel_data

        url = self.EXPORT_URL_TEMPLATE.format(sheet_id=self.sheet_id)

        try:
            response = urllib.request.urlopen(url)
            self._excel_data = response.read()
            return self._excel_data
        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch Google Sheet. "
                f"Ensure the sheet is publicly accessible. Error: {e}"
            )

    def get_sheet_names(self) -> list[str]:
        """Get list of available sheet names."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required. Install with: pip install pandas")

        data = self._fetch_excel()
        xl = pd.ExcelFile(io.BytesIO(data))
        return xl.sheet_names

    def _load_sheet(self, sheet_name: str | None = None):
        """Load a specific sheet as pandas DataFrame."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required. Install with: pip install pandas")

        data = self._fetch_excel()
        return pd.read_excel(
            io.BytesIO(data),
            sheet_name=sheet_name or self.sheet_name,
        )

    def _parse_topics(self, row: dict) -> list[str]:
        """Parse topic columns (Topics 1-7) to get all topics."""
        topics = []
        for i in range(1, 8):
            # Try capitalized version first
            topic_col = f"Topics {i}"
            value = clean_string(row.get(topic_col))
            # If not found, try lowercase version (for "topics 5")
            if not value:
                topic_col_lower = f"topics {i}"
                value = clean_string(row.get(topic_col_lower))
            if value and value not in topics:
                topics.append(value)
        return topics

    def _parse_row(self, row: dict) -> ExternalPartner | None:
        """Parse a single row into an ExternalPartner."""
        name = clean_string(row.get("Entreprises"))

        if not name:
            return None

        partner_type_raw = clean_string(row.get("Type of External Partners"))
        status_raw = clean_string(row.get("Status"))

        # Parse partner type and company size from the Type column
        partner_type, company_size = PartnerType.from_string(partner_type_raw)

        # Parse department (filter out invalid entries)
        department = clean_string(row.get("Equipe ou departement de l'entreprise"))
        departments = [department] if department and is_valid_department(department) else []

        # Parse collaboration type
        collaboration_type = clean_string(row.get("Type of Collaboration"))
        collaboration_types = [collaboration_type] if collaboration_type else []

        # Parse comments
        comment = clean_string(row.get("Commentaires"))
        comments = [comment] if comment else []

        partner = ExternalPartner(
            name=name,
            partner_type=partner_type,
            partner_type_raw=partner_type_raw,
            departments=departments,
            contact_partner=clean_string(row.get("Contact Entreprise")),
            contact_exama=clean_string(row.get("Contact ExaMA")),
            exama_partner=clean_string(row.get("Partenaire ExaMA")),
            collaboration_types=collaboration_types,
            status=PartnerStatus.from_string(status_raw),
            status_raw=status_raw,
            topics=self._parse_topics(row),
            comments=comments,
            icon=get_partner_icon(name),
            company_size=company_size,
        )

        return partner

    def fetch(self, deduplicate: bool = True) -> PartnersCollection:
        """Fetch all external partners.

        Args:
            deduplicate: If True, merge duplicate partners by name

        Returns:
            PartnersCollection with fetched partners
        """
        df = self._load_sheet()
        partners = []

        for _, row in df.iterrows():
            partner = self._parse_row(row.to_dict())
            if partner:
                partners.append(partner)

        collection = PartnersCollection(
            partners=partners,
            source=f"google-sheets:{self.sheet_id}",
            fetched_at=datetime.now(),
        )

        if deduplicate:
            collection = collection.deduplicate()

        return collection


def fetch_partners(
    sheet_id: str = DEFAULT_SHEET_ID,
    sheet_name: str = DEFAULT_SHEET_NAME,
) -> PartnersCollection:
    """Convenience function to fetch external partners."""
    fetcher = PartnersFetcher(sheet_id=sheet_id, sheet_name=sheet_name)
    return fetcher.fetch()


def fetch_partners_with_config(
    config_path: Path | str | None = None,
) -> PartnersCollection:
    """Fetch external partners using unified configuration.

    Args:
        config_path: Optional path to exama.yaml config file

    Returns:
        PartnersCollection with fetched partners
    """
    # Defaults
    sheet_id = DEFAULT_SHEET_ID
    sheet_name = DEFAULT_SHEET_NAME

    # Try to load from unified config
    if HAS_UNIFIED_CONFIG:
        try:
            config = load_exama_config(config_path)
            partners_config = config.get_partners_config()
            sheet_id = partners_config.sheet_id
            sheet_name = partners_config.sheet_name
        except (FileNotFoundError, AttributeError, Exception):
            pass  # Use defaults

    return fetch_partners(
        sheet_id=sheet_id,
        sheet_name=sheet_name,
    )


def generate_external_partners_section(
    collection: PartnersCollection,
    include_all: bool = True,
    partial: bool = False,
) -> str:
    """Generate AsciiDoc section for external partners.

    Args:
        collection: Collection of external partners
        include_all: Whether to include all partners or only co-funding
        partial: If True, generate partial content without page header

    Returns:
        AsciiDoc formatted string
    """
    lines = []

    partners = collection.partners if include_all else collection.cofunding_partners

    if not partners:
        lines.append("_No external partners available._")
        return "\n".join(lines)

    # Group by type
    by_type = {}
    for partner in partners:
        ptype = partner.partner_type
        if ptype not in by_type:
            by_type[ptype] = []
        by_type[ptype].append(partner)

    # Section header (only for full page, not partial)
    if not partial:
        lines.append("= External Partners")
        lines.append(":page-tags: info")
        lines.append(":parent-catalogs: exama-home")
        lines.append(":page-illustration: fa-solid fa-handshake")
        lines.append(":description: External partners collaborating with the Exa-MA project.")
        lines.append(":icons: font")
        lines.append("")
        lines.append("[.lead]")
        lines.append(f"The Exa-MA project collaborates with {len(partners)} external partners from industry, research organizations, and academia.")
        lines.append("")
    else:
        # Partial header
        lines.append(f"// Total external partners: {len(partners)}")
        lines.append(":sectnums!:")
        lines.append("")

    # Calculate statistics for cards
    cofunding_count = len(collection.cofunding_partners)
    private_partners = [p for p in partners if p.is_private]
    public_partners = [p for p in partners if p.is_public]

    # Private breakdown by size
    private_large = len([p for p in private_partners if p.company_size == CompanySize.LARGE])
    private_sme = len([p for p in private_partners if p.company_size == CompanySize.SME])

    # Public breakdown by type
    public_epic = len([p for p in public_partners if p.partner_type == PartnerType.EPIC])
    public_academic = len([p for p in public_partners if p.partner_type == PartnerType.ACADEMIC])
    public_research_infra = len([p for p in public_partners if p.partner_type == PartnerType.LARGE_SCALE_RESEARCH_INFRA])

    # Statistics cards section
    lines.append("== icon:chart-pie[] Overview")
    lines.append("")
    lines.append(f"icon:handshake[] Total external partners: *{len(partners)}*")
    lines.append("")

    lines.append("[.grid.grid-2.gap-2]")
    lines.append("====")

    # Public partners card
    public_percent = (len(public_partners) / len(partners) * 100) if partners else 0
    lines.append("____")
    lines.append(f"icon:university[size=2x,role=text-primary] *{len(public_partners)}* Public Partners")
    lines.append("")
    lines.append(f"_{public_percent:.1f}% of total_")
    lines.append("")
    # Build public breakdown line
    public_parts = []
    if public_epic > 0:
        public_parts.append(f"icon:flask[] EPIC: *{public_epic}*")
    if public_academic > 0:
        public_parts.append(f"icon:graduation-cap[] Academic: *{public_academic}*")
    if public_research_infra > 0:
        public_parts.append(f"icon:microscope[] Research Infra: *{public_research_infra}*")
    if public_parts:
        lines.append(" | ".join(public_parts))
    lines.append("____")
    lines.append("")

    # Private partners card
    private_percent = (len(private_partners) / len(partners) * 100) if partners else 0
    lines.append("____")
    lines.append(f"icon:building[size=2x,role=text-primary] *{len(private_partners)}* Private Partners")
    lines.append("")
    lines.append(f"_{private_percent:.1f}% of total_")
    lines.append("")
    lines.append(f"icon:industry[] Large Groups: *{private_large}* | icon:briefcase[] SMEs: *{private_sme}*")
    lines.append("____")
    lines.append("")

    # Co-funding card
    phd_cofunding_count = len([p for p in partners if p.has_phd_cofunding])
    cofunding_percent = (cofunding_count / len(partners) * 100) if partners else 0
    lines.append("____")
    lines.append(f"icon:hand-holding-usd[size=2x,role=text-primary] *{cofunding_count}* Co-funding Arrangements")
    lines.append("")
    lines.append(f"_{cofunding_percent:.1f}% of total_")
    lines.append("")
    lines.append(f"icon:user-graduate[] PhD Co-funding: *{phd_cofunding_count}*")
    lines.append("____")
    lines.append("")

    # Funded Projects card
    funded_projects_count = len([p for p in partners if p.has_funded_projects])
    if funded_projects_count > 0:
        funded_percent = (funded_projects_count / len(partners) * 100) if partners else 0
        lines.append("____")
        lines.append(f"icon:project-diagram[size=2x,role=text-primary] *{funded_projects_count}* Funded Projects")
        lines.append("")
        lines.append(f"_{funded_percent:.1f}% of total_")
        lines.append("")
        lines.append("ANR PRCI, European, and other collaborative research projects")
        lines.append("____")
        lines.append("")

    lines.append("====")
    lines.append("")

    # Generate sections by company size (only for Entreprise type)
    by_size = {}
    other_partners = []

    for partner in partners:
        if partner.partner_type == PartnerType.ENTREPRISE:
            size = partner.company_size
            if size not in by_size:
                by_size[size] = []
            by_size[size].append(partner)
        else:
            other_partners.append(partner)

    # Display company partners by size
    size_order = [
        (CompanySize.LARGE, "Large Groups"),
        (CompanySize.MIDCAP, "Mid Caps"),
        (CompanySize.SME, "SMEs"),
    ]

    for size, title in size_order:
        if size not in by_size:
            continue

        size_partners = sorted(by_size[size], key=lambda p: p.name.lower())

        lines.append(f"== {title}")
        lines.append("")

        lines.append("[.grid.grid-2.gap-2]")
        lines.append("====")

        for partner in size_partners:
            lines.append("____")
            icon_str = f"icon:{partner.icon}[size=2x,role=text-primary]"
            # Add badges if applicable
            badges = ""
            if partner.has_cofunding:
                badges += " [.badge.badge-cofunding]#icon:hand-holding-usd[] Co-funding#"
            if partner.has_funded_projects:
                badges += " [.badge.badge-funded]#icon:project-diagram[] Funded Projects#"
            lines.append(f"{icon_str} *{partner.name}*{badges}")
            lines.append("")

            # Display all departments
            if partner.departments:
                for dept in partner.departments:
                    lines.append(f"_{dept}_")
                lines.append("")

            # Display all collaboration types
            if partner.collaboration_types:
                collab_str = ", ".join(partner.collaboration_types)
                lines.append(f"*Collaboration:* {collab_str}")
                lines.append("")

            # Display all topics
            if partner.topics:
                lines.append(f"*Topics:* {partner.topics_display}")
                lines.append("")

            lines.append("____")
            lines.append("")

        lines.append("====")
        lines.append("")

    # Display Research Organizations, Academic partners, and Research Infrastructure
    for ptype in [PartnerType.EPIC, PartnerType.ACADEMIC, PartnerType.LARGE_SCALE_RESEARCH_INFRA]:
        type_partners = [p for p in other_partners if p.partner_type == ptype]
        if not type_partners:
            continue

        type_partners = sorted(type_partners, key=lambda p: p.name.lower())

        type_title = {
            PartnerType.EPIC: "Research Organizations (EPIC)",
            PartnerType.ACADEMIC: "Academic Partners",
            PartnerType.LARGE_SCALE_RESEARCH_INFRA: "Large scale Research Infrastructure",
        }
        lines.append(f"== {type_title.get(ptype, ptype.value)}")
        lines.append("")

        lines.append("[.grid.grid-2.gap-2]")
        lines.append("====")

        for partner in type_partners:
            lines.append("____")
            icon_str = f"icon:{partner.icon}[size=2x,role=text-primary]"
            # Add badges if applicable
            badges = ""
            if partner.has_cofunding:
                badges += " [.badge.badge-cofunding]#icon:hand-holding-usd[] Co-funding#"
            if partner.has_funded_projects:
                badges += " [.badge.badge-funded]#icon:project-diagram[] Funded Projects#"
            lines.append(f"{icon_str} *{partner.name}*{badges}")
            lines.append("")

            # Display all departments
            if partner.departments:
                for dept in partner.departments:
                    lines.append(f"_{dept}_")
                lines.append("")

            # Display all collaboration types
            if partner.collaboration_types:
                collab_str = ", ".join(partner.collaboration_types)
                lines.append(f"*Collaboration:* {collab_str}")
                lines.append("")

            # Display all topics
            if partner.topics:
                lines.append(f"*Topics:* {partner.topics_display}")
                lines.append("")

            lines.append("____")
            lines.append("")

        lines.append("====")
        lines.append("")

    # Summary statistics (reusing values calculated for cards above)
    lines.append("== Collaboration Overview")
    lines.append("")

    # Get mid caps count and public research count for the detailed table
    private_midcap = len([p for p in private_partners if p.company_size == CompanySize.MIDCAP])
    public_research = len([p for p in public_partners if p.partner_type == PartnerType.PUBLIC_RESEARCH])

    # Count other partners (neither public nor private)
    other_partners_count = len([p for p in partners if not p.is_public and not p.is_private])

    lines.append("[.striped,cols=\"2,1\",options=\"header\"]")
    lines.append("|===")
    lines.append("|Indicator |Value")
    lines.append("")
    lines.append(f"|*Total External Partners* |*{len(partners)}*")
    lines.append("")
    lines.append(f"|*Public Partners* |*{len(public_partners)}*")
    lines.append(f"|{{nbsp}}{{nbsp}}EPIC |{public_epic}")
    lines.append(f"|{{nbsp}}{{nbsp}}Academic |{public_academic}")
    if public_research > 0:
        lines.append(f"|{{nbsp}}{{nbsp}}Public Research |{public_research}")
    if public_research_infra > 0:
        lines.append(f"|{{nbsp}}{{nbsp}}Research Infrastructure |{public_research_infra}")
    lines.append("")
    lines.append(f"|*Private Partners* |*{len(private_partners)}*")
    lines.append(f"|{{nbsp}}{{nbsp}}Large Groups |{private_large}")
    if private_midcap > 0:
        lines.append(f"|{{nbsp}}{{nbsp}}Mid Caps |{private_midcap}")
    lines.append(f"|{{nbsp}}{{nbsp}}SMEs |{private_sme}")
    lines.append("")
    if other_partners_count > 0:
        lines.append(f"|Other Partners |{other_partners_count}")
        lines.append("")
    lines.append(f"|Co-funding Arrangements |{cofunding_count}")
    lines.append("|===")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    # Quick test
    collection = fetch_partners()
    print(f"Fetched {len(collection.partners)} external partners")

    by_type = collection.by_type
    print("\nBy Type:")
    for ptype, partners in by_type.items():
        print(f"  {ptype.value}: {len(partners)}")

    print(f"\nCo-funding partners: {len(collection.cofunding_partners)}")

    print("\n" + "=" * 50)
    print("Generated AsciiDoc:\n")
    print(generate_external_partners_section(collection))
