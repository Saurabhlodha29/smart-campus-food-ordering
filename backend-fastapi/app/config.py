"""
Pydantic-Settings config — mirrors every variable in .env.example / application.yml.

All variable NAMES are preserved exactly so the existing backend/.env keeps
working unedited (just copy or symlink it to backend-fastapi/.env).

New variable added here that has no Spring equivalent:
  ENVIRONMENT — "development" enables the simulateOrderPayment bypass
                (spec §4.10 security fix; default "production" = bypass disabled)
"""
from urllib.parse import quote_plus

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
          - JDBC format: jdbc:postgresql://host:port/db
          - Standard:    postgresql://host:port/db
          - Full URL with embedded creds: postgresql://user:pass@host:port/db

        If DB_USERNAME is set and the URL has no embedded credentials,
        the credentials are injected automatically — matching Spring's separate
        url / username / password datasource config.
        """
        url = self.DB_URL.strip()

        # Strip JDBC prefix if present
        if url.startswith("jdbc:"):
            url = url[5:]

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
    def is_development(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"


settings = Settings()
