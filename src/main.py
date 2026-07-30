# src/main.py

"""Entry point for the automated YouTube content channel project.

This script sets up logging, loads environment variables, assembles the LangGraph workflow,
provides the initial state, and runs the workflow synchronously.

The script is designed to work with the mock implementations provided in the agent
modules, so it can be executed without external API keys or a real YouTube account.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
import json
import logging
import shutil # For potential cleanup on exit
from dotenv import load_dotenv

# ------------------------------------------------------------
# Logging configuration – ensure we have a logger before any imports.
# ------------------------------------------------------------
log_file_path = "youtube_automation.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path, mode="w", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Environment variables – load from .env if present.
# ------------------------------------------------------------
load_dotenv()
logger.info("Environment variables loaded from .env (if present).")

# ------------------------------------------------------------
# Import LangGraph and the workflow definition.
# ------------------------------------------------------------
try:
    # The LangGraph library is required for the workflow.
    from langgraph.graph import END
    try:
        from .graph import create_youtube_workflow, WorkflowState
    except ImportError:
        from graph import create_youtube_workflow, WorkflowState
except Exception as e:  # Broad except to catch import errors or missing library.
    logger.critical(
        f"Failed to import LangGraph components or workflow: {e}. "
        "Make sure the 'langgraph' package is installed and src/graph.py is present."
    )
    # Exit early – we cannot continue without the workflow.
    raise SystemExit(1)

# ------------------------------------------------------------
# Main execution function.
# ------------------------------------------------------------
def main():
    logger.info("Starting the YouTube automation workflow.")

    # --------------------------------------------------------
    # Compile the workflow.
    # --------------------------------------------------------
    try:
        workflow = create_youtube_workflow()
        logger.info("LangGraph workflow compiled successfully.")
    except Exception as e:
        logger.critical(f"Error compiling workflow: {e}")
        raise SystemExit(1)

    # --------------------------------------------------------
    # Define the initial state for the workflow.
    # --------------------------------------------------------
    initial_state: WorkflowState = {
        "initial_input": {
            "niche": os.getenv("YOUTUBE_NICHE", "AI in Education"),
            "target_audience": os.getenv("YOUTUBE_TARGET_AUDIENCE", "general"),
        },
        "topic_ideas": [],
        "selected_topic": None,
        "script_content": None,
        "audio_file_path": None,
        "video_file_path": None,
        "youtube_url": None,
        "error_message": None,
        # For a fully automated dry‑run we simulate user approval.
        "user_approval_needed": True,
        "user_approved_topic": True,
        "user_approved_script": True,
        "is_video_published": False,
    }
    logger.info(f"Initial state prepared with niche: {initial_state['initial_input']['niche']}")

    # --------------------------------------------------------
    # Run the workflow synchronously.
    # --------------------------------------------------------
    try:
        final_state = workflow.invoke(initial_state)
        logger.info("Workflow execution completed.")
    except Exception as e:
        logger.critical(f"Fatal error during workflow execution: {e}", exc_info=True)
        raise SystemExit(1)

    # --------------------------------------------------------
    # Report the outcome.
    # --------------------------------------------------------
    if final_state.get("is_video_published") and final_state.get("youtube_url"):
        logger.info(f"[SUCCESS] Video published! URL: {final_state['youtube_url']}")
        print("\n=== Workflow Completed Successfully ===")
        print(f"YouTube URL: {final_state['youtube_url']}")
    elif final_state.get("error_message"):
        logger.error(f"Workflow ended with error: {final_state['error_message']}")
        print("\n=== Workflow Ended with Error ===")
        print(f"Error: {final_state['error_message']}")
    else:
        logger.warning("Workflow finished without publishing and without an explicit error.")
        print("\n=== Workflow Finished (No Publication) ===")
        print("Check the log file for details.")

    # Optional – dump the final state for debugging.
    # logger.debug(json.dumps(final_state, indent=2))

if __name__ == "__main__":
    main()
