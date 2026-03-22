"""Agent implementation for the template agent system.

This module provides the core agent functionality using the deepagents library,
including initialization, configuration, and agent creation with MCP tools,
skills, subagents, and memory.
"""

from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from deepagents import SubAgent, create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from template_agent.src.core.exceptions.exceptions import AppException, AppExceptionCode
from template_agent.src.core.storage import get_global_checkpoint
from template_agent.src.settings import settings
from template_agent.utils.pylogger import get_python_logger

logger = get_python_logger(log_level=settings.PYTHON_LOG_LEVEL)

# Repo root for loading memory, skills, and subagents
REPO_ROOT = Path(__file__).parent.parent.parent.parent  # template-agent/


async def initialize_database() -> None:
    """Initialize PostgreSQL database schema on application startup.

    This function ensures the checkpoints table and related schema are created
    before any requests are processed. Only runs when using PostgreSQL storage
    (USE_INMEMORY_SAVER=False).

    Raises:
        AppException: If database connection or schema creation fails.
    """
    if settings.USE_INMEMORY_SAVER:
        logger.info("Using in-memory storage - skipping database initialization")
        return

    try:
        logger.info("Initializing PostgreSQL database schema")
        async with AsyncPostgresSaver.from_conn_string(
            settings.database_uri
        ) as checkpoint:
            # Setup database schema - creates checkpoints table and indexes
            if hasattr(checkpoint, "setup"):
                await checkpoint.setup()
                logger.info("Database schema initialized successfully")
            else:
                logger.warning(
                    "AsyncPostgresSaver does not have setup method - schema may need manual creation"
                )
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}", exc_info=True)
        raise AppException(
            f"Database initialization failed: {str(e)}",
            AppExceptionCode.CONFIGURATION_INITIALIZATION_ERROR,
        )


@asynccontextmanager
async def get_template_agent(
    sso_token: str | None = None, enable_checkpointing: bool = True
):
    """Get a fully initialized deep agent with MCP tools, skills, subagents, and memory.

    This function creates and configures a deep agent using the deepagents library
    with the necessary tools from MCP, skills, subagents, and memory. It uses an
    async context manager to ensure proper resource cleanup.

    Args:
        sso_token: Optional access token for authentication. If provided,
            it will be used for authorization headers in MCP client requests.
        enable_checkpointing: Whether to enable checkpointing/persistence.
            Set to False for streaming-only operations that shouldn't save to DB.

    Yields:
        The initialized deep agent instance.

    Raises:
        Exception: If there are issues with database connections or agent setup.
    """
    # Initialize MCP client and get tools
    tools: list = []

    # Log MCP connection details for debugging
    logger.info(f"Attempting to connect to MCP server at {settings.MCP_SERVER_URL}")
    logger.info(f"MCP server name: {settings.MCP_SERVER_NAME}")
    logger.info(f"MCP transport protocol: {settings.MCP_TRANSPORT_PROTOCOL}")
    logger.info(f"MCP connection timeout: {settings.MCP_CONNECTION_TIMEOUT}s")
    logger.info(f"SSO authentication: {'Yes' if sso_token else 'No'}")

    try:
        import asyncio

        # Add timeout wrapper for MCP connection
        async def connect_with_timeout():
            # Configure MCP client with SSL verification setting
            server_config: dict = {
                "url": settings.MCP_SERVER_URL,
                "transport": settings.MCP_TRANSPORT_PROTOCOL,
                "headers": {"Authorization": f"Bearer {sso_token}"}
                if sso_token
                else {},
            }

            # Add SSL verification setting (verify=False disables cert verification)
            if not settings.MCP_SSL_VERIFY:
                server_config["verify"] = False
                logger.warning(
                    "SSL certificate verification disabled for MCP connection"
                )

            client = MultiServerMCPClient({settings.MCP_SERVER_NAME: server_config})
            return await client.get_tools()

        tools = await asyncio.wait_for(
            connect_with_timeout(), timeout=settings.MCP_CONNECTION_TIMEOUT
        )
        logger.info(
            f"Successfully connected to MCP server and loaded {len(tools)} tools"
        )
        logger.info(f"Available tools: {[tool.name for tool in tools]}")
    except asyncio.TimeoutError:
        # Handle timeout specifically
        error_msg = (
            f"Timeout connecting to MCP server at {settings.MCP_SERVER_URL} "
            f"after {settings.MCP_CONNECTION_TIMEOUT}s. "
            f"Server may be down or unreachable."
        )
        logger.error(error_msg)

        if settings.USE_INMEMORY_SAVER:
            logger.warning("Running in local development mode without MCP tools")
            tools = []
        else:
            logger.critical(error_msg)
            raise AppException(
                error_msg,
                AppExceptionCode.PRODUCTION_MCP_CONNECTION_ERROR,
            )
    except Exception as e:
        # Log detailed error information for other exceptions
        logger.error(
            f"Failed to connect to MCP server at {settings.MCP_SERVER_URL}",
            exc_info=True,
        )
        logger.error(f"MCP connection error type: {type(e).__name__}")
        logger.error(f"MCP connection error details: {str(e)}")

        if settings.USE_INMEMORY_SAVER:
            logger.warning("Running in local development mode without MCP tools")
            tools = []  # No tools for local development
        else:
            # In production, MCP is required
            error_msg = (
                f"Failed to connect to required MCP server at {settings.MCP_SERVER_URL}. "
                f"Error: {type(e).__name__}: {str(e)}"
            )
            logger.critical(error_msg)
            raise AppException(
                error_msg,
                AppExceptionCode.PRODUCTION_MCP_CONNECTION_ERROR,
            )

    # Initialize the language model with service account credentials
    import google.auth

    credentials, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
        credentials=credentials,
        project=project,
    )

    # Load subagents from YAML
    subagents_path = REPO_ROOT / "subagents.yaml"
    logger.info(f"Loading subagents from {subagents_path}")

    subagents_config: list[SubAgent] | None = None
    if subagents_path.exists():
        raw = yaml.safe_load(subagents_path.read_text())
        entries = raw.get("subagents", []) if isinstance(raw, dict) else []
        subagents_config = [
            SubAgent(
                name=e["name"],
                description=e.get("description", ""),
                system_prompt=e.get("instructions", ""),
            )
            for e in entries
        ]
        logger.info(f"Loaded {len(subagents_config)} subagents")
    else:
        logger.warning(f"Subagents file not found at {subagents_path}")

    # Setup memory (AGENTS.md)
    memory_files = []
    agents_md_path = REPO_ROOT / "AGENTS.md"
    if agents_md_path.exists():
        memory_files.append(str(agents_md_path))
        logger.info(f"Loaded memory from {agents_md_path}")
    else:
        logger.warning(f"AGENTS.md not found at {agents_md_path}")

    # Setup skills directory
    skills_dir = REPO_ROOT / "skills"
    skills_path = [str(skills_dir)] if skills_dir.exists() else []
    if skills_path:
        logger.info(f"Loaded skills from {skills_dir}")
    else:
        logger.warning(f"Skills directory not found at {skills_dir}")

    # Setup backend for deep agent
    backend = FilesystemBackend(root_dir=str(REPO_ROOT))

    if not enable_checkpointing:
        # Create agent without checkpointing for streaming-only operations
        logger.info(
            "Creating deep agent without checkpointing for streaming-only operations"
        )
        agent = create_deep_agent(
            model=model,
            memory=memory_files,
            skills=skills_path,
            tools=tools,
            subagents=subagents_config,
            backend=backend,
            # No checkpointer - streaming only, no persistence
        )
        logger.info("Deep agent initialized successfully without checkpointing")
        yield agent
    elif settings.USE_INMEMORY_SAVER:
        # Use single global checkpoint for local development
        logger.info("Using single global checkpoint for local development")
        checkpoint = get_global_checkpoint()

        agent = create_deep_agent(
            model=model,
            memory=memory_files,
            skills=skills_path,
            tools=tools,
            subagents=subagents_config,
            backend=backend,
            checkpointer=checkpoint,
        )
        logger.info("Deep agent initialized successfully with single global checkpoint")
        yield agent
    else:
        # Use PostgreSQL storage for production
        logger.info("Using PostgreSQL checkpoint for production")
        async with AsyncPostgresSaver.from_conn_string(
            settings.database_uri
        ) as checkpoint:
            # Setup database connection once
            if hasattr(checkpoint, "setup"):
                await checkpoint.setup()

            # Create the deep agent with PostgreSQL checkpointer
            agent = create_deep_agent(
                model=model,
                memory=memory_files,
                skills=skills_path,
                tools=tools,
                subagents=subagents_config,
                backend=backend,
                checkpointer=checkpoint,
            )

            logger.info(
                "Deep agent initialized successfully with PostgreSQL checkpoint"
            )
            yield agent
