from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.openapi.utils import get_openapi
import logging
import os
import json

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import route modules
from .routes import root, attendance, calendar, csv

# Application version
APP_VERSION = "1.0.0"

# Create FastAPI app (disable default documentation)
app = FastAPI(
    title="Sokora API",
    docs_url=None,  # Disable default /docs
    redoc_url=None,  # Disable default /redoc
    version=APP_VERSION,
)

# Serve static files from /static
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Include routers from each module
app.include_router(root.router)
app.include_router(attendance.page_router)  # Router for page display
app.include_router(attendance.router)  # Router for API
app.include_router(calendar.router)
app.include_router(csv.router)


# API tag definitions
API_TAGS = [
    {
        "name": "Attendance",
        "description": "Endpoints for managing user attendance data",
    },
    {
        "name": "Calendar",
        "description": "Endpoints for calendar display and daily detail information",
    },
    {
        "name": "CSV Data",
        "description": "Endpoints for importing and exporting CSV data",
    },
    {
        "name": "Page Display",
        "description": "Endpoints for displaying application UI pages",
    },
]


# Custom OpenAPI schema definition
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Sokora API",
        version=APP_VERSION,
        description="Sokora API Documentation",
        routes=app.routes,
    )

    # Explicitly set OpenAPI version
    openapi_schema["openapi"] = "3.0.2"

    # Add tag order and custom descriptions
    openapi_schema["tags"] = API_TAGS

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Provide custom Swagger UI page
@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui_html(request: Request):
    """Provide Swagger UI at a custom path"""
    swagger_js = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js"
    swagger_css = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css"
    openapi_url = app.openapi_url or "/openapi.json"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{app.title} - API Documentation</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" type="text/css" href="{swagger_css}">
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="{swagger_js}"></script>
        <script>
            const ui = SwaggerUIBundle({{
                url: '{openapi_url}',
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout",
                deepLinking: true
            }})
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_endpoint():
    """Provide OpenAPI JSON schema"""
    return app.openapi()
