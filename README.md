# Component Reliability

This is a Flask application that allows users to get the reliability of components either by entering a component name directly or by uploading an Excel file with multiple component names.

## Prerequisites

- Docker
- An eFind token
- A PostgreSQL database URL

## Building the Docker Container

To build the Docker container, navigate to the project directory and run the following command:

```bash
docker build -t component_reliability_app .
```

## Running the Docker Container

```bash
docker run -e DATABASE_URL=your_database_url -e EFIND_TOKEN=your_efind_token -p 5000:5000 component_reliability_app
```

Please replace `your_database_url`, and `your_efind_token` with your actual Docker image name,
PostgreSQL database URL, and eFind token, respectively.