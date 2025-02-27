# LangChain Application

This project is a LangChain-based application built using Python and Docker. It includes a Docker
environment configured to simplify the development, building, and execution of the application.

## Requirements

- **Docker** and **Docker Compose** installed
- **Python 3.11** (for local execution, optional)

## Environment Setup

1. **Clone this repository**:

   ```bash
   git clone https://github.com/your-username/langchain-app.git
   cd langchain

1. **Configure the** `**.env**` **file**:

   - If the `.env` file does not exist, it will be automatically created from `.env-example` when you run `make build`.
   - If needed, you can manually create the `.env` file with the required variables.

2. **Install local dependencies (optional):**

   ```
   pip install -r requirements.txt
   ```

## Architecture

### Dockerfile

The `Dockerfile` contains the configuration for building the environment:

- Based on the `python:3.10-slim` image.
- Installs dependencies from `requirements.txt`.
- Sets `/app` as the working directory and copies all files to it.
- Configures the entry command to run `src/main.py`.

## License

<a href="LICENSE" target="_blank">GNU GENERAL PUBLIC LICENSE</a>

