# Use a slim Python base image
FROM python:3.10-slim-buster

# Set working directory
WORKDIR /app

# Install required libraries (using requirements.txt)
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script and any other dependencies
COPY . .

# Expose the port
EXPOSE 8080

# Set the CMD to run the application
CMD ["python", "api.py"]
