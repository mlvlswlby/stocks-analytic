# Use official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Validate file structure
RUN ls -R /app

# Expose port 7860 for FastAPI (Default for Hugging Face Spaces)
EXPOSE 7860

# Define environment variable
ENV MODULE_NAME="backend.main"
ENV VARIABLE_NAME="app"
ENV PORT="7860"

# Run app.py when the container launches
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
