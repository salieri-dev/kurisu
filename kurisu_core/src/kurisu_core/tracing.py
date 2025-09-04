from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_tracing(service_name: str):
    """Configures and registers a global tracer provider."""

    if getattr(setup_tracing, "has_run", False):
        return

    resource = Resource(attributes={SERVICE_NAME: service_name})

    otlp_exporter = OTLPSpanExporter()

    span_processor = BatchSpanProcessor(otlp_exporter)

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(span_processor)

    trace.set_tracer_provider(provider)
    setup_tracing.has_run = True


def get_tracer(module_name: str):
    """Gets a tracer instance for a specific module."""
    return trace.get_tracer(module_name)
