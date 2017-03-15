# Use python:2-alpine
FROM python:2-alpine

# Copy in the requirements.txt file
COPY requirements.txt /requirements.txt

# Install the requirements
RUN pip install -r /requirements.txt

# Copy in the application
COPY app /app

# Setup Flask
ENV FLASK_APP=/app/postscore.py

ENTRYPOINT flask run -h '::'
