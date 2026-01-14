"""
Structured Logging Configuration for NNRT.

Uses structlog for production-quality logging with:
- Structured JSON output (for production)
- Pretty console output (for development)
- Context binding for traceability
- Performance timing
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any

import structlog

# Environment configuration
LOG_LEVEL = os.environ.get("NNRT_LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.environ.get("NNRT_LOG_FORMAT", "console")  # "console" or "json"

# Track if logging has been configured
_configured = False


def configure_logging(
    level: str = None,
    format: str = None,
    force: bool = False,
) -> None:
    """
    Configure structured logging for NNRT.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format: Output format ("console" or "json")
        force: Force reconfiguration if already configured
    """
    global _configured
    
    if _configured and not force:
        return
    
    level = level or LOG_LEVEL
    format = format or LOG_FORMAT
    
    # Set up standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level),
    )
    
    # Configure structlog processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    
    if format == "json":
        # JSON format for production
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console format for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    _configured = True


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger.
    
    Args:
        name: Logger name (defaults to "nnrt")
        
    Returns:
        Configured structlog logger
    """
    configure_logging()
    return structlog.get_logger(name or "nnrt")


class TransformLogger:
    """
    Context-aware logger for transformation pipeline.
    
    Binds request context for all log messages.
    """
    
    def __init__(self, request_id: str):
        self.request_id = request_id
        self._logger = get_logger("nnrt.transform")
        self._start_time = datetime.now()
        self._pass_times: dict[str, float] = {}
    
    def bind(self, **kwargs: Any) -> "TransformLogger":
        """Bind additional context."""
        self._logger = self._logger.bind(**kwargs)
        return self
    
    def pass_start(self, pass_name: str) -> None:
        """Log the start of a pipeline pass."""
        self._pass_times[pass_name] = datetime.now().timestamp()
        self._logger.debug(
            "pass_started",
            request_id=self.request_id,
            pass_name=pass_name,
        )
    
    def pass_end(self, pass_name: str, **metrics: Any) -> None:
        """Log the end of a pipeline pass with timing."""
        start = self._pass_times.get(pass_name, datetime.now().timestamp())
        duration_ms = (datetime.now().timestamp() - start) * 1000
        
        self._logger.info(
            "pass_completed",
            request_id=self.request_id,
            pass_name=pass_name,
            duration_ms=round(duration_ms, 2),
            **metrics,
        )
    
    def pass_error(self, pass_name: str, error: Exception) -> None:
        """Log a pass error."""
        self._logger.error(
            "pass_failed",
            request_id=self.request_id,
            pass_name=pass_name,
            error=str(error),
            error_type=type(error).__name__,
        )
    
    def transform_complete(self, status: str, **metrics: Any) -> None:
        """Log transformation completion with summary."""
        total_ms = (datetime.now() - self._start_time).total_seconds() * 1000
        
        self._logger.info(
            "transform_complete",
            request_id=self.request_id,
            status=status,
            total_duration_ms=round(total_ms, 2),
            **metrics,
        )
    
    def policy_match(self, rule_id: str, action: str, matched_text: str) -> None:
        """Log a policy rule match."""
        self._logger.debug(
            "policy_matched",
            request_id=self.request_id,
            rule_id=rule_id,
            action=action,
            matched_text=matched_text[:50],
        )
    
    def identifier_found(self, id_type: str, value: str, confidence: float) -> None:
        """Log an extracted identifier."""
        self._logger.debug(
            "identifier_extracted",
            request_id=self.request_id,
            id_type=id_type,
            value=value,
            confidence=confidence,
        )


# Default logger instance
_default_logger = None


def log() -> structlog.stdlib.BoundLogger:
    """Get the default logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger()
    return _default_logger
