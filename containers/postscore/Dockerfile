# Use python:2-alpine
FROM python:2-alpine
# Copy in the application
COPY app /app

# Copy in the requirements.txt file
COPY requirements.txt /requirements.txt

# Install the requirements
RUN pip install -r /requirements.txt
