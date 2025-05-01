FROM python:3.11-slim

# include system dependencies libraries
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    rm -rf /var/lib/apt/lists/*

# install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy requirements and install
COPY ./requirements.txt ./requirements.txt
RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY ./main.py ./main.py
COPY ./config.toml ./config.toml

CMD ["python", "main.py"]