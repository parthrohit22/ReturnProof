"""Root URL configuration.

`/api/v1/` is the entire application surface the Operator Console talks to.
`/admin/` is for developer inspection of persisted runs, not part of the
product. Everything else falls back to the built frontend's `index.html`
when `web/dist` exists (a local production-style preview, see README), or
404s during normal development, where Vite serves the frontend itself on
its own port and proxies `/api` requests here.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponseNotFound
from django.urls import path, re_path
from django.views.static import serve
from reconciliation.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls),
]

_dist_assets = settings.WEB_DIST_DIR / "assets"
if _dist_assets.exists():
    urlpatterns.append(
        re_path(r"^assets/(?P<path>.*)$", serve, {"document_root": _dist_assets})
    )

_dist_index = settings.WEB_DIST_DIR / "index.html"
if _dist_index.exists():

    def spa_index(request, *args, **kwargs):
        return serve(request, path="index.html", document_root=settings.WEB_DIST_DIR)

    urlpatterns.append(re_path(r"^(?!api/|admin/|assets/).*$", spa_index))
else:

    def spa_not_built(request, *args, **kwargs):
        return HttpResponseNotFound(
            "The Operator Console frontend has not been built. Run `npm run build` "
            "in web/, or run the frontend separately with `npm run dev` during "
            "development (see README)."
        )

    urlpatterns.append(re_path(r"^(?!api/|admin/).*$", spa_not_built))
