"""
Team and recruited personnel data harvesting.

Fetches recruited personnel (PhD students, postdocs, engineers) from Google Sheets.

Supports configuration from:
- Command line arguments (highest priority)
- Unified exama.yaml config file
- Default values (fallback)
"""

from __future__ import annotations

import io
import math
import re
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


def parse_date(value: Any) -> datetime | None:
    """Parse various date formats including French DD/MM/YYYY and Month Year formats."""
    if is_nan(value):
        return None
    if isinstance(value, datetime):
        return value
    str_val = str(value).strip()

    # Try standard formats (French DD/MM/YYYY format is prioritized)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str_val.split()[0], fmt)
        except (ValueError, TypeError):
            continue

    # Try "Month Year" formats (English and French)
    # English: "January 2024", "Jan 2024"
    for fmt in ("%B %Y", "%b %Y"):
        try:
            return datetime.strptime(str_val, fmt)
        except (ValueError, TypeError):
            continue

    # Try French month names
    french_months = {
        "janvier": "January", "janv": "Jan",
        "février": "February", "févr": "Feb", "fevrier": "February", "fevr": "Feb",
        "mars": "March",
        "avril": "April", "avr": "Apr",
        "mai": "May",
        "juin": "June",
        "juillet": "July", "juil": "Jul",
        "août": "August", "aout": "August", "aoû": "Aug",
        "septembre": "September", "sept": "Sep",
        "octobre": "October", "oct": "Oct",
        "novembre": "November", "nov": "Nov",
        "décembre": "December", "déc": "Dec", "decembre": "December", "dec": "Dec",
    }

    # Try to parse French month names by converting to English
    str_lower = str_val.lower()
    for french, english in french_months.items():
        if french in str_lower:
            # Replace French month with English equivalent
            str_english = str_lower.replace(french, english)
            for fmt in ("%B %Y", "%b %Y"):
                try:
                    return datetime.strptime(str_english, fmt)
                except (ValueError, TypeError):
                    continue

    return None


class Gender(str, Enum):
    """Gender classification."""
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


# Common French/International first names for gender detection
FEMALE_NAMES = {
    "alice", "amélie", "amelie", "anna", "anne", "béatrice", "beatrice", "camille",
    "caroline", "catherine", "céline", "celine", "charlotte", "chloé", "chloe",
    "claire", "clémence", "clemence", "daria", "delphine", "diane", "elise", "élise",
    "elisabeth", "émilie", "emilie", "emma", "florence", "françoise", "francoise",
    "gabrielle", "hélène", "helene", "isabelle", "jeanne", "julie", "juliette",
    "laure", "laurence", "léa", "lea", "lise", "louise", "lucie", "madeleine",
    "manon", "margot", "marguerite", "marie", "marine", "marion", "martine",
    "mathilde", "mélanie", "melanie", "nathalie", "nicole", "pauline", "sarah",
    "sophie", "stéphanie", "stephanie", "sylvie", "valérie", "valerie", "véronique",
    "veronique", "virginie", "zineb", "fatima", "leila", "nadia", "sofia", "maria",
    "elena", "olga", "anna", "natalia", "ekaterina", "alexandra", "victoria",
}

MALE_NAMES = {
    "adrien", "alexandre", "alexis", "alain", "antoine", "arnaud", "arthur",
    "benjamin", "benoit", "benoît", "bernard", "bertrand", "bruno", "charles",
    "christian", "christophe", "claude", "clément", "clement", "damien", "daniel",
    "david", "denis", "didier", "dominique", "édouard", "edouard", "emmanuel",
    "eric", "éric", "etienne", "étienne", "fabien", "fabrice", "florian",
    "franck", "françois", "francois", "frédéric", "frederic", "gabriel", "gaël",
    "gael", "georges", "gérard", "gerard", "guillaume", "guy", "henri", "hervé",
    "herve", "hugo", "jacques", "jean", "jérôme", "jerome", "jonathan", "joseph",
    "julien", "laurent", "lionel", "louis", "luc", "lucas", "ludovic", "marc",
    "marcel", "martin", "mathieu", "matthieu", "maurice", "maxime", "michel",
    "nicolas", "olivier", "pascal", "patrick", "paul", "philippe", "pierre",
    "quentin", "raphaël", "raphael", "raymond", "rémi", "remi", "renaud", "richard",
    "robert", "romain", "samuel", "sébastien", "sebastien", "serge", "simon",
    "stéphane", "stephane", "sylvain", "thierry", "thomas", "vincent", "xavier",
    "yann", "yannick", "yves", "hassan", "mohamed", "ahmed", "ali", "omar",
    "karim", "samir", "mahamat", "pape", "mahmoud", "christos", "lukas", "utpal",
    "hung", "dinh", "xinye", "amaury", "brieuc", "tom", "mikaël", "mikael",
}


def detect_gender(first_name: str) -> Gender:
    """Detect gender from first name using common name lists."""
    name_lower = first_name.lower().strip()
    # Handle compound names (e.g., "Jean-Pierre")
    first_part = name_lower.split("-")[0].split()[0]

    if first_part in FEMALE_NAMES:
        return Gender.FEMALE
    if first_part in MALE_NAMES:
        return Gender.MALE
    return Gender.UNKNOWN


class PositionType(str, Enum):
    """Types of recruited positions."""
    PHD = "PhD"
    POSTDOC = "Post-Doc"
    RESEARCH_ENGINEER = "IR-CDD"
    PERMANENT = "Permanent"
    OTHER = "Other"

    @classmethod
    def from_string(cls, value: str | None) -> "PositionType":
        """Parse position type from string."""
        if not value:
            return cls.OTHER
        value_lower = value.lower().strip()
        if "phd" in value_lower or "thèse" in value_lower:
            return cls.PHD
        if "post" in value_lower:
            return cls.POSTDOC
        if "ir" in value_lower or "engineer" in value_lower or "ingénieur" in value_lower:
            return cls.RESEARCH_ENGINEER
        if "permanent" in value_lower or "cdi" in value_lower:
            return cls.PERMANENT
        return cls.OTHER


# Institution name normalization
INSTITUTION_NAMES = {
    "CEA": "CEA",
    "INRIA": "Inria",
    "Inria": "Inria",
    "EP": "École Polytechnique",
    "Polytechnique": "École Polytechnique",
    "Unistra": "Université de Strasbourg",
    "SorbonneU": "Sorbonne Université",
    "Sorbonne": "Sorbonne Université",
    "CNRS": "CNRS",
    "Lille": "Université de Lille",
}


def normalize_institution(name: str | None) -> str:
    """Normalize institution name for display."""
    if not name:
        return "Unknown"
    return INSTITUTION_NAMES.get(name, name)


class RecruitedPerson(BaseModel):
    """A person recruited/funded by the Exa-MA project."""

    first_name: str
    surname: str
    email: str | None = None
    work_packages: list[str] = Field(default_factory=list)  # Support multiple WPs
    funded_by_exama: bool = True
    start_date: datetime | None = None
    end_date: datetime | None = None
    other_info: str | None = None
    position: PositionType = PositionType.OTHER
    position_raw: str | None = None
    team: str | None = None
    partner: str | None = None
    institution: str | None = None
    advisors: list[str] = Field(default_factory=list)
    # Gender override from spreadsheet column (takes precedence over name detection)
    _gender_override: Gender | None = None

    model_config = {"arbitrary_types_allowed": True}

    @property
    def work_package(self) -> str | None:
        """Backward-compatible property returning primary (first) work package."""
        return self.work_packages[0] if self.work_packages else None

    @property
    def full_name(self) -> str:
        """Return full name."""
        return f"{self.first_name} {self.surname}"

    @property
    def slug(self) -> str:
        """Return URL-safe slug for the person."""
        name = f"{self.first_name}-{self.surname}".lower()
        # Remove accents and special chars
        replacements = {
            "é": "e", "è": "e", "ê": "e", "ë": "e",
            "à": "a", "â": "a", "ä": "a",
            "î": "i", "ï": "i",
            "ô": "o", "ö": "o",
            "ù": "u", "û": "u", "ü": "u",
            "ç": "c", "ñ": "n",
        }
        for old, new in replacements.items():
            name = name.replace(old, new)
        return re.sub(r"[^a-z0-9-]", "-", name)

    @property
    def gender(self) -> Gender:
        """Get gender - uses override from spreadsheet column if set, otherwise detects from name."""
        if self._gender_override is not None:
            return self._gender_override
        return detect_gender(self.first_name)

    @property
    def is_active(self) -> bool:
        """Check if the person is currently active (no end date or end date in future)."""
        if self.end_date is None:
            return True
        return self.end_date > datetime.now()

    @property
    def wp_numbers(self) -> list[int]:
        """Extract WP numbers from all work packages."""
        numbers = []
        for wp in self.work_packages:
            match = re.search(r"WP\s*(\d+)", wp, re.IGNORECASE)
            if match:
                numbers.append(int(match.group(1)))
        return sorted(numbers)

    @property
    def wp_number(self) -> int | None:
        """Extract WP number from primary work package (backward compat)."""
        return self.wp_numbers[0] if self.wp_numbers else None

    @property
    def position_display(self) -> str:
        """Return display-friendly position string."""
        position_map = {
            PositionType.PHD: "PhD Student",
            PositionType.POSTDOC: "Postdoc",
            PositionType.RESEARCH_ENGINEER: "Research Engineer",
            PositionType.PERMANENT: "Permanent Researcher",
            PositionType.OTHER: self.position_raw or "Staff",
        }
        return position_map.get(self.position, self.position_raw or "Staff")

    @property
    def institution_display(self) -> str:
        """Return normalized institution name.

        Prioritizes 'institution' (employer) over 'partner' as per Google Sheet
        column I (Institution employer) being the authoritative source.
        """
        return normalize_institution(self.institution or self.partner)

    @property
    def has_detailed_info(self) -> bool:
        """Check if person has detailed work description worth a dedicated page."""
        if not self.other_info:
            return False
        # Has detailed info if other_info is substantial (>100 chars) or multi-line
        return len(self.other_info) > 100 or "\n" in self.other_info

    @property
    def start_date_display(self) -> str:
        """Format start date for display."""
        if not self.start_date:
            return "Project start"
        return self.start_date.strftime("%B %Y")

    @property
    def end_date_display(self) -> str | None:
        """Format end date for display."""
        if not self.end_date:
            return None
        return self.end_date.strftime("%B %Y")

    @property
    def duration_display(self) -> str:
        """Calculate and display duration."""
        start = self.start_date or datetime(2023, 6, 1)  # Project start
        end = self.end_date or datetime.now()
        months = (end.year - start.year) * 12 + (end.month - start.month)
        if months < 12:
            return f"{months} months"
        years = months // 12
        remaining_months = months % 12
        if remaining_months == 0:
            return f"{years} year{'s' if years > 1 else ''}"
        return f"{years} year{'s' if years > 1 else ''}, {remaining_months} months"


class GenderStats(BaseModel):
    """Gender statistics for a collection."""
    male: int = 0
    female: int = 0
    unknown: int = 0

    @property
    def total(self) -> int:
        return self.male + self.female + self.unknown

    @property
    def female_percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.female / self.total) * 100

    @property
    def male_percentage(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.male / self.total) * 100


class RecruitedCollection(BaseModel):
    """Collection of recruited personnel."""

    personnel: list[RecruitedPerson] = Field(default_factory=list)
    source: str = "unknown"
    fetched_at: datetime = Field(default_factory=datetime.now)

    @property
    def active_personnel(self) -> list[RecruitedPerson]:
        """Return only currently active personnel."""
        return [p for p in self.personnel if p.is_active]

    @property
    def funded_personnel(self) -> list[RecruitedPerson]:
        """Return only personnel funded by Exa-MA."""
        return [p for p in self.personnel if p.funded_by_exama]

    @property
    def gender_stats(self) -> GenderStats:
        """Calculate gender statistics."""
        stats = GenderStats()
        for p in self.personnel:
            if p.gender == Gender.MALE:
                stats.male += 1
            elif p.gender == Gender.FEMALE:
                stats.female += 1
            else:
                stats.unknown += 1
        return stats

    def unique_personnel(self) -> list[RecruitedPerson]:
        """Return deduplicated list of personnel."""
        seen = set()
        unique = []
        for p in self.personnel:
            if p.full_name not in seen:
                seen.add(p.full_name)
                unique.append(p)
        return unique

    def by_work_package(self) -> dict[str, list[RecruitedPerson]]:
        """Group personnel by work package.

        Note: A person working on multiple WPs will appear in each WP's list.
        """
        result: dict[str, list[RecruitedPerson]] = {}
        for person in self.personnel:
            wps = person.work_packages if person.work_packages else ["Unknown"]
            for wp in wps:
                if wp not in result:
                    result[wp] = []
                result[wp].append(person)
        return dict(sorted(result.items(), key=lambda x: (
            int(x[0].replace("WP", "").strip()) if x[0].startswith("WP") else 99
        )))

    def by_position(self) -> dict[PositionType, list[RecruitedPerson]]:
        """Group personnel by position type."""
        result: dict[PositionType, list[RecruitedPerson]] = {}
        for person in self.personnel:
            if person.position not in result:
                result[person.position] = []
            result[person.position].append(person)
        return result

    def by_partner(self) -> dict[str, list[RecruitedPerson]]:
        """Group personnel by partner institution."""
        result: dict[str, list[RecruitedPerson]] = {}
        for person in self.personnel:
            partner = person.partner or person.institution or "Unknown"
            if partner not in result:
                result[partner] = []
            result[partner].append(person)
        return dict(sorted(result.items()))


# Default sheet ID for Exa-MA contact data
DEFAULT_SHEET_ID = "1-QuexB1IiP2O1ebNhp1OrQb6hOx8BXA5"
DEFAULT_SHEET_NAME = "All Exa-MA"  # Source of truth with all personnel


class TeamFetcher:
    """Fetch team/recruited personnel data from Google Sheets."""

    EXPORT_URL_TEMPLATE = (
        "https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    )

    def __init__(
        self,
        sheet_id: str,
        sheet_name: str = DEFAULT_SHEET_NAME,
    ):
        """Initialize team fetcher."""
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
        # Disable automatic date parsing to ensure we use our custom parse_date function
        # which correctly handles French DD/MM/YYYY format
        return pd.read_excel(
            io.BytesIO(data),
            sheet_name=sheet_name or self.sheet_name,
            parse_dates=False,  # Disable auto date parsing
            date_format=None,   # Don't infer date format
        )

    def _parse_work_packages(self, row: dict) -> list[str]:
        """Parse WP columns (WP0-WP7) to get all work packages.

        Returns all WPs where the person has involvement, sorted by WP number.
        """
        wp_involvement = []
        # Include WP0 (Project Office) through WP7
        for wp_num in range(0, 8):
            wp_col = f"WP{wp_num}"
            value = row.get(wp_col)
            if not is_nan(value) and isinstance(value, (int, float)) and value > 0:
                wp_involvement.append(wp_num)

        # Return sorted list of WP strings
        return [f"WP{num}" for num in sorted(wp_involvement)]

    def _parse_gender_from_column(self, row: dict) -> Gender:
        """Parse gender from the 'Woman' column."""
        woman_val = row.get("Woman")
        if is_nan(woman_val):
            return Gender.MALE  # Default assumption when not specified
        if isinstance(woman_val, (int, float)) and woman_val == 1:
            return Gender.FEMALE
        if isinstance(woman_val, (int, float)) and woman_val == 0:
            return Gender.MALE
        return Gender.UNKNOWN

    def _parse_advisors(self, row: dict) -> list[str]:
        """Parse advisors from the 'Advisor' column.

        Supports multiple advisors separated by comma, semicolon, or newline.
        """
        advisor_raw = row.get("Advisor")
        if is_nan(advisor_raw) or not advisor_raw:
            return []

        advisor_str = str(advisor_raw).strip()
        if not advisor_str:
            return []

        # Split by common separators: comma, semicolon, or newline
        import re
        advisors = re.split(r"[,;\n]+", advisor_str)
        return [a.strip() for a in advisors if a.strip()]

    def _parse_row(self, row: dict) -> RecruitedPerson | None:
        """Parse a single row into a RecruitedPerson.

        Supports both 'All Exa-MA' sheet format and 'Recruitments only' format.
        """
        first_name = clean_string(row.get("First name"))
        surname = clean_string(row.get("Surname"))

        if not first_name or not surname:
            return None

        # Parse funded status
        funded_raw = row.get("Funded by Exa-MA")
        funded = False
        if not is_nan(funded_raw):
            if isinstance(funded_raw, bool):
                funded = funded_raw
            elif isinstance(funded_raw, (int, float)):
                funded = funded_raw == 1
            else:
                funded = str(funded_raw).lower() in ("1", "yes", "true", "x")

        position_raw = clean_string(row.get("Position"))

        # Parse work packages - try WP column first, then individual WP0-WP7 columns
        wp_from_column = clean_string(row.get("WP"))
        if wp_from_column:
            work_packages = [wp_from_column]
        else:
            work_packages = self._parse_work_packages(row)

        # Parse gender - use 'Woman' column if available, otherwise detect from name
        gender_from_col = self._parse_gender_from_column(row)

        person = RecruitedPerson(
            first_name=first_name,
            surname=surname,
            email=clean_string(row.get("Email")),
            work_packages=work_packages,
            funded_by_exama=funded,
            start_date=parse_date(row.get("Start date (if the person was not here from start)")),
            end_date=parse_date(row.get("End date (if the person has left)")),
            other_info=clean_string(row.get("Other info")),
            position=PositionType.from_string(position_raw),
            position_raw=position_raw,
            team=clean_string(row.get("Team")),
            partner=clean_string(row.get("Partner")),
            institution=clean_string(row.get("Institution (employer)")),
            advisors=self._parse_advisors(row),
        )

        # Override gender detection with explicit column value if available
        person._gender_override = gender_from_col

        return person

    def fetch(self, funded_only: bool = False, active_only: bool = False) -> RecruitedCollection:
        """Fetch all recruited personnel."""
        df = self._load_sheet()
        personnel = []

        for _, row in df.iterrows():
            person = self._parse_row(row.to_dict())
            if person:
                if funded_only and not person.funded_by_exama:
                    continue
                if active_only and not person.is_active:
                    continue
                personnel.append(person)

        return RecruitedCollection(
            personnel=personnel,
            source=f"google-sheets:{self.sheet_id}",
            fetched_at=datetime.now(),
        )


def fetch_recruited(
    sheet_id: str = DEFAULT_SHEET_ID,
    sheet_name: str = DEFAULT_SHEET_NAME,
    funded_only: bool = True,
    active_only: bool = False,
) -> RecruitedCollection:
    """Convenience function to fetch recruited personnel."""
    fetcher = TeamFetcher(sheet_id=sheet_id, sheet_name=sheet_name)
    return fetcher.fetch(funded_only=funded_only, active_only=active_only)


def fetch_recruited_with_config(
    config_path: Path | str | None = None,
    funded_only: bool | None = None,
    active_only: bool | None = None,
) -> RecruitedCollection:
    """Fetch recruited personnel using unified configuration.

    Args:
        config_path: Optional path to exama.yaml config file
        funded_only: Override config's funded_only setting
        active_only: Override config's active_only setting

    Returns:
        RecruitedCollection with fetched personnel
    """
    # Defaults
    sheet_id = DEFAULT_SHEET_ID
    sheet_name = DEFAULT_SHEET_NAME
    filter_funded_only = True
    filter_active_only = False

    # Try to load from unified config
    if HAS_UNIFIED_CONFIG:
        try:
            config = load_exama_config(config_path)
            team_config = config.get_team_config()
            sheet_id = team_config.sheet_id
            sheet_name = team_config.sheet_name
            filter_funded_only = team_config.filter.funded_only
            filter_active_only = team_config.filter.active_only
        except (FileNotFoundError, Exception):
            pass  # Use defaults

    # CLI args override config
    if funded_only is not None:
        filter_funded_only = funded_only
    if active_only is not None:
        filter_active_only = active_only

    return fetch_recruited(
        sheet_id=sheet_id,
        sheet_name=sheet_name,
        funded_only=filter_funded_only,
        active_only=filter_active_only,
    )


# Work Package titles
WP_TITLES = {
    "WP0": "Project Management",
    "WP1": "Discretization",
    "WP2": "Model order reduction, Surrogate, Scientific Machine Learning methods",
    "WP3": "Solvers for linear algebra and multiphysics",
    "WP4": "Combine Data and Models, Inverse Problems at Exascale",
    "WP5": "Optimization",
    "WP6": "Uncertainty Quantification",
    "WP7": "Showroom, Benchmarking and Co-Design coordination",
}


def generate_person_page(person: RecruitedPerson) -> str:
    """Generate an individual AsciiDoc page for a person with detailed info.

    Args:
        person: The recruited person

    Returns:
        AsciiDoc page content
    """
    lines = []

    # Page header
    lines.append(f"= {person.full_name}")
    lines.append(f":page-role: recruited-person")
    lines.append(f":page-position: {person.position_display}")
    lines.append(f":page-wp: {person.work_package or 'N/A'}")
    lines.append(f":page-institution: {person.institution_display}")
    lines.append("")

    # Profile section
    lines.append("[.person-profile]")
    lines.append("--")

    # Basic info card
    lines.append("[.info-card]")
    lines.append("====")
    lines.append(f"[.position]*{person.position_display}*")
    lines.append("")

    if person.work_package:
        wp_title = WP_TITLES.get(person.work_package, person.work_package)
        lines.append(f"*Work Package:* {person.work_package} - {wp_title}")
        lines.append("")

    lines.append(f"*Institution:* {person.institution_display}")
    lines.append("")

    # Dates
    lines.append(f"*Started:* {person.start_date_display}")
    if person.end_date_display:
        lines.append(f" +")
        lines.append(f"*Ended:* {person.end_date_display}")
    lines.append("")
    lines.append(f"*Duration:* {person.duration_display}")
    lines.append("====")
    lines.append("--")
    lines.append("")

    # Work description section
    if person.other_info:
        lines.append("== Research Work")
        lines.append("")
        # Convert newlines to proper AsciiDoc formatting
        info_lines = person.other_info.replace("\n", " +\n")
        lines.append(info_lines)
        lines.append("")

    return "\n".join(lines)


def generate_recruited_section(
    collection: RecruitedCollection,
    active_only: bool = False,
    generate_individual_pages: bool = False,
    output_dir: Path | None = None,
) -> str:
    """Generate a complete AsciiDoc section for recruited personnel.

    Uses table format similar to publications, grouped by position type.

    Args:
        collection: Collection of recruited personnel
        active_only: Whether to only include active personnel
        generate_individual_pages: Whether to generate individual pages
        output_dir: Directory for individual pages (if generating)

    Returns:
        Complete AsciiDoc section string
    """
    lines = []

    # Use active personnel if requested and deduplicate
    personnel = collection.active_personnel if active_only else collection.personnel
    personnel = list({p.full_name: p for p in personnel}.values())

    # Calculate statistics
    total = len(personnel)
    temp_collection = RecruitedCollection(personnel=personnel)
    by_pos = temp_collection.by_position()
    gender_stats = temp_collection.gender_stats

    # Generate individual pages if requested
    people_with_pages = []
    if generate_individual_pages and output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for person in personnel:
            if person.has_detailed_info:
                page_content = generate_person_page(person)
                page_path = output_dir / f"{person.slug}.adoc"
                page_path.write_text(page_content)
                people_with_pages.append(person)

    # Comment with total count
    lines.append(f"// Total recruited personnel: {total}")
    lines.append(":sectnums!:")
    lines.append("")

    # Position type config
    position_config = {
        PositionType.PHD: {
            "title": "PhD Students",
            "icon": "graduation-cap",
        },
        PositionType.POSTDOC: {
            "title": "Postdoctoral Researchers",
            "icon": "flask",
        },
        PositionType.RESEARCH_ENGINEER: {
            "title": "Research Engineers",
            "icon": "cogs",
        },
    }

    position_order = [
        PositionType.PHD,
        PositionType.POSTDOC,
        PositionType.RESEARCH_ENGINEER,
    ]

    # Generate table for each position type
    for pos_type in position_order:
        if pos_type not in by_pos:
            continue
        people = by_pos[pos_type]
        config = position_config.get(pos_type, {"title": pos_type.value, "icon": "user"})

        lines.append("[discrete]")
        lines.append(f"== icon:{config['icon']}[] {config['title']}")
        lines.append("")
        lines.append(f"_{len(people)} personnel_")
        lines.append("")

        # Table header - Last name first, then First name
        lines.append("[.striped.recruited,cols=\"2,2,2,2,2,2\",options=\"header\"]")
        lines.append("|===")
        lines.append("|Last Name |First Name |Work Package |Institution |Period |Advisor(s)")
        lines.append("")

        # Sort by primary work package first, then by surname
        def sort_key(p):
            # Primary WP number for sorting (Unknown = 99)
            wp_nums = p.wp_numbers
            wp_num = wp_nums[0] if wp_nums else 99
            return (wp_num, p.surname.lower())

        for person in sorted(people, key=sort_key):
            # Last name with optional link to individual page
            if person in people_with_pages:
                surname_str = f"*xref:team/{person.slug}.adoc[{person.surname}]*"
            else:
                surname_str = f"*{person.surname}*"

            # First name
            firstname_str = person.first_name

            # Work packages (show all, with titles)
            wp_str = ""
            if person.work_packages:
                wp_parts = []
                for wp in person.work_packages:
                    wp_title = WP_TITLES.get(wp, "")
                    if wp_title:
                        wp_parts.append(f"{wp}: {wp_title}")
                    else:
                        wp_parts.append(wp)
                wp_str = " +\n".join(wp_parts)  # Line break between multiple WPs

            # Institution (employer) and Partner (collaboration)
            inst_str = person.institution_display
            # Show partner if different from institution to highlight collaborations
            if person.partner and person.institution:
                partner_norm = normalize_institution(person.partner)
                inst_norm = normalize_institution(person.institution)
                if partner_norm != inst_norm:
                    inst_str = f"{inst_norm} +\n_(Partner: {partner_norm})_"

            # Period
            period_str = person.start_date_display
            if person.end_date_display:
                period_str += f" - {person.end_date_display}"
            else:
                period_str += " - Present"

            # Advisors (show all, with line breaks)
            advisor_str = " +\n".join(person.advisors) if person.advisors else ""

            lines.append(f"|{surname_str}")
            lines.append(f"|{firstname_str}")
            lines.append(f"|{wp_str}")
            lines.append(f"|{inst_str}")
            lines.append(f"|{period_str}")
            lines.append(f"|{advisor_str}")
            lines.append("")

        lines.append("|===")
        lines.append("")

    # Add KPI summary at the end
    phd_count = len(by_pos.get(PositionType.PHD, []))
    postdoc_count = len(by_pos.get(PositionType.POSTDOC, []))
    engineer_count = len(by_pos.get(PositionType.RESEARCH_ENGINEER, []))

    lines.append("[discrete]")
    lines.append("== Key Indicators")
    lines.append("")
    lines.append("[.striped,cols=\"2,1\",options=\"header\"]")
    lines.append("|===")
    lines.append("|Indicator |Value")
    lines.append("")
    lines.append(f"|Total Recruited Personnel |*{total}*")
    lines.append(f"|PhD Students |{phd_count}")
    lines.append(f"|Postdoctoral Researchers |{postdoc_count}")
    lines.append(f"|Research Engineers |{engineer_count}")
    lines.append(f"|Women |{gender_stats.female} ({gender_stats.female_percentage:.0f}%)")
    lines.append(f"|Men |{gender_stats.male} ({gender_stats.male_percentage:.0f}%)")
    lines.append("|===")
    lines.append("")

    return "\n".join(lines)


def generate_team_asciidoc(
    collection: RecruitedCollection,
    include_email: bool = False,
    group_by: str = "position",
    active_only: bool = False,
) -> str:
    """Generate AsciiDoc content for the recruited personnel section.

    Args:
        collection: Collection of recruited personnel
        include_email: Whether to include email addresses
        group_by: How to group personnel ("wp", "position", "partner")
        active_only: Whether to only include active personnel

    Returns:
        AsciiDoc formatted string
    """
    if group_by == "position":
        return generate_recruited_section(collection, active_only=active_only)

    lines = []
    personnel = collection.active_personnel if active_only else collection.personnel
    personnel = list({p.full_name: p for p in personnel}.values())
    temp_collection = RecruitedCollection(personnel=personnel)

    if group_by == "wp":
        grouped = temp_collection.by_work_package()

        lines.append("[.grid.grid-2.gap-2]")
        lines.append("====")

        for wp, people in grouped.items():
            title = f"{wp}: {WP_TITLES.get(wp, '')}"
            lines.append("____")
            lines.append(f"*{title}*")
            lines.append("")
            for person in sorted(people, key=lambda p: p.surname):
                email_part = f" ({person.email})" if include_email and person.email else ""
                position_part = f" _({person.position_display})_"
                lines.append(f"- {person.full_name}{position_part}{email_part}")
            lines.append("____")
            lines.append("")

        lines.append("====")

    elif group_by == "partner":
        grouped = temp_collection.by_partner()
        for partner, people in grouped.items():
            lines.append(f"=== {normalize_institution(partner)}")
            lines.append("")
            for person in sorted(people, key=lambda p: p.surname):
                wp_part = f" ({person.work_package})" if person.work_package else ""
                lines.append(f"- {person.full_name} _{person.position_display}_{wp_part}")
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    # Quick test
    collection = fetch_recruited(funded_only=True)
    personnel = collection.unique_personnel()
    print(f"Fetched {len(personnel)} unique recruited personnel")
    print(f"Active: {len([p for p in personnel if p.is_active])}")

    # Gender stats
    stats = collection.gender_stats
    print(f"\nGender Statistics:")
    print(f"  Male: {stats.male} ({stats.male_percentage:.1f}%)")
    print(f"  Female: {stats.female} ({stats.female_percentage:.1f}%)")
    print(f"  Unknown: {stats.unknown}")

    print("\nBy Position:")
    for pos, people in collection.by_position().items():
        unique_people = list({p.full_name: p for p in people}.values())
        print(f"  {pos.value}: {len(unique_people)}")

    print("\n" + "=" * 50)
    print("Generated AsciiDoc:\n")
    print(generate_recruited_section(collection))
