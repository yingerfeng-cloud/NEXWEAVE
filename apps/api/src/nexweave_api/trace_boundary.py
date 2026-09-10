"""Isolate ASGI request context before OpenTelemetry reads the incoming carrier."""

from opentelemetry import context
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestTraceIsolation:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        token = context.attach(context.Context())

        async def traced_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                trace_id = scope.get("state", {}).get("trace_id")
                if trace_id:
                    MutableHeaders(scope=message)["X-Trace-Id"] = trace_id
            await send(message)

        try:
            await self.app(scope, receive, traced_send)
        finally:
            context.detach(token)
