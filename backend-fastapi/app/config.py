"""
Pydantic-Settings config — mirrors every variable in .env.example / application.yml.

All variable NAMES are preserved exactly so the existing backend/.env keeps
working unedited (just copy or symlink it to backend-fastapi/.env).

New variable added here that has no Spring equivalent:
  ENVIRONMENT — "development" enables the simulateOrderPayment bypass
                (spec §4.10 security fix; default "production" = bypass disabled)
"""
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    # DB_URL accepts either a full JDBC URL (jdbc:postgresql://...) or a plain
    # SQLAlchemy URL (postgresql://...).  Credentials in the URL OR via the
    # separate DB_USERNAME / DB_PASSWORD variables (like Spring's datasource
    # config) are both supported.
    DB_URL: str = ""
    DB_USERNAME: str = ""
    DB_PASSWORD: str = ""

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_SECRET: str = ""
    JWT_EXPIRY_MS: int = 86400000  # 24 h default

    # ── OTP ───────────────────────────────────────────────────────────────────
    OTP_SECRET: str = ""
    OTP_EXPIRY_MINUTES: int = 10

    # ── Razorpay ──────────────────────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = "NOT_SET"
    RAZORPAY_PAYOUT_ACCOUNT: str = "NOT_SET"
    RAZORPAY_PAYOUTS_ENABLED: bool = False

    # ── Mail ──────────────────────────────────────────────────────────────────
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""

    # ── SuperAdmin seed ───────────────────────────────────────────────────────
    SUPERADMIN_EMAIL: str = "superadmin@smartcampus.dev"
    SUPERADMIN_PASSWORD: str = ""
    SUPERADMIN_FULLNAME: str = "Platform SuperAdmin"

    # ── ML Service ────────────────────────────────────────────────────────────
    ML_SERVICE_URL: str = "http://localhost:8000"
    ML_SERVICE_ENABLED: bool = True
    ML_SERVICE_TIMEOUT_MS: int = 3000

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # ── Environment flag (NEW — not in Spring config) ─────────────────────────
    # "development" enables the simulateOrderPayment bypass (spec §4.10 fix).
    # Any other value (including the default "production") disables it.
    ENVIRONMENT: str = "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore VITE_* and other frontend vars in the same .env
    )

    @computed_field
    @property
    def async_database_url(self) -> str:
        """
        Construct an asyncpg-compatible SQLAlchemy URL.

        Accepts:
          - JDBC format: jdbc:postgresql://host:port/db[?pgbouncer=true&options=...&prepareThreshold=0]
          - Standard:    postgresql://host:port/db
          - Full URL with embedded creds: postgresql://user:pass@host:port/db

        If DB_USERNAME is set and the URL has no embedded credentials,
        the credentials are injected automatically — matching Spring's separate
        url / username / password datasource config.

        The existing .env has a Supabase pooler URL with PgBouncer. asyncpg
        doesn't recognise `pgbouncer` (a JDBC-only Hikari param) or
        `prepareThreshold` (asyncpg uses `statement_cache_size` instead), so
        we strip them from the URL and let ``asyncpg_connect_args`` deliver the
        equivalents (server_settings + statement_cache_size=0 for PgBouncer
        transaction mode safety).
        """
        url = self.DB_URL.strip()

        # Strip JDBC prefix if present
        if url.startswith("jdbc:"):
            url = url[5:]

        # Parse URL to clean up JDBC-only query parameters
        if "?" in url:
            base, qs = url.split("?", 1)
            params = dict(parse_qsl(qs))
            # Strip JDBC/Hikari-only params; also strip `options` (asyncpg rejects
            # it as a flat kwarg — it's delivered via server_settings in connect_args)
            for k in ("pgbouncer", "prepareThreshold", "options"):
                params.pop(k, None)
            cleaned = urlencode(params, safe=",-:/")
            url = f"{base}?{cleaned}" if cleaned else base

        # Normalise scheme to asyncpg driver
        for old in ("postgresql://", "postgres://"):
            if url.startswith(old):
                url = "postgresql+asyncpg://" + url[len(old):]
                break
        else:
            # URL might already have the asyncpg scheme or be empty
            if url and not url.startswith("postgresql+asyncpg://"):
                url = "postgresql+asyncpg://" + url

        # Inject credentials if not already embedded and DB_USERNAME is set
        if "://" in url and self.DB_USERNAME:
            scheme, authority_path = url.split("://", 1)
            host_part = authority_path.split("/")[0]
            if "@" not in host_part:
                user = quote_plus(self.DB_USERNAME)
                pw = quote_plus(self.DB_PASSWORD or "")
                url = f"{scheme}://{user}:{pw}@{authority_path}"

        return url

    @property
    def asyncpg_connect_args(self) -> dict:
        """
        Keyword arguments to pass directly to asyncpg.connect().

        Translates JDBC pgBouncer-pool parameters from the original DB_URL into
        their asyncpg equivalents so SQLAlchemy can talk to the Supabase pooler:

          - `prepareThreshold=0` (JDBC)
              Tells the Hikari pool not to use server-side prepared statements
              (which break across PgBouncer transactions).
              Equivalent for asyncpg: `statement_cache_size=0` (asyncpg uses
              prepared-statement caching internally, which will fail with
              "prepared statement does not exist" under transaction-mode
              PgBouncer unless disabled).
          - `options=-c search_path=public` (URL query, kept by async_database_url)
              PostgreSQL command-line options — must be set via
              `server_settings["options"]` since asyncpg doesn't accept arbitrary
              query-string keys without a `<dialect>_` prefix.
          - `pgbouncer=true` (JDBC Hikari)
              Drop-only; no asyncpg equivalent needed.

        Includes only the keys needed; returns an empty dict if DB_URL has no
        options query parameter.
        """
        url = self.DB_URL.strip()
        if url.startswith("jdbc:"):
            url = url[5:]
        connect_args: dict = {
            "statement_cache_size": 0,  # disable prepared statements (PgBouncer tx mode)
        }
        if "?" in url:
            params = dict(parse_qsl(url.split("?", 1)[1]))
            options = params.get("options")
            if options:
                connect_args["server_settings"] = {"options": options}
        return connect_args

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"


settings = Settings()
