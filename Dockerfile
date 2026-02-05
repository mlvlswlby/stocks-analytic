# Use official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
# Copy the requirements file into the container
COPY backend/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend directory into the container
COPY backend/ ./backend/

# Validate file structure (Debugging step to ensure files are where we expect)
RUN ls -R /app/backend

# Expose port 8000 for FastAPI
EXPOSE 8000

# Define environment variable
ENV MODULE_NAME="backend.main"
ENV VARIABLE_NAME="app"
ENV PORT="8000"

# Run app.py when the container launches
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
