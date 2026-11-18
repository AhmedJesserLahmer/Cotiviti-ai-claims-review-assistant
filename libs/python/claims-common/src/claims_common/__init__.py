"""Shared library for the Claims Review services.

Every service under services/ installs this package (see each Dockerfile), so
cross-cutting concerns are implemented once: structured logging, settings, the
FastAPI app factory, health probes, resilience primitives and the service-to-service
HTTP client.
"""

__version__ = "0.2.0"
