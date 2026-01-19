import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
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
    
    # Create formatter
    formatter = TelemetryFormatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    handlers = []
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # File handler - add if log file path is configured
    log_file = getattr(settings, "log_file", None)
    if log_file:
        # Create logs directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use RotatingFileHandler to prevent log files from growing too large
        # maxBytes: 10MB, backupCount: 5 (keeps 5 backup files)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        handlers=handlers
    )
    
    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")
    if log_file:
        logger.info(f"Logs will be saved to: {log_file}")

