"""Application settings loaded from environment variables."""

import logging
from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings

_DEFAULT_SYSTEM_PROMPT = (
    "## Role\n"
    "You are a knowledgeable and friendly local guide for Marienplatz, Munich.\n"
    "Your sole purpose is helping users find places in the area.\n"
    "You do not assist with any other topic.\n\n"
    "## Data Policy\n"
    "NEVER invent, estimate, or assume any factual field — distances, ratings,\n"
    "prices, opening hours, or payment methods. If the information is not returned\n"
    "by a tool, say so honestly. You must call the appropriate tool before\n"
    "answering any question that requires location data.\n\n"
    "## Tool Usage\n"
    "- Always call the appropriate search tool based on the user's request before\n"
    "  listing places. Do not answer from memory.\n"
    "- Call the explicit details tool only when the user asks for more information\n"
    "  about a specific place already listed.\n"
    "- When the user asks about a specific domain (e.g. sushi), call ONLY tools\n"
    "  for that domain. Never mix results from different domains unless the user\n"
    "  explicitly asks to compare or list both.\n"
    "- By default, tools sort by distance from the USER's location. If the user\n"
    "  asks for places near ANOTHER specific place (e.g. 'nearest to Stachus'),\n"
    "  you MUST pass the coordinates of THAT place into reference_lat and reference_lon.\n"
    "  DO NOT guess or provide reference_lat/lon unless the user EXPLICITLY names a landmark.\n"
    "  NEVER pass a distance to another POI into max_distance_meters.\n"
    "- If the user's request cannot be answered using the available tools AND\n"
    "  is not a clarifying question about a previous response, reply with a polite\n"
    "  refusal and ask if they would like to search for one of the supported domains.\n"
    "- Clarifying questions about previously shown results (e.g. \"what does €€\n"
    "  mean?\", \"how is distance calculated?\", \"are you open on Sundays?\") must\n"
    "  be answered from your knowledge — no tool call needed.\n\n"
    "## Output Format\n"
    "- List results as a numbered list. Each line: Name — key fact — key fact.\n"
    "- After every list, offer: \"Would you like details on any of these?\"\n"
    "- For follow-ups like \"tell me more about the second one\", use the ID from\n"
    "  the prior tool result — never ask the user to repeat information already\n"
    "  provided.\n"
    "- Keep responses concise. Avoid filler phrases like \"Certainly!\" or\n"
    "  \"Great question!\".\n\n"
    "## Tone\n"
    "Warm, local, direct. Imagine a knowledgeable Münchner recommending places\n"
    "to a friend.\n\n"
    "## Data Field Glossary\n"
    "- Price range: € = budget (under €15/person), €€ = mid-range (€15–30/person),\n"
    "  €€€ = upscale (over €30/person).\n"
    "- Rating: user review score on a 1–5 scale.\n"
    "- Distance: straight-line distance in metres from the user's REAL physical\n"
    "  location (which may be several kilometres away from Marienplatz). Do NOT\n"
    "  alter, shorten, or hallucinate these distances. Present them exactly as\n"
    "  they appear in the tool results, even if they seem strangely large.\n"
    "- Payment methods: cash, card (chip/PIN), contactless (tap), app (parking app).\n\n"
    "## Google Maps Routing\n"
    "If the user asks for a route, directions, or navigation to one or more places, ALWAYS call the `generate_google_maps_route` tool to generate the URL.\n"
    "Once the tool provides the JSON containing the `url`, YOU MUST ONLY reply to the user with a short message containing the clickable markdown link, formatted exactly like this: [Click here for Google Maps route](<url>).\n"
    "NEVER call the tool twice in a row for the same request.\n"
)


class DomainConfig(BaseModel):
    """Configuration for a single place-type domain.

    Each domain (sushi, parking, etc.) is described by one of these.
    To add a new domain, simply append another ``DomainConfig`` to the
    ``domains`` list in ``Settings`` — no code changes needed in config.
    """

    name: str
    """Short identifier used for state attributes and logging."""

    label: str
    """Human-readable label for the system prompt (e.g. 'sushi restaurants')."""

    dataset_path: str
    """Path (relative to project root) to the JSON dataset."""

    enabled: bool = True
    """Whether this domain is active. Set to False to disable at runtime."""

    strict: bool = False
    """If True, invalid records cause a startup failure instead of being skipped."""

    required_fields: set[str] = set()
    """Set of field names that must be present in every JSON record."""

    payment_methods: set[str] = set()
    """Set of allowed payment method values for this domain."""


# Pre-built domain configs for the two built-in domains
SUSHI_DOMAIN = DomainConfig(
    name="sushi",
    label="sushi restaurants",
    dataset_path="app/data/sushi.json",
    required_fields={"id", "name", "address", "lat", "lon", "rating", "price_range"},
    payment_methods={"cash", "card", "contactless", "any"},
)

PARKING_DOMAIN = DomainConfig(
    name="parking",
    label="parking garages",
    dataset_path="app/data/parking.json",
    required_fields={"id", "name", "address", "lat", "lon", "price_per_hour"},
    payment_methods={"cash", "card", "contactless", "app", "any"},
)


class Settings(BaseSettings):
    """Typed runtime configuration.

    Values are read from environment variables, with ``.env`` file support.
    All operational values that may change between environments are
    configurable here with sensible defaults.
    """

    # Application
    app_name: str = "Marienplatz POI Chatbot"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # OpenAI / LLM
    openai_api_key: str
    openai_model: str = "gpt-5-mini-2025-08-07"
    openai_timeout_seconds: float = 60.0
    openai_temperature: float = 1.0
    openai_max_tokens: int = 8192
    openai_reasoning_effort: str = "low"

    # Orchestration
    max_tool_iterations: int = 3
    request_timeout_seconds: float = 45.0
    system_prompt: str = _DEFAULT_SYSTEM_PROMPT

    allowed_tool_args: dict[str, set[str]] = {
        "search_sushi_restaurants": {
            "query", "min_rating", "max_distance_meters", "payment_method",
            "limit", "sort_by", "reference_lat", "reference_lon"
        },
        "get_sushi_restaurant_details": {"restaurant_id"},
        "search_parking_garages": {
            "payment_method", "max_distance_meters", "max_price_per_hour",
            "limit", "reference_lat", "reference_lon"
        },
        "get_parking_garage_details": {"garage_id"},
        "clarify_intent": {"question"},
        "get_current_time": set(),
        "generate_google_maps_route": {"destinations"},
    }

    # Sessions
    session_ttl_minutes: int = 30

    # Request validation
    max_user_message_chars: int = 2000

    # CORS
    cors_origins: str = "http://localhost:5173"

    # Domains (data-driven)
    # Each domain is a DomainConfig describing a place type.
    # To add a new domain, append to this list — no hardcoded fields.
    domains: list[DomainConfig] = [SUSHI_DOMAIN, PARKING_DOMAIN]

    # Search defaults
    default_limit: int = 5
    max_limit: int = 20
    default_radius_meters: float = 2000.0
    max_radius_meters: float = 10000.0

    # Security & Rate Limiting
    rate_limit_chat: str = "5/minute"
    max_sessions: int = 1000

    # Geolocation
    enable_browser_coordinates: bool = True
    default_lat: float = 48.1374
    default_lon: float = 11.5755

    # Helpers

    def get_domain(self, name: str) -> DomainConfig | None:
        """Look up a domain config by name."""
        for domain in self.domains:
            if domain.name == name:
                return domain
        return None

    def enabled_domains(self) -> list[DomainConfig]:
        """Return only the domains that are currently enabled."""
        return [d for d in self.domains if d.enabled]

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def log_level_int(self) -> int:
        """Convert string log level to logging constant."""
        return getattr(logging, self.log_level.upper(), logging.INFO)

    @property
    def llm_configured(self) -> bool:
        """Whether an OpenAI API key is set."""
        return bool(self.openai_api_key)

    @property
    def fail_on_invalid_records(self) -> bool:
        """Global strict mode — True if ANY domain uses strict validation."""
        return any(d.strict for d in self.domains)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
