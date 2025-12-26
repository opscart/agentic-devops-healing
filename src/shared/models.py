"""
Data models for the agent
"""

from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class FailureContext:
    """Context about a pipeline failure"""
    pipeline_id: str
    build_id: str
    build_number: str
    pr_id: Optional[str]
    failed_stage: str
    failed_job: str
    failed_task: str
    repo_url: str
    source_branch: str
    project_name: str
    organization_url: str
    timestamp: str


@dataclass
class RCAResult:
    """Result of root cause analysis"""
    category: str
    confidence: float
    explanation: str
    can_autofix: bool
    fix_code: Optional[str] = None
    suggested_fix: Optional[str] = None