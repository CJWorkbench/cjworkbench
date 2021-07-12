from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.cache import patch_response_headers


def icon_path(basename: str) -> str:
    return settings.STATIC_URL + "images/app-icons/" + basename


async def manifest(request: HttpRequest) -> HttpResponse:
    response = JsonResponse(
        {
            "name": "Workbench",
            "short_name": "Workbench",
            "description": "Find and share insights in tables of data",
            "start_url": "/",
            "icons": [
                {
                    "src": icon_path("android-chrome-192x192.png"),
                    "sizes": "192x192",
                    "type": "image/png",
                },
                {
                    "src": icon_path("android-chrome-512x512.png"),
                    "sizes": "512x512",
                    "type": "image/png",
                },
            ],
            "theme_color": "white",
            "background_color": "white",
        }
    )
    patch_response_headers(response, cache_timeout=600)
    return response
