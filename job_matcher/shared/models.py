"""
Shared Pydantic models used across all agents and MCP servers.
These are the canonical data structures for the entire pipeline.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid


# ─── Domain Enums ─────────────────────────────────────────────────────────────

class JobSource(str, Enum):
    LINKEDIN  = "linkedin"
    INDEED    = "indeed"
    GLASSDOOR = "glassdoor"
    OTHER     = "other"

class ExperienceLevel(str, Enum):
    ENTRY      = "entry"
    MID        = "mid"
    SENIOR     = "senior"
    EXECUTIVE  = "executive"

class GapSeverity(str, Enum):
    CRITICAL     = "critical"       # Disqualifying
    IMPORTANT    = "important"      # Significant but bridgeable
    NICE_TO_HAVE = "nice_to_have"   # Minor


# ─── User / Profile Models ────────────────────────────────────────────────────

class WorkExperience(BaseModel):
    company:     str
    title:       str
    start_date:  str
    end_date:    Optional[str] = None   # None = current
    description: str
    skills_used: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)

class Education(BaseModel):
    institution:     str
    degree:          str
    field:           str
    graduation_year: Optional[int] = None
    gpa:             Optional[float] = None

class UserProfile(BaseModel):
    """Canonical user profile built from LinkedIn + resume."""
    name:              str
    headline:          Optional[str] = None
    summary:           Optional[str] = None
    location:          Optional[str] = None
    linkedin_url:      Optional[str] = None
    email:             Optional[str] = None
    skills:            list[str] = Field(default_factory=list)
    experience:        list[WorkExperience] = Field(default_factory=list)
    education:         list[Education] = Field(default_factory=list)
    certifications:    list[str] = Field(default_factory=list)
    languages:         list[str] = Field(default_factory=list)
    # Job preferences
    desired_roles:     list[str] = Field(default_factory=list)
    desired_locations: list[str] = Field(default_factory=list)
    salary_range:      Optional[dict[str, int]] = None   # {min, max}
    work_type:         Optional[str] = None              # remote / hybrid / onsite
    total_years_exp:   Optional[float] = None


# ─── Job Models ───────────────────────────────────────────────────────────────

class JobPosting(BaseModel):
    id:               str = Field(default_factory=lambda: str(uuid.uuid4()))
    title:            str
    company:          str
    location:         str
    description:      str
    requirements:     list[str] = Field(default_factory=list)
    salary_range:     Optional[dict[str, int]] = None
    experience_level: Optional[ExperienceLevel] = None
    job_type:         Optional[str] = None          # full-time / part-time / contract
    posted_date:      Optional[str] = None
    apply_url:        str
    source:           JobSource
    skills_required:  list[str] = Field(default_factory=list)
    benefits:         list[str] = Field(default_factory=list)
    company_size:     Optional[str] = None
    industry:         Optional[str] = None
    remote_ok:        bool = False

class JobMatch(BaseModel):
    job:                  JobPosting
    match_score:          float                   # 0-100 composite
    skill_match_pct:      float
    experience_match_pct: float
    culture_match_pct:    float
    match_reasons:        list[str] = Field(default_factory=list)
    concerns:             list[str] = Field(default_factory=list)


# ─── Output Documents ─────────────────────────────────────────────────────────

class TailoredResume(BaseModel):
    job_id:        str
    content:       str                              # Markdown / plain text
    key_changes:   list[str] = Field(default_factory=list)
    keywords_added: list[str] = Field(default_factory=list)
    ats_score:     Optional[float] = None           # Estimated ATS pass-rate

class CoverLetter(BaseModel):
    job_id:     str
    content:    str
    tone:       str = "professional"
    word_count: int = 0

class SkillGap(BaseModel):
    skill:         str
    severity:      GapSeverity
    current_level: str          # "none" | "beginner" | "intermediate"
    target_level:  str
    resources:     list[str] = Field(default_factory=list)   # courses / links

class GapAnalysis(BaseModel):
    job_id:            str
    skill_gaps:        list[SkillGap] = Field(default_factory=list)
    experience_gaps:   list[str] = Field(default_factory=list)
    education_gaps:    list[str] = Field(default_factory=list)
    strengths:         list[str] = Field(default_factory=list)
    overall_readiness: float     # 0-100
    action_plan:       list[str] = Field(default_factory=list)

class InterviewQuestion(BaseModel):
    question:        str
    category:        str          # "technical" | "behavioral" | "situational"
    difficulty:      str          # "easy" | "medium" | "hard"
    suggested_answer: str
    tips:            list[str] = Field(default_factory=list)

class InterviewPrep(BaseModel):
    job_id:              str
    company_insights:    str
    technical_questions: list[InterviewQuestion] = Field(default_factory=list)
    behavioral_questions: list[InterviewQuestion] = Field(default_factory=list)
    questions_to_ask:    list[str] = Field(default_factory=list)   # ask the interviewer
    red_flags:           list[str] = Field(default_factory=list)
    salary_negotiation:  str = ""


# ─── A2A Protocol Models ──────────────────────────────────────────────────────

class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING   = "working"
    COMPLETED = "completed"
    FAILED    = "failed"

class TextPart(BaseModel):
    type: str = "text"
    text: str

class DataPart(BaseModel):
    type: str = "data"
    data: dict[str, Any]

class A2AMessage(BaseModel):
    role:  str                       # "user" | "agent"
    parts: list[dict[str, Any]]

class TaskStatus(BaseModel):
    state:     TaskState
    message:   Optional[str] = None
    timestamp: Optional[str] = None

class Artifact(BaseModel):
    name:     Optional[str] = None
    parts:    list[dict[str, Any]]
    metadata: Optional[dict[str, Any]] = None

class A2ATask(BaseModel):
    id:        str = Field(default_factory=lambda: str(uuid.uuid4()))
    message:   A2AMessage
    status:    TaskStatus = Field(default_factory=lambda: TaskStatus(state=TaskState.SUBMITTED))
    artifacts: list[Artifact] = Field(default_factory=list)
    metadata:  dict[str, Any] = Field(default_factory=dict)

class AgentSkill(BaseModel):
    id:           str
    name:         str
    description:  str
    input_modes:  list[str] = Field(default_factory=lambda: ["text", "data"])
    output_modes: list[str] = Field(default_factory=lambda: ["text", "data"])

class AgentCard(BaseModel):
    """Agent discovery card served at /.well-known/agent.json (A2A spec)."""
    name:                  str
    description:           str
    url:                   str
    version:               str = "1.0.0"
    capabilities:          dict[str, bool] = Field(default_factory=dict)
    skills:                list[AgentSkill] = Field(default_factory=list)
    input_content_types:   list[str] = Field(default_factory=lambda: ["application/json"])
    output_content_types:  list[str] = Field(default_factory=lambda: ["application/json"])


# ─── Orchestrator Pipeline State ──────────────────────────────────────────────

class PipelineRequest(BaseModel):
    """Top-level request from the user."""
    linkedin_url:   Optional[str] = None
    resume_text:    Optional[str] = None      # pre-extracted resume content
    desired_roles:  list[str] = Field(default_factory=list)
    locations:      list[str] = Field(default_factory=list)
    target_job_id:  Optional[str] = None      # if user already chose a job
    # Pipeline toggles
    run_job_search:     bool = True
    run_resume_tailor:  bool = True
    run_cover_letter:   bool = True
    run_gap_analysis:   bool = True
    run_interview_prep: bool = True

class PipelineResult(BaseModel):
    session_id:      str
    profile:         Optional[UserProfile] = None
    job_matches:     list[JobMatch] = Field(default_factory=list)
    tailored_resume: Optional[TailoredResume] = None
    cover_letter:    Optional[CoverLetter] = None
    gap_analysis:    Optional[GapAnalysis] = None
    interview_prep:  Optional[InterviewPrep] = None
    errors:          list[str] = Field(default_factory=list)
