import logging
import sys
from ..config import settings


class TelemetryFormatter(logging.Formatter):
    """
    Custom formatter that includes OpenTelemetry trace IDs in logs
    
    This allows correlating logs with traces for easier debugging.
    """
    
    def format(self, record):
        # Try to get trace ID from current OpenTelemetry span
        trace_id = None
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            if span and span.is_recording():
                span_context = span.get_span_context()
                if span_context and span_context.trace_id:
                    # Format trace ID as hex (16 bytes = 32 hex chars)
                    trace_id = format(span_context.trace_id, '032x')[:16]  # Use first 16 chars for readability
        except Exception:
            # If OpenTelemetry is not available or span is not active, continue without trace ID
            pass
        
        # Add trace ID to record if available
        if trace_id:
            record.trace_id = trace_id
            # Modify format to include trace ID if not already present
            if not hasattr(self, '_original_fmt'):
                self._original_fmt = self._style._fmt
            if '%(trace_id)s' not in self._style._fmt:
                self._style._fmt = f"{self._original_fmt} [trace_id=%(trace_id)s]"
        else:
            # Remove trace_id from format if not available
            if hasattr(self, '_original_fmt'):
                self._style._fmt = self._original_fmt
        
        return super().format(record)


def setup_logging():
    """Configure logging for the application"""
    log_level = getattr(settings, "log_level", "INFO").upper()
    
    # Create handler with telemetry formatter
    handler = logging.StreamHandler(sys.stdout)
    formatter = TelemetryFormatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        handlers=[handler]
    )
    
    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")

