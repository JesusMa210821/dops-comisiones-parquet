FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

# Usuario sin privilegios
RUN useradd --create-home pipeline && mkdir -p /app/output /app/reports && chown -R pipeline /app
USER pipeline

ENTRYPOINT ["python", "-m", "app.main"]
CMD ["--env", "dev"]
