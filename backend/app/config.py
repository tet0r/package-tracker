import os


class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-key-change-me")
    DATABASE_URL = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://tracker:tracker@db:5432/tracker"
    )
    NOMINATIM_USER_AGENT = os.environ.get(
        "NOMINATIM_USER_AGENT", "self-hosted-package-tracker/1.0"
    )


settings = Settings()
