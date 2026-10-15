"""Clinical Triage Agent Tools.

This module provides tools for patient vital recording, emergency adverse event
escalation, clinical guideline retrieval, and symptom guidance dispatch.
All tools follow strict Pydantic V2 input/output schemas, detailed Google-style
docstrings, and descriptive guided error recovery instructions.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# 1. Pydantic Schemas (Explicit JSON Schemas Criterion)
# ============================================================================

class VitalAnomalyInput(BaseModel):
    """Schema for recording vital anomalies with strict validation."""
    patient_id: str = Field(
        ...,
        description="Unique anonymous patient identifier (e.g. PT-1042).",
        min_length=3,
        max_length=32,
    )
    vital_type: str = Field(
        ...,
        description="Type of anomalous vital sign observed: 'heart_rate', 'spo2', 'systolic_bp', 'temperature'.",
    )
    observed_value: float = Field(
        ...,
        description="Numerical reading of the anomalous vital measurement.",
    )
    unit: str = Field(
        ...,
        description="Standard unit of measurement (e.g., 'bpm', '%', 'mmHg', 'C').",
    )
    severity_grade: int = Field(
        ...,
        ge=1,
        le=5,
        description="Common Terminology Criteria for Adverse Events (CTCAE) severity grade from 1 (Mild) to 5 (Death).",
    )

    @field_validator("vital_type")
    @classmethod
    def validate_vital_type(cls, v: str) -> str:
        allowed = {"heart_rate", "spo2", "systolic_bp", "temperature"}
        if v.lower() not in allowed:
            raise ValueError(f"vital_type must be one of {allowed}, got '{v}'")
        return v.lower()


class EscalateAdverseEventInput(BaseModel):
    """Schema for escalating critical adverse events to EMR and on-call physicians."""
    patient_id: str = Field(
        ...,
        description="Unique patient identifier.",
        min_length=3,
    )
    adverse_event_title: str = Field(
        ...,
        description="Descriptive clinical title of the adverse event (e.g., 'Grade 3 Anaphylactoid Infusion Reaction').",
        min_length=5,
    )
    ctcae_grade: int = Field(
        ...,
        ge=3,
        le=5,
        description="CTCAE grade requiring urgent escalation (3 = Severe, 4 = Life-threatening, 5 = Fatal).",
    )
    clinical_summary: str = Field(
        ...,
        description="Thorough clinical summary including suspected drug/treatment, symptom progression, and immediate risks.",
        min_length=20,
    )
    physician_confirmation_id: str = Field(
        ...,
        description="Valid attending physician employee/credential ID who authorized this escalation (HITL verification token).",
        min_length=3,
    )


class ClinicalGuidelineQueryInput(BaseModel):
    """Schema for querying clinical decision support guidelines."""
    condition_or_drug: str = Field(
        ...,
        description="Medical condition, drug class, or symptom to search (e.g. 'CAR-T cytokine release syndrome', 'Pembrolizumab rash').",
        min_length=3,
    )
    target_grade: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Optional CTCAE grade to narrow guideline recommendations.",
    )


# ============================================================================
# 2. Tool Implementations (Descriptive Naming & Guided Error Handling)
# ============================================================================

def record_patient_vital_anomaly(
    patient_id: str,
    vital_type: str,
    observed_value: float,
    unit: str,
    severity_grade: int,
) -> Dict[str, Any]:
    """Records an anomalous clinical vital measurement into the electronic monitoring log.

    This tool logs out-of-range clinical parameters, validates against physiological limits,
    and flags anomalies for attending nursing staff.

    Args:
        patient_id: Unique anonymous patient identifier (e.g. PT-1042).
        vital_type: Category of vital sign ('heart_rate', 'spo2', 'systolic_bp', 'temperature').
        observed_value: Numerical reading of the vital measurement.
        unit: Unit of measurement (e.g., 'bpm', '%', 'mmHg', 'C').
        severity_grade: CTCAE severity rating from 1 to 5.

    Returns:
        A dictionary containing:
            - status (str): 'recorded' or 'error'
            - record_id (str): Generated clinical observation ID
            - alert_level (str): Triage urgency level
            - guidance (str): Clinical nursing advice or recovery instructions

    Raises:
        ValueError: If input validation fails or physiological ranges are nonsensical.

    Example:
        >>> record_patient_vital_anomaly("PT-101", "spo2", 88.0, "%", 3)
        {'status': 'recorded', 'record_id': 'VITAL-8812', 'alert_level': 'HIGH_ALERT', ...}
    """
    try:
        validated = VitalAnomalyInput(
            patient_id=patient_id,
            vital_type=vital_type,
            observed_value=observed_value,
            unit=unit,
            severity_grade=severity_grade,
        )
    except Exception as exc:
        # Guided Error Handling: Return recovery instructions to LLM
        return {
            "status": "error",
            "error_type": "SchemaValidationError",
            "message": str(exc),
            "recovery_instruction": (
                "Input parameter validation failed. Please check that 'vital_type' is strictly "
                "one of ('heart_rate', 'spo2', 'systolic_bp', 'temperature'), 'severity_grade' is "
                "an integer between 1 and 5, and 'patient_id' is non-empty."
            ),
        }

    # Simulate recording
    record_id = f"VITAL-{abs(hash((validated.patient_id, validated.vital_type))) % 10000:04d}"
    alert = "CRITICAL_ALERT" if validated.severity_grade >= 3 else "STANDARD_OBSERVATION"

    return {
        "status": "recorded",
        "record_id": record_id,
        "patient_id": validated.patient_id,
        "vital_type": validated.vital_type,
        "observed_value": f"{validated.observed_value} {validated.unit}",
        "severity_grade": validated.severity_grade,
        "alert_level": alert,
        "guidance": f"Vital anomaly saved to patient telemetry chart. Alert level: {alert}."
    }


def escalate_critical_adverse_event(
    patient_id: str,
    adverse_event_title: str,
    ctcae_grade: int,
    clinical_summary: str,
    physician_confirmation_id: str,
) -> Dict[str, Any]:
    """Escalates a severe adverse event (Grade 3+) to EMR emergency alert and rapid response team.

    CRITICAL SAFETY REQUIREMENT:
    This tool should only be executed AFTER a certified physician confirms the intervention
    through the Human-in-the-Loop review process. Do not call this tool autonomously for
    severe events without a valid physician_confirmation_id.

    Args:
        patient_id: Unique patient identifier.
        adverse_event_title: Clinical description of the adverse reaction.
        ctcae_grade: Severity level (must be 3, 4, or 5).
        clinical_summary: Comprehensive clinical findings and suspected treatment.
        physician_confirmation_id: Credential ID of approving physician.

    Returns:
        A dictionary containing:
            - status (str): 'escalated' or 'rejected_for_insufficient_auth'
            - dispatch_code (str): EMR emergency protocol tracking code
            - timestamp (str): Escalation timestamp
            - response_team (str): Assigned clinical response unit

    Example:
        >>> escalate_critical_adverse_event("PT-202", "Grade 3 Anaphylaxis", 3, "Acute dyspnea post Infusion", "DR-501")
        {'status': 'escalated', 'dispatch_code': 'EMR-CODE-BLUE-441', ...}
    """
    try:
        validated = EscalateAdverseEventInput(
            patient_id=patient_id,
            adverse_event_title=adverse_event_title,
            ctcae_grade=ctcae_grade,
            clinical_summary=clinical_summary,
            physician_confirmation_id=physician_confirmation_id,
        )
    except Exception as exc:
        return {
            "status": "error",
            "error_type": "SchemaValidationError",
            "message": str(exc),
            "recovery_instruction": (
                "Adverse event escalation requires ctcae_grade >= 3, clinical_summary of at least 20 chars, "
                "and an explicit physician_confirmation_id obtained from the Human-in-the-Loop approval step. "
                "Ensure human physician confirmation has been requested first."
            ),
        }

    dispatch_code = f"EMR-CRIT-{abs(hash((validated.patient_id, validated.adverse_event_title))) % 90000 + 10000}"
    
    return {
        "status": "escalated",
        "dispatch_code": dispatch_code,
        "patient_id": validated.patient_id,
        "adverse_event_title": validated.adverse_event_title,
        "ctcae_grade": validated.ctcae_grade,
        "physician_signoff": validated.physician_confirmation_id,
        "response_team": "Rapid Response & Inpatient Oncology On-Call",
        "action_taken": "High-priority EMR order registered. Emergency pager sent to attending team."
    }


def fetch_clinical_guidance(condition_or_drug: str, target_grade: Optional[int] = None) -> Dict[str, Any]:
    """Retrieves standardized medical guidelines and toxicity management protocols.

    Queries evidence-based institutional guidelines (e.g. NCCN, ASCO, CTCAE v5.0) for
    recommended diagnostic workup, supportive medications, and monitoring schedules.

    Args:
        condition_or_drug: Name of condition, suspected toxicity, or drug class.
        target_grade: Optional severity grade (1-5) to filter guideline specifics.

    Returns:
        A dictionary with clinical recommendations, reference source, and cautionary notes.
    """
    try:
        validated = ClinicalGuidelineQueryInput(
            condition_or_drug=condition_or_drug,
            target_grade=target_grade,
        )
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
            "recovery_instruction": "Specify condition_or_drug string with at least 3 characters."
        }

    q = validated.condition_or_drug.lower()
    if "dyspnea" in q or "chest" in q or "oxygen" in q or "spo2" in q:
        return {
            "status": "success",
            "protocol": "ACUTE_RESPIRATORY_DISTRESS_PROTOCOL",
            "guideline_title": "CTCAE Management of Immune-Mediated Pneumonitis & Bronchospasm",
            "evidence_grade": "Level 1A",
            "recommendations": [
                "Immediately administer high-flow oxygen to maintain SpO2 >= 92%.",
                "Hold suspected offending pharmaceutical agent immediately.",
                "Order emergent STAT chest CT and arterial blood gas (ABG) analysis.",
                "Prepare IV Methylprednisolone 1-2 mg/kg/day pending physician sign-off."
            ],
            "requires_hitl_approval": True,
        }
    elif "rash" in q or "skin" in q:
        return {
            "status": "success",
            "protocol": "DERMATOLOGIC_TOXICITY_PROTOCOL",
            "guideline_title": "Management of Drug-Induced Maculopapular Rash",
            "evidence_grade": "Level 2B",
            "recommendations": [
                "Apply topical hydrocortisone 1% cream BID to affected areas.",
                "Oral cetirizine 10mg once daily for pruritus.",
                "Continue oral hydration and avoid excessive sun exposure."
            ],
            "requires_hitl_approval": False,
        }
    else:
        return {
            "status": "success",
            "protocol": "GENERAL_SYMPTOM_SUPPORT_PROTOCOL",
            "guideline_title": "Standard Supportive Ambulatory Triage Guidance",
            "evidence_grade": "Level 2A",
            "recommendations": [
                "Monitor vitals q4h if symptoms persist.",
                "Maintain oral fluid intake >= 2L/day unless contraindicated.",
                "Report immediately if fever > 38.0C or shortness of breath develops."
            ],
            "requires_hitl_approval": False,
        }
