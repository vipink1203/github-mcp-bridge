FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TRANSPORT=stdio
ENV PORT=8050
ENV HOST=0.0.0.0

# Run the application
CMD ["python", "main.py"]
