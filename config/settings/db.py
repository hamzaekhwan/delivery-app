from config.env import env


POSTGRES_USER = env.str("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = env.str("POSTGRES_PASSWORD")
POSTGRES_HOST = env.str("POSTGRES_HOST", "db")
POSTGRES_PORT = env.str("POSTGRES_PORT", "5432")
POSTGRES_DB = env.str("POSTGRES_DB", "super_delivery")


# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": POSTGRES_DB,
        "USER": POSTGRES_USER,
        "PASSWORD": POSTGRES_PASSWORD,
        "HOST": POSTGRES_HOST,
        "PORT": POSTGRES_PORT,
    }
}
