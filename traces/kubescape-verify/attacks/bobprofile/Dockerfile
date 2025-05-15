# Use a lightweight Python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the Python script into the container
COPY syscall_demo.py .

# Install any required Python packages (if needed)
RUN pip install --no-cache-dir requests

# Set the entrypoint to the Python script
ENTRYPOINT ["python", "syscall_demo.py"]