"""FastAPI application entrypoint."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.chat import router as chat_router
from app.config import get_settings, Settings
from app.core.llm_client import OpenAIClient
from app.core.orchestrator import ConversationOrchestrator
from app.core.security import limiter
from app.core.session_store import SessionStore
from app.core.tool_dispatcher import ToolDispatcher
from app.core.tool_schemas import ToolRegistry
from app.domain_registry import DOMAIN_REGISTRY
from app.errors.handlers import register_exception_handlers
from app.observability.logging import setup_logging
from app.services.geo_service import GeospatialHelper

logger = logging.getLogger(__name__)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize all layers at startup."""
    settings = get_settings()

    # Configure structured logging
    setup_logging(settings)

    logger.info(
        "Starting %s (env=%s, log_level=%s)",
        settings.app_name,
        settings.app_env,
        settings.log_level,
    )

    # Store settings on app.state for route handlers
    app.state.settings = settings

    # Initialize geolocation helper
    geo = GeospatialHelper(settings)
    app.state.geo_service = geo
    logger.info(
        "Geolocation: browser=%s, default=(%.4f, %.4f)",
        settings.enable_browser_coordinates,
        settings.default_lat,
        settings.default_lon,
    )

    # Initialize repositories and services (data-driven from config + descriptor)
    tool_registry = ToolRegistry()
    services_by_name = {}

    for domain_cfg in settings.domains:
        if not domain_cfg.enabled:
            setattr(app.state, f"{domain_cfg.name}_repo", None)
            setattr(app.state, f"{domain_cfg.name}_service", None)
            logger.info("%s domain disabled by config", domain_cfg.name.capitalize())
            continue

        descriptor = DOMAIN_REGISTRY.get(domain_cfg.name)
        if descriptor is None:
            logger.warning(
                "Domain '%s' has no registered descriptor — skipping",
                domain_cfg.name,
            )
            continue

        repo = descriptor.repo_class(domain_cfg)
        service = descriptor.service_class(repo, geo, settings)

        setattr(app.state, f"{domain_cfg.name}_repo", repo)
        setattr(app.state, f"{domain_cfg.name}_service", service)
        logger.info(
            "%s domain enabled (%d records loaded)",
            domain_cfg.name.capitalize(),
            repo.count(),
        )

        services_by_name[domain_cfg.name] = service
        tool_registry.register_domain(
            label=domain_cfg.label,
            search_schema=descriptor.search_schema,
            details_schema=descriptor.details_schema,
        )

    # Initialize session store
    session_store = SessionStore(
        ttl_minutes=settings.session_ttl_minutes,
        max_sessions=settings.max_sessions,
    )
    app.state.session_store = session_store
    logger.info("Session store initialized (TTL=%dm, Max=%d)", settings.session_ttl_minutes, settings.max_sessions)

    # Initialize tool dispatcher with registry and dynamic search tool names
    dispatcher = ToolDispatcher(
        registry=tool_registry,
        settings=settings,
    )

    # Register tool handlers from enabled domains
    for domain_cfg in settings.domains:
        if not domain_cfg.enabled:
            continue
        service = services_by_name.get(domain_cfg.name)
        descriptor = DOMAIN_REGISTRY.get(domain_cfg.name)
        if service is None or descriptor is None:
            continue
        for tool_name, method_name in descriptor.tool_handlers.items():
            dispatcher.register(tool_name, getattr(service, method_name))

    from datetime import datetime
    dispatcher.register("get_current_time", lambda **kwargs: {"time": datetime.now().astimezone().isoformat()})

    def generate_google_maps_route(destinations: list[dict[str, float]], user_lat: float | None = None, user_lon: float | None = None, **kwargs) -> dict:
        if not user_lat or not user_lon:
            return {"url": "Error: User location unknown. Cannot generate origin route."}
        if not destinations:
            return {"url": "Error: No destinations provided."}
            
        base_url = "https://www.google.com/maps/dir/?api=1&travelmode=driving"
        origin = f"&origin={user_lat},{user_lon}"
        
        if len(destinations) == 1:
            dest = destinations[0]
            destination = f"&destination={dest['lat']},{dest['lon']}"
            waypoints = ""
        else:
            final = destinations[-1]
            destination = f"&destination={final['lat']},{final['lon']}"
            wps = [f"{d['lat']},{d['lon']}" for d in destinations[:-1]]
            waypoints = f"&waypoints={'|'.join(wps)}"
            
        return {"url": f"{base_url}{origin}{waypoints}{destination}"}

    dispatcher.register("generate_google_maps_route", generate_google_maps_route)

    app.state.tool_dispatcher = dispatcher

    # Initialize LLM client and orchestrator (only if API key is set)
    if settings.llm_configured:
        llm_client = OpenAIClient(settings)
        orchestrator = ConversationOrchestrator(
            session_store=session_store,
            tool_dispatcher=dispatcher,
            llm_client=llm_client,
            geo_service=geo,
            settings=settings,
            tool_registry=tool_registry,
        )
        app.state.orchestrator = orchestrator
        logger.info(
            "LLM client initialized (model=%s, timeout=%.0fs, max_iterations=%d)",
            settings.openai_model,
            settings.openai_timeout_seconds,
            settings.max_tool_iterations,
        )
    else:
        app.state.orchestrator = None
        logger.warning(
            "OPENAI_API_KEY not set — chat orchestration disabled. "
            "Set it in .env to enable the chat flow."
        )

    logger.info("Startup complete — ready to serve requests")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version="0.5.0",
        lifespan=lifespan,
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers & Rate Limiter
    register_exception_handlers(application)
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Routers
    application.include_router(chat_router)
    @application.get("/health")
    async def health():
        domain_counts = {}
        for domain_cfg in settings.domains:
            repo = getattr(application.state, f"{domain_cfg.name}_repo", None)
            domain_counts[domain_cfg.name] = repo.count() if repo else 0

        session_count = (
            application.state.session_store.count()
            if getattr(application.state, "session_store", None)
            else 0
        )
        llm_ok = getattr(application.state, "orchestrator", None) is not None

        return {
            "status": "ok",
            **domain_counts,
            "active_sessions": session_count,
            "llm_configured": llm_ok,
        }

    # Serve compiled frontend in production, or a simple root response in dev
    if FRONTEND_DIR.is_dir():
        application.mount(
            "/",
            StaticFiles(directory=str(FRONTEND_DIR), html=True),
            name="frontend",
        )
        logger.info("Serving frontend from %s", FRONTEND_DIR)
    else:

        @application.get("/")
        async def root():
            return {
                "service": settings.app_name,
                "stage": 5,
                "hint": "Frontend not built. Run `cd frontend && npm run build` or use the Vite dev server.",
            }

    return application


app = create_app()
