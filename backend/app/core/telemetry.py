"""
OpenTelemetry Setup

Automatically instruments FastAPI, SQLAlchemy, and HTTP clients.
No manual logging needed - everything is tracked automatically.

This provides:
- Automatic request/response timing for all FastAPI routes
- Database query timing (SQLAlchemy)
- HTTP client call tracking (httpx, requests)
- Request correlation via trace IDs
- Service dependency visualization
- Error tracking with full context
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from ..config import settings
import logging

logger = logging.getLogger(__name__)


def setup_telemetry(app):
    """
    Setup OpenTelemetry instrumentation for FastAPI app
    
    This automatically tracks:
    - All FastAPI routes (request/response timing, status codes, methods)
    - SQLAlchemy queries (database timing, query details)
    - HTTP client calls (httpx, requests - URL, method, status)
    - Request correlation (trace IDs propagated across services)
    
    Args:
        app: FastAPI application instance
    """
    # Create resource with service metadata
    resource = Resource.create({
        "service.name": "canon-api",
        "service.version": "1.0.0",
        "service.namespace": "canon",
    })
    
    # Setup tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # Configure exporters based on settings
    exporter_type = getattr(settings, 'telemetry_exporter', 'jaeger').lower()
    jaeger_host = getattr(settings, 'jaeger_agent_host', 'localhost')
    jaeger_port = getattr(settings, 'jaeger_agent_port', 14268)
    
    if exporter_type in ('jaeger', 'both'):
        try:
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter
            # Use HTTP collector endpoint instead of UDP agent to avoid "Message too long" errors
            # The collector endpoint can handle larger payloads
            collector_endpoint = f"http://{jaeger_host}:14268/api/traces"
            jaeger_exporter = JaegerExporter(
                collector_endpoint=collector_endpoint,
            )
            tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            logger.info(f"Jaeger exporter configured (HTTP collector): {collector_endpoint}")
        except ImportError:
            logger.warning("opentelemetry-exporter-jaeger not installed, skipping Jaeger exporter")
        except Exception as e:
            logger.warning(f"Failed to setup Jaeger exporter: {e}")
    
    if exporter_type in ('console', 'both'):
        console_exporter = ConsoleSpanExporter()
        tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("Console exporter enabled")
    
    # Automatically instrument FastAPI
    # This tracks all routes, request/response timing, status codes
    FastAPIInstrumentor.instrument_app(app)
    
    # Automatically instrument SQLAlchemy
    # This tracks all database queries and their timing
    SQLAlchemyInstrumentor().instrument()
    
    # Automatically instrument HTTP clients (httpx, requests)
    # This tracks all external HTTP calls (LLM APIs, Tavily, etc.)
    HTTPXClientInstrumentor().instrument()
    
    logger.info("OpenTelemetry instrumentation enabled - all requests, DB queries, and HTTP calls are automatically tracked")
    return tracer_provider


def get_tracer(name: str):
    """
    Get a tracer for custom spans (optional)
    
    Use this if you want to add custom instrumentation for specific operations.
    For example, tracking LLM API calls with custom attributes.
    
    Args:
        name: Name of the tracer (usually __name__)
    
    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)

