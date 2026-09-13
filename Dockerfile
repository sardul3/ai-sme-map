FROM python:3.12-slim
WORKDIR /app
COPY . .
# Validate-only smoke for Linux. The atlas server binds 127.0.0.1 and is not this image's job.
CMD ["python3", "scripts/validate.py"]
