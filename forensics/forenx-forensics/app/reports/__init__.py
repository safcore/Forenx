"""Forensic report generation package (Phase 8).

Aggregates Phase 2–7 service outputs into derived JSON/PDF reports without
modifying source evidence.
"""

from app.reports.builder import build_forensic_report, validate_report
from app.reports.dispatcher import dispatch_report_output

__all__ = [
    "build_forensic_report",
    "dispatch_report_output",
    "validate_report",
]
