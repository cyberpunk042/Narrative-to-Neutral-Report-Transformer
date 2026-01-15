"""
Channel-Aware Structured Logging for NNRT.

Provides semantic logging channels with level-based filtering:
- PIPELINE: pass start/end, timing
- TRANSFORM: individual transformations
- EXTRACT: entity/identifier extraction
- POLICY: rule matching
- RENDER: template/LLM rendering  
- SYSTEM: errors, warnings, status

Log Levels:
- SILENT (0): No logging
- INFO (1): Key milestones only
- VERBOSE (2): Detailed operations
- DEBUG (3): Everything

Configuration via environment:
- NNRT_LOG_LEVEL: Global level (silent/info/verbose/debug)
- NNRT_LOG_FORMAT: Output format (console/json)
- NNRT_LOG_CHANNELS: Comma-separated channel filter (all if not set)
"""

import logging
import os
import sys
from datetime import datetime
from enum import IntEnum, Enum
from typing import Any, Optional, Union
from contextvars import ContextVar

import structlog


# =============================================================================
# Enums
# =============================================================================

class LogLevel(IntEnum):
    """Log verbosity levels."""
    SILENT = 0
    INFO = 1
    VERBOSE = 2
    DEBUG = 3
    
    @classmethod
    def from_string(cls, s: str) -> "LogLevel":
        """Parse log level from string."""
        mapping = {
            "silent": cls.SILENT,
            "info": cls.INFO,
            "verbose": cls.VERBOSE,
            "debug": cls.DEBUG,
            # stdlib compatibility
            "warning": cls.INFO,
            "error": cls.INFO,
        }
        return mapping.get(s.lower(), cls.INFO)


class LogChannel(str, Enum):
    """Semantic log channels."""
    PIPELINE = "PIPELINE"     # Pass orchestration
    TRANSFORM = "TRANSFORM"   # Individual transformations
    EXTRACT = "EXTRACT"       # Entity/identifier extraction
    POLICY = "POLICY"         # Rule matching
    RENDER = "RENDER"         # Template/LLM rendering
    SYSTEM = "SYSTEM"         # Errors, warnings, status
    
    @classmethod
    def all(cls) -> list["LogChannel"]:
        """Return all channels."""
        return list(cls)
    
    @classmethod
    def from_string(cls, s: str) -> Optional["LogChannel"]:
        """Parse channel from string."""
        try:
            return cls(s.upper())
        except ValueError:
            return None


# =============================================================================
# Configuration
# =============================================================================

# Context variable for request-scoped logging
_request_context: ContextVar[dict] = ContextVar("nnrt_log_context", default={})

# Global configuration
_config = {
    "level": LogLevel.INFO,
    "format": "console",
    "channels": set(LogChannel.all()),
    "configured": False,
}


def configure_logging(
    level: Union[LogLevel, str, None] = None,
    format: str = None,
    channels: list[Union[LogChannel, str]] = None,
    force: bool = False,
) -> None:
    """
    Configure the logging system.
    
    Args:
        level: Log level (LogLevel enum or string)
        format: Output format ("console" or "json")
        channels: List of channels to enable (all if None)
        force: Force reconfiguration if already configured
    """
    global _config
    
    if _config["configured"] and not force:
        return
    
    # Parse level from env or argument
    if level is None:
        level_str = os.environ.get("NNRT_LOG_LEVEL", "info")
        level = LogLevel.from_string(level_str)
    elif isinstance(level, str):
        level = LogLevel.from_string(level)
    
    # Parse format from env or argument
    if format is None:
        format = os.environ.get("NNRT_LOG_FORMAT", "console")
    
    # Parse channels from env or argument
    if channels is None:
        channels_str = os.environ.get("NNRT_LOG_CHANNELS", "")
        if channels_str:
            parsed_channels = []
            for ch in channels_str.split(","):
                parsed = LogChannel.from_string(ch.strip())
                if parsed:
                    parsed_channels.append(parsed)
            channels = parsed_channels if parsed_channels else LogChannel.all()
        else:
            channels = LogChannel.all()
    else:
        # Convert strings to enums
        parsed_channels = []
        for ch in channels:
            if isinstance(ch, str):
                parsed = LogChannel.from_string(ch)
                if parsed:
                    parsed_channels.append(parsed)
            else:
                parsed_channels.append(ch)
        channels = parsed_channels
    
    _config["level"] = level
    _config["format"] = format
    _config["channels"] = set(channels)
    
    # Set up standard library logging
    stdlib_level = {
        LogLevel.SILENT: logging.CRITICAL + 10,  # Above critical = nothing
        LogLevel.INFO: logging.INFO,
        LogLevel.VERBOSE: logging.DEBUG,
        LogLevel.DEBUG: logging.DEBUG,
    }.get(level, logging.INFO)
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=stdlib_level,
        force=True,
    )
    
    # Configure structlog processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _add_channel_processor,
    ]
    
    if format == "json":
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
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
    
    _config["configured"] = True


def _add_channel_processor(logger, method_name, event_dict):
    """Add channel info to the event dict if present."""
    # Channel is added by ChannelLogger, just pass through
    return event_dict


# =============================================================================
# Channel Logger
# =============================================================================

class ChannelLogger:
    """
    A logger bound to a specific channel.
    
    Provides level-aware logging methods:
    - info(): Key milestones (level >= INFO)
    - verbose(): Detailed operations (level >= VERBOSE)
    - debug(): Everything (level >= DEBUG)
    - error(): Always logged (unless SILENT)
    - warning(): Always logged (unless SILENT)
    """
    
    def __init__(
        self,
        channel: LogChannel,
        name: str = None,
        pass_name: str = None,
    ):
        self.channel = channel
        self.name = name or f"nnrt.{channel.value.lower()}"
        self.pass_name = pass_name
        self._logger = structlog.get_logger(self.name)
    
    def _should_log(self, msg_level: LogLevel) -> bool:
        """Check if this message should be logged based on config."""
        # Check channel filter
        if self.channel not in _config["channels"]:
            return False
        
        # Check level
        return _config["level"] >= msg_level
    
    def _make_event(self, event: str, **kwargs) -> dict:
        """Build the event dict with channel and pass info."""
        data = {
            "channel": self.channel.value,
            **kwargs,
        }
        if self.pass_name:
            data["pass"] = self.pass_name
        
        # Add request context if available
        ctx = _request_context.get()
        if ctx:
            data.update(ctx)
        
        return data
    
    def info(self, event: str, **kwargs) -> None:
        """Log at INFO level (key milestones)."""
        if not self._should_log(LogLevel.INFO):
            return
        self._logger.info(event, **self._make_event(event, **kwargs))
    
    def verbose(self, event: str, **kwargs) -> None:
        """Log at VERBOSE level (detailed operations)."""
        if not self._should_log(LogLevel.VERBOSE):
            return
        self._logger.debug(event, **self._make_event(event, level="verbose", **kwargs))
    
    def debug(self, event: str, **kwargs) -> None:
        """Log at DEBUG level (everything)."""
        if not self._should_log(LogLevel.DEBUG):
            return
        self._logger.debug(event, **self._make_event(event, level="debug", **kwargs))
    
    def error(self, event: str, **kwargs) -> None:
        """Log an error (always logged unless SILENT)."""
        if _config["level"] == LogLevel.SILENT:
            return
        self._logger.error(event, **self._make_event(event, **kwargs))
    
    def warning(self, event: str, **kwargs) -> None:
        """Log a warning (always logged unless SILENT)."""
        if _config["level"] == LogLevel.SILENT:
            return
        self._logger.warning(event, **self._make_event(event, **kwargs))
    
    def bind(self, **kwargs) -> "ChannelLogger":
        """Create a new logger with additional bound context."""
        new_logger = ChannelLogger(
            channel=self.channel,
            name=self.name,
            pass_name=self.pass_name,
        )
        new_logger._logger = self._logger.bind(**kwargs)
        return new_logger


# =============================================================================
# Logger Factory Functions
# =============================================================================

def get_logger(channel: Union[LogChannel, str] = LogChannel.SYSTEM) -> ChannelLogger:
    """
    Get a channel-specific logger.
    
    Args:
        channel: The log channel (default: SYSTEM)
        
    Returns:
        A ChannelLogger instance
    """
    configure_logging()
    
    if isinstance(channel, str):
        channel = LogChannel.from_string(channel) or LogChannel.SYSTEM
    
    return ChannelLogger(channel=channel)


def get_pass_logger(pass_name: str, channel: LogChannel = None) -> ChannelLogger:
    """
    Get a logger for a specific pipeline pass.
    
    Args:
        pass_name: The pass name (e.g., "p32_extract_entities")
        channel: The log channel (auto-detected if None)
        
    Returns:
        A ChannelLogger bound to the pass
    """
    configure_logging()
    
    # Auto-detect channel from pass name
    if channel is None:
        channel_map = {
            "p00": LogChannel.PIPELINE,
            "p10": LogChannel.PIPELINE,
            "p20": LogChannel.TRANSFORM,
            "p22": LogChannel.TRANSFORM,
            "p25": LogChannel.TRANSFORM,
            "p26": LogChannel.TRANSFORM,
            "p27": LogChannel.TRANSFORM,
            "p28": LogChannel.TRANSFORM,
            "p30": LogChannel.EXTRACT,
            "p32": LogChannel.EXTRACT,
            "p34": LogChannel.EXTRACT,
            "p40": LogChannel.PIPELINE,
            "p50": LogChannel.POLICY,
            "p60": LogChannel.PIPELINE,
            "p70": LogChannel.RENDER,
            "p75": LogChannel.RENDER,
            "p80": LogChannel.PIPELINE,
        }
        prefix = pass_name[:3]
        channel = channel_map.get(prefix, LogChannel.PIPELINE)
    
    return ChannelLogger(
        channel=channel,
        name=f"nnrt.{pass_name}",
        pass_name=pass_name,
    )


# =============================================================================
# Request Context Management
# =============================================================================

def bind_request_context(**kwargs) -> None:
    """Bind context that will be included in all log messages."""
    ctx = _request_context.get().copy()
    ctx.update(kwargs)
    _request_context.set(ctx)


def clear_request_context() -> None:
    """Clear the request context."""
    _request_context.set({})


# =============================================================================
# TransformLogger (Backward Compatibility)
# =============================================================================

class TransformLogger:
    """
    Context-aware logger for transformation pipeline.
    
    Binds request context for all log messages.
    Maintains backward compatibility with existing engine.py usage.
    """
    
    def __init__(self, request_id: str):
        self.request_id = request_id
        self._pipeline_log = get_logger(LogChannel.PIPELINE)
        self._start_time = datetime.now()
        self._pass_times: dict[str, float] = {}
        
        # Bind request ID to context
        bind_request_context(request_id=request_id)
    
    def bind(self, **kwargs: Any) -> "TransformLogger":
        """Bind additional context."""
        bind_request_context(**kwargs)
        return self
    
    def pass_start(self, pass_name: str) -> None:
        """Log the start of a pipeline pass."""
        self._pass_times[pass_name] = datetime.now().timestamp()
        self._pipeline_log.verbose(
            "pass_started",
            pass_name=pass_name,
        )
    
    def pass_end(self, pass_name: str, **metrics: Any) -> None:
        """Log the end of a pipeline pass with timing."""
        start = self._pass_times.get(pass_name, datetime.now().timestamp())
        duration_ms = (datetime.now().timestamp() - start) * 1000
        
        self._pipeline_log.info(
            "pass_completed",
            pass_name=pass_name,
            duration_ms=round(duration_ms, 2),
            **metrics,
        )
    
    def pass_error(self, pass_name: str, error: Exception) -> None:
        """Log a pass error."""
        self._pipeline_log.error(
            "pass_failed",
            pass_name=pass_name,
            error=str(error),
            error_type=type(error).__name__,
        )
    
    def transform_complete(self, status: str, **metrics: Any) -> None:
        """Log transformation completion with summary."""
        total_ms = (datetime.now() - self._start_time).total_seconds() * 1000
        
        self._pipeline_log.info(
            "transform_complete",
            status=status,
            total_duration_ms=round(total_ms, 2),
            **metrics,
        )
        
        # Clear request context
        clear_request_context()
    
    def policy_match(self, rule_id: str, action: str, matched_text: str) -> None:
        """Log a policy rule match."""
        log = get_logger(LogChannel.POLICY)
        log.verbose(
            "policy_matched",
            rule_id=rule_id,
            action=action,
            matched_text=matched_text[:50],
        )
    
    def identifier_found(self, id_type: str, value: str, confidence: float) -> None:
        """Log an extracted identifier."""
        log = get_logger(LogChannel.EXTRACT)
        log.verbose(
            "identifier_extracted",
            id_type=id_type,
            value=value,
            confidence=confidence,
        )


# =============================================================================
# Convenience Functions
# =============================================================================

_default_logger: Optional[ChannelLogger] = None


def log() -> ChannelLogger:
    """Get the default system logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger(LogChannel.SYSTEM)
    return _default_logger


def get_current_config() -> dict:
    """Get the current logging configuration (for testing/debugging)."""
    return {
        "level": _config["level"].name,
        "format": _config["format"],
        "channels": [ch.value for ch in _config["channels"]],
    }
