"""OpenTelemetry trace, metric and log initialization."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sqlalchemy.ext.asyncio import AsyncEngine

from nexweave_api.settings import Settings

_configured = False


def configure_telemetry(application: FastAPI, engine: AsyncEngine, settings: Settings) -> None:
    global _configured
    resource = Resource.create(
        {"service.name": settings.otel_service_name, "service.version": settings.build_version}
    )
    if not _configured:
        tracer_provider = TracerProvider(resource=resource)
        meter_readers = []
        logger_provider = LoggerProvider(resource=resource)
        if settings.otel_exporter_otlp_endpoint:
            endpoint = settings.otel_exporter_otlp_endpoint.rstrip("/")
            tracer_provider.add_span_processor(
                BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
            )
            meter_readers.append(
                PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"))
            )
            logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{endpoint}/v1/logs"))
            )
        trace.set_tracer_provider(tracer_provider)
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=meter_readers))
        logging.getLogger("nexweave").addHandler(
            LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
        )
        LoggingInstrumentor().instrument(
            tracer_provider=tracer_provider,
            inject_trace_context=True,
        )
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
        _configured = True
    FastAPIInstrumentor.instrument_app(application, excluded_urls="/api/v1/health/live")
