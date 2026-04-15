# Minimal Dockerfile for development and simple deployment
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/app

# Install lightweight system deps. Audio-related deps are optional (controlled via build-arg).
# To include audio support (pyaudio/ffmpeg), build with: --build-arg INSTALL_AUDIO_DEPS=true
ARG INSTALL_AUDIO_DEPS=false
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git curl docker.io \
    && if [ "$INSTALL_AUDIO_DEPS" = "true" ]; then apt-get install -y --no-install-recommends libasound2-dev ffmpeg portaudio19-dev; fi \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install them. If audio deps are enabled, install extra requirements.
COPY requirements.txt ./
COPY requirements-audio.txt ./
RUN pip install --upgrade pip && \
    if [ "$INSTALL_AUDIO_DEPS" = "true" ] && [ -f requirements-audio.txt ]; then \
        pip install -r requirements.txt -r requirements-audio.txt; \
    else \
        # Exclude pyaudio from requirements when not installing audio deps (avoids missing headers)
        grep -v -E '^pyaudio\b' requirements.txt > /.tmp-reqs && pip install -r /.tmp-reqs; \
    fi

# Copy project files
COPY . .

# Expose the port the app uses
EXPOSE 5001

# Environment defaults (override with .env or docker-compose)
ENV FLASK_APP=app.py

# Use a production WSGI server and bind to Render's dynamic port
CMD ["sh", "-lc", "gunicorn -w 4 -b 0.0.0.0:$PORT app:app"]
