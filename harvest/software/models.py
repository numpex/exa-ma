"""
Pydantic models for software and application metadata.

These models represent the structure of software and application data from the
Excel/Google Sheets source and provide validation and type safety.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_serializer, field_validator


class BenchmarkStatus(str, Enum):
    """Benchmark availability status."""

    NOT_YET = "not_yet"
    CPU_ONLY = "cpu_only"
    GPU_ONLY = "gpu_only"
    CPU_OR_GPU = "cpu_or_gpu"
    BOTH = "both"

    @classmethod
    def from_string(cls, value: str | None) -> BenchmarkStatus | None:
        """Parse benchmark status from Excel string."""
        if not value or str(value).strip().upper() == "NOT YET":
            return cls.NOT_YET
        value_lower = str(value).lower()
        if "cpu" in value_lower and "gpu" in value_lower:
            return cls.CPU_OR_GPU
        if "cpu" in value_lower:
            return cls.CPU_ONLY
        if "gpu" in value_lower:
            return cls.GPU_ONLY
        return cls.NOT_YET


class PackagingInfo(BaseModel):
    """Packaging information for a software package."""

    software_name: str
    version: Optional[str] = None

    # Spack
    spack_available: bool = False
    spack_timeline: Optional[str] = None
    spack_url: Optional[str] = None

    # Guix
    guix_available: bool = False
    guix_timeline: Optional[str] = None
    guix_url: Optional[str] = None

    # PETSc
    petsc_available: bool = False
    petsc_timeline: Optional[str] = None
    petsc_url: Optional[str] = None

    # Docker
    docker_available: bool = False
    docker_timeline: Optional[str] = None
    docker_url: Optional[str] = None

    # Apptainer
    apptainer_available: bool = False
    apptainer_timeline: Optional[str] = None
    apptainer_url: Optional[str] = None

    notes: Optional[str] = None
    last_updated: Optional[datetime] = None

    @property
    def has_any_package(self) -> bool:
        """Check if any packaging is available."""
        return any([
            self.spack_available,
            self.guix_available,
            self.petsc_available,
            self.docker_available,
            self.apptainer_available,
        ])

    @property
    def community_packages(self) -> list[str]:
        """List of available community package managers."""
        packages = []
        if self.spack_available:
            packages.append("Spack")
        if self.guix_available:
            packages.append("Guix")
        return packages


class WorkPackageInfo(BaseModel):
    """Work package involvement for a software."""

    wp_number: int = Field(ge=1, le=7)
    topics: list[str] = Field(default_factory=list)
    benchmarked: bool = False

    @classmethod
    def from_excel_row(
        cls, row: dict, wp_num: int
    ) -> WorkPackageInfo | None:
        """Create from Excel row data."""
        wp_key = f"WP{wp_num}"
        topics_raw = row.get(wp_key)
        benchmarked_raw = row.get(f"{wp_key} Benchmarked", False)

        if not topics_raw or (isinstance(topics_raw, float) and str(topics_raw) == "nan"):
            return None

        topics = [t.strip() for t in str(topics_raw).split(",") if t.strip()]
        if not topics:
            return None

        return cls(
            wp_number=wp_num,
            topics=topics,
            benchmarked=bool(benchmarked_raw),
        )


class SoftwarePackage(BaseModel):
    """Complete software package metadata."""

    # Identity
    name: str
    description: Optional[str] = None
    partner: Optional[str] = None
    consortium: Optional[str] = None
    emails: list[str] = Field(default_factory=list)
    github_account: Optional[str] = None

    # Repository & License
    repository: Optional[str] = None
    license: Optional[str] = None
    interfaces: Optional[str] = None

    # Documentation & Channels
    docs_url: Optional[str] = None
    channels: list[str] = Field(default_factory=list)
    training_available: bool = False
    training_url: Optional[str] = None

    # Technical
    languages: list[str] = Field(default_factory=list)
    parallelism: list[str] = Field(default_factory=list)
    data_formats: list[str] = Field(default_factory=list)
    resilience: Optional[str] = None
    bottlenecks: list[str] = Field(default_factory=list)

    # DevOps & Quality
    devops: list[str] = Field(default_factory=list)
    api_info: Optional[str] = None
    metadata_info: Optional[str] = None

    # Benchmarking
    benchmark_status: Optional[BenchmarkStatus] = None
    comments: Optional[str] = None

    # Work Packages
    work_packages: list[WorkPackageInfo] = Field(default_factory=list)

    # Packaging (linked separately)
    packaging: Optional[PackagingInfo] = None

    @field_validator("emails", "languages", "parallelism", "data_formats", "devops", "channels", "bottlenecks", mode="before")
    @classmethod
    def split_comma_separated(cls, v):
        """Split comma/newline separated strings into lists."""
        if v is None or (isinstance(v, float) and str(v) == "nan"):
            return []
        if isinstance(v, list):
            return v
        return [item.strip() for item in str(v).replace("\n", ",").split(",") if item.strip()]

    @property
    def slug(self) -> str:
        """Generate URL-safe slug from name."""
        return (
            self.name.lower()
            .replace("/", "_")
            .replace("+", "p")
            .replace(" ", "_")
            .replace("-", "_")
        )

    @property
    def has_public_repository(self) -> bool:
        """Check if a public repository is available."""
        return bool(self.repository and self.repository.strip())

    @property
    def supports_pull_requests(self) -> bool:
        """Check if repository supports PRs (GitHub/GitLab)."""
        if not self.repository:
            return False
        repo_lower = self.repository.lower()
        return "github.com" in repo_lower or "gitlab" in repo_lower

    @property
    def has_floss_license(self) -> bool:
        """Check if license is FLOSS (FSF/OSI conformant)."""
        if not self.license:
            return False
        floss_keywords = ["GPL", "LGPL", "MIT", "BSD", "Apache", "MPL", "CECILL"]
        return any(kw.lower() in self.license.lower() for kw in floss_keywords)

    @property
    def has_ci(self) -> bool:
        """Check if CI is configured."""
        return "Continuous Integration" in self.devops

    @property
    def has_unit_tests(self) -> bool:
        """Check if unit tests exist."""
        return any("unit" in d.lower() for d in self.devops)

    @property
    def has_benchmarking(self) -> bool:
        """Check if benchmarking is configured."""
        return any("benchmark" in d.lower() for d in self.devops)

    @property
    def has_packages(self) -> bool:
        """Check if packages exist."""
        return any("package" in d.lower() for d in self.devops)

    @property
    def is_eligible_for_page(self) -> bool:
        """Check if software meets criteria for page generation."""
        return (
            self.benchmark_status is not None
            and self.benchmark_status != BenchmarkStatus.NOT_YET
            and bool(self.license)
            and bool(self.devops)
        )

    def get_license_list(self) -> list[str]:
        """Parse license string into individual licenses."""
        if not self.license:
            return []
        # Handle formats like "OSS:: LGPL v*, OSS:: GPL v*"
        licenses = []
        for part in self.license.split(","):
            part = part.strip()
            if "::" in part:
                part = part.split("::")[-1].strip()
            if part:
                licenses.append(part)
        return licenses


class SoftwareCollection(BaseModel):
    """Collection of software packages with metadata."""

    packages: list[SoftwarePackage] = Field(default_factory=list)
    source_file: Optional[str] = None
    fetched_at: Optional[datetime] = None

    @property
    def eligible_packages(self) -> list[SoftwarePackage]:
        """Get packages eligible for page generation."""
        return [p for p in self.packages if p.is_eligible_for_page]

    def get_by_name(self, name: str) -> SoftwarePackage | None:
        """Find package by name (case-insensitive)."""
        name_lower = name.lower()
        for pkg in self.packages:
            if pkg.name.lower() == name_lower:
                return pkg
        return None

    def get_by_work_package(self, wp_num: int) -> list[SoftwarePackage]:
        """Get packages involved in a specific work package."""
        return [
            p for p in self.packages
            if any(wp.wp_number == wp_num for wp in p.work_packages)
        ]


class ApplicationStatus(str, Enum):
    """Application development status."""

    PLANNED = "planned"
    IN_DEVELOPMENT = "in-development"
    BENCHMARK_READY = "benchmark-ready"
    COMPLETED = "completed"

    @classmethod
    def from_string(cls, value: str | None) -> ApplicationStatus:
        """Parse status from Excel string."""
        if not value:
            return cls.PLANNED
        value_lower = str(value).lower().strip().replace("_", "-")
        for status in cls:
            if status.value == value_lower:
                return status
        return cls.PLANNED


class ApplicationType(str, Enum):
    """Type of application/benchmark."""

    MINI_APP = "mini-app"
    EXTENDED_MINI_APP = "extended-mini-app"
    PROXY_APP = "proxy-app"
    FULL_APPLICATION = "full-application"
    DEMONSTRATOR = "demonstrator"

    @classmethod
    def from_string(cls, value: str | None) -> ApplicationType:
        """Parse application type from Excel string."""
        if not value:
            return cls.MINI_APP
        value_lower = str(value).lower().strip().replace("_", "-")
        for app_type in cls:
            if app_type.value == value_lower:
                return app_type
        # Fallback matching
        if "extended" in value_lower:
            return cls.EXTENDED_MINI_APP
        if "proxy" in value_lower:
            return cls.PROXY_APP
        if "full" in value_lower:
            return cls.FULL_APPLICATION
        if "demo" in value_lower:
            return cls.DEMONSTRATOR
        return cls.MINI_APP


class Application(BaseModel):
    """Application/benchmark metadata."""

    # Identity
    id: str
    name: str
    partners: list[str] = Field(default_factory=list)
    pc: list[str] = Field(default_factory=list)  # Project Components (PC1, PC2, etc.)
    responsible: list[str] = Field(default_factory=list)
    wp7_engineer: Optional[str] = None

    # Classification
    work_packages: list[str] = Field(default_factory=list)
    application_type: ApplicationType = ApplicationType.MINI_APP
    purpose: Optional[str] = None

    # Methods & Algorithms per WP
    methods_wp1: list[str] = Field(default_factory=list)
    methods_wp2: list[str] = Field(default_factory=list)
    methods_wp3: list[str] = Field(default_factory=list)
    methods_wp4: list[str] = Field(default_factory=list)
    methods_wp5: list[str] = Field(default_factory=list)
    methods_wp6: list[str] = Field(default_factory=list)
    wp7_topics: list[str] = Field(default_factory=list)

    # I/O
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)

    # Benchmarking
    metrics: list[str] = Field(default_factory=list)
    status: ApplicationStatus = ApplicationStatus.PLANNED
    benchmark_scope: list[str] = Field(default_factory=list)

    # Technical
    frameworks: list[str] = Field(default_factory=list)
    parallel_frameworks: list[str] = Field(default_factory=list)

    # Timeline
    spec_due: Optional[datetime] = None
    proto_due: Optional[datetime] = None

    # Links
    repo_url: Optional[str] = None
    tex_url: Optional[str] = None
    notes: Optional[str] = None

    @field_validator(
        "partners", "pc", "responsible", "work_packages",
        "methods_wp1", "methods_wp2", "methods_wp3", "methods_wp4",
        "methods_wp5", "methods_wp6", "wp7_topics",
        "inputs", "outputs", "metrics", "benchmark_scope",
        "frameworks", "parallel_frameworks",
        mode="before"
    )
    @classmethod
    def split_comma_separated(cls, v):
        """Split comma/newline separated strings into lists."""
        if v is None or (isinstance(v, float) and str(v) == "nan"):
            return []
        if isinstance(v, list):
            return v
        return [item.strip() for item in str(v).replace("\n", ",").split(",") if item.strip()]

    @field_serializer("spec_due", "proto_due")
    def serialize_dates(self, value: datetime | None) -> str | None:
        """Serialize datetime to ISO string."""
        if value is None:
            return None
        return value.isoformat()

    @property
    def slug(self) -> str:
        """Generate URL-safe slug from id."""
        return (
            self.id.lower()
            .replace("/", "_")
            .replace("+", "p")
            .replace(" ", "_")
        )

    @property
    def has_repository(self) -> bool:
        """Check if a repository URL is available."""
        return bool(self.repo_url and self.repo_url.strip())

    @property
    def is_benchmark_ready(self) -> bool:
        """Check if application is ready for benchmarking."""
        return self.status in (ApplicationStatus.BENCHMARK_READY, ApplicationStatus.COMPLETED)

    @property
    def is_eligible_for_page(self) -> bool:
        """Check if application meets criteria for page generation."""
        return bool(self.name) and bool(self.purpose)

    @property
    def all_methods(self) -> list[str]:
        """Get all methods across all work packages."""
        methods = []
        for wp_methods in [
            self.methods_wp1, self.methods_wp2, self.methods_wp3,
            self.methods_wp4, self.methods_wp5, self.methods_wp6,
            self.wp7_topics
        ]:
            methods.extend(wp_methods)
        return list(set(methods))


class ApplicationCollection(BaseModel):
    """Collection of applications with metadata."""

    applications: list[Application] = Field(default_factory=list)
    source_file: Optional[str] = None
    fetched_at: Optional[datetime] = None

    @property
    def benchmark_ready(self) -> list[Application]:
        """Get applications ready for benchmarking."""
        return [a for a in self.applications if a.is_benchmark_ready]

    @property
    def eligible_applications(self) -> list[Application]:
        """Get applications eligible for page generation."""
        return [a for a in self.applications if a.is_eligible_for_page]

    def get_by_id(self, app_id: str) -> Application | None:
        """Find application by ID."""
        for app in self.applications:
            if app.id == app_id:
                return app
        return None

    def get_by_framework(self, framework: str) -> list[Application]:
        """Get applications using a specific framework."""
        framework_lower = framework.lower()
        return [
            a for a in self.applications
            if any(framework_lower in f.lower() for f in a.frameworks)
        ]

    def get_by_work_package(self, wp: str) -> list[Application]:
        """Get applications in a specific work package."""
        wp_upper = wp.upper()
        return [
            a for a in self.applications
            if any(wp_upper in w.upper() for w in a.work_packages)
        ]
