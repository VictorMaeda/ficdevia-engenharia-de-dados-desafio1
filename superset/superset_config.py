import os
from urllib.parse import quote_plus


# Chave usada pelo Superset para sessões e recursos internos.
SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]


# Banco interno de metadados do Superset.
meta_user = quote_plus(os.environ["SUPERSET_META_USER"])
meta_password = quote_plus(os.environ["SUPERSET_META_PASSWORD"])
meta_db = quote_plus(os.environ["SUPERSET_META_DB"])

meta_host = os.environ.get(
    "SUPERSET_META_HOST",
    "superset_meta_db",
)

meta_port = os.environ.get(
    "SUPERSET_META_PORT",
    "5432",
)


SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://"
    f"{meta_user}:{meta_password}"
    f"@{meta_host}:{meta_port}/{meta_db}"
)


SQLALCHEMY_TRACK_MODIFICATIONS = False