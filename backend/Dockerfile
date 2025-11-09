FROM python:3.12

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY pyproject.toml .
COPY README.md .
COPY src ./src
COPY app.py .

# Install the application dependencies.
WORKDIR /app
RUN uv sync

EXPOSE 80

# Run migration & the application.
WORKDIR /app/
CMD /app/.venv/bin/alembic upgrade head ; uv run fastapi dev app.py --host 0.0.0.0 --port 80