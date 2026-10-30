"""
SubLedger URL Dispatcher (Django-Style Route Registry)

In Django, route mappings live in `urls.py` using `urlpatterns = [path(...)]`.
In FastAPI, route mappings live in APIRouters using `router.include_router(...)`.

This file acts as the top-level URL dispatcher bridging the Django concept 
to FastAPI's `api_router`.
"""

from app.api.v1.api_router import api_router

# Equivalent to Django's root urlpatterns
urlpatterns = api_router

__all__ = ["urlpatterns", "api_router"]
