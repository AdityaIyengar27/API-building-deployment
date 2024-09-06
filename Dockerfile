# Use the official Python image as a base image
FROM python:3.12-slim as base-image

# Set the working directory in the container
WORKDIR /app

# Install bash and other necessary packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file to the working directory
COPY requirements.txt /app/

# Create a virtual environment
RUN python -m venv /app/venv

# Install dependencies
RUN /app/venv/bin/python -m pip install --upgrade pip \
    && /app/venv/bin/pip install -r requirements.txt

# Copy the application code into the container
COPY . /app

# --------------------------------------------------------------------------------------------------------------
FROM python:3.12-slim as final-image

# Set the working directory in the container
WORKDIR /app

# Install bash
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the base image
COPY --from=base-image /app/venv /app/venv

# Set the PATH to include the virtual environment
ENV PATH="/app/venv/bin:$PATH"

# Expose port 8080 to allow communication to/from the server
EXPOSE 8080

# Copy the application code into the container
# Copy the necessary files to the working directory
COPY main.py /app/
COPY database_queries.py /app/
COPY database_server_operations.py /app/
COPY helper_module.py /app/
COPY scraper.py /app/
COPY tests /app/tests/

# Command to run the FastAPI application using uvicorn server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
