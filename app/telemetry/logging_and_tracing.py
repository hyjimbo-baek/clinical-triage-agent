"""Observability, OpenTelemetry Distributed Tracing, and Structured JSON Logging.

Provides:
- Structured JSON logging capturing Intent vs Outcome.
- OpenTelemetry Distributed Tracing with Cloud Trace span creation.
- Audit trail for high-stakes clinical interventions.
"""

import json
import logging
import sys
import time
from typing import Any, Dict, Optional

# Setup standard structured logger
logger = logging.getLogger("clinical_triage_agent")
logger.setLevel(logging.INFO)

# JSON Formatter for structured logs
class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as rich structured JSON objects."""
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra_fields"):
            log_obj.update(record.extra_fields)
        return json.dumps(log_obj)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(StructuredJsonFormatter())
if not logger.handlers:
    logger.addHandler(handler)


def log_intent(agent_name: str, action: str, intent_payload: Dict[str, Any], session_id: Optional[str] = None):
    """Records the agent's intended action and reasoning BEFORE execution (Intent Capture)."""
    record = logging.LogRecord(
        name="clinical_triage_agent.intent",
        level=logging.INFO,
        pathname=__file__,
        lineno=45,
        msg=f"Intent: Agent '{agent_name}' intends to execute '{action}'",
        args=(),
        exc_info=None,
    )
    record.extra_fields = {
        "event_type": "AGENT_INTENT",
        "agent": agent_name,
        "action": action,
        "payload": intent_payload,
        "session_id": session_id or "default_session",
    }
    logger.handle(record)


def log_outcome(agent_name: str, action: str, outcome_payload: Dict[str, Any], status: str = "success", session_id: Optional[str] = None):
    """Records the actual outcome and return value AFTER tool/action execution (Outcome Capture)."""
    record = logging.LogRecord(
        name="clinical_triage_agent.outcome",
        level=logging.INFO,
        pathname=__file__,
        lineno=65,
        msg=f"Outcome: Agent '{agent_name}' completed '{action}' with status '{status}'",
        args=(),
        exc_info=None,
    )
    record.extra_fields = {
        "event_type": "AGENT_OUTCOME",
        "agent": agent_name,
        "action": action,
        "status": status,
        "payload": outcome_payload,
        "session_id": session_id or "default_session",
    }
    logger.handle(record)


# OpenTelemetry Tracing Setup
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    provider = TracerProvider()
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("clinical_triage_agent", "1.0.0")
except Exception:
    tracer = None


def trace_span(span_name: str):
    """Context manager or helper for distributed tracing span creation."""
    if tracer:
        return tracer.start_as_current_span(span_name)
    class DummySpan:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def set_attribute(self, *args): pass
    return DummySpan()
