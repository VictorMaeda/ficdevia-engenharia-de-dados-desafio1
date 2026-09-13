FROM apache/superset:latest

USER root

RUN /app/.venv/bin/python3 -m ensurepip --upgrade \
    && /app/.venv/bin/python3 -m pip install --no-cache-dir psycopg2-binary \
    || (which uv && uv pip install --python /app/.venv/bin/python3 psycopg2-binary)

USER superset

COPY superset_config.py /app/pythonpath/superset_config.py