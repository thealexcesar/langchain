# LangChain Application

This project is a LangChain-based application built using Python and Docker. It includes a Docker environment configured to simplify the development, building, and execution of the application.

## Requirements

- **Docker** and **Docker Compose** installed
- **Python 3.10** (for local execution, optional)
- **Make** (optional, to simplify commands)

## Environment Setup

1. **Clone this repository**:

   ```bash
   git clone https://github.com/your-username/langchain-app.git
   cd langchain-app

1. **Configure the** `**.env**` **file**:

   - If the `.env` file does not exist, it will be automatically created from `.env-example` when you run `make build`.
   - If needed, you can manually create the `.env` file with the required variables.

2. **Install local dependencies (optional):**

   ```
   pip install -r requirements.txt
   ```

## Available Commands

This project uses a **Makefile** to simplify common tasks. Here are the main commands:

### Command Execution

- `**make**` or `**make default**`: Executes the default flow: builds and runs the application.
- `**make build**`: Builds the Docker image. If `.env` does not exist, it will be created from `.env-example`.
- `**make run**`: Runs the application inside the Docker container.
- `**make up**`: Starts the Docker Compose services.
- `**make down**`: Stops the Docker Compose services.
- `**make restart**`: Restarts the Docker Compose services (down and up).
- `**make clean**`: Removes containers, volumes, and Docker images related to the application.
- `**make logs**`: Displays the application logs in real-time.
- `**make shell**`: Accesses the interactive shell of the `langchain-app` container.
- `**make test-interactive**`: Runs the Python script interactively outside of Docker.

## Architecture

### Dockerfile

The `Dockerfile` contains the configuration for building the environment:

- Based on the `python:3.10-slim` image.
- Installs dependencies from `requirements.txt`.
- Sets `/app` as the working directory and copies all files to it.
- Configures the entry command to run `src/main.py`.

### docker-compose.yml

Configures the main `app` service:

- **Build**: Builds the image from the Dockerfile.
- **Ports**: Exposes port 8000 to the host.
- **Volumes**: Mounts the local directory into the container for easier development.
- **Networks**: Uses a custom `langchain-network`.
- **env_file**: Loads environment variables from the `.env` file.

## Project Structure

```
langchain-app/
├── Dockerfile            # Docker image configuration
├── Makefile              # Task automation
├── docker-compose.yml    # Docker Compose configuration
├── requirements.txt      # Project dependencies
├── src/                  # Application source code
│   └── main.py           # Main application script
├── .env-example          # Example environment configuration
└── README.md             # Project documentation
```

## How It Works

1. **Build and Run:**
   - Use `make build` to build the Docker image.
   - Use `make run` to execute the application.
2. **Interacting with LangChain:**
   - The code uses LangChain to process and respond to user inputs.
   - Currently, there are deprecation warnings indicating that some classes and methods need updates for future LangChain versions.
3. **Troubleshooting:**
   - Check logs using `make logs`.
   - If you need to completely restart the environment, use `make clean` followed by `make build`.

## License
