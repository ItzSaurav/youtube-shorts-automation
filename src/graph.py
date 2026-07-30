# src/graph.py

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
import json
import logging
import shutil # For file cleanup
from typing import Any, Dict, List, Optional, TypedDict, Union

from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)

# Import agent modules - support both package (.agents) and direct (agents) imports
try:
    try:
        from .agents.topic_research import TopicResearchAgent
        from .agents.script_generation import ScriptGenerationAgent
        from .agents.audio_generation import AudioGenerationAgent
        from .agents.video_generation import VideoGenerationAgent
        from .agents.publishing import PublishingAgent
    except ImportError:
        from agents.topic_research import TopicResearchAgent
        from agents.script_generation import ScriptGenerationAgent
        from agents.audio_generation import AudioGenerationAgent
        from agents.video_generation import VideoGenerationAgent
        from agents.publishing import PublishingAgent
except Exception as e:
    logger.error(f"Failed to import agent modules: {e}. Ensure all agent files are present.")

# Import utility clients - support both package (.utils) and direct (utils) imports
try:
    try:
        from .utils.api_clients import (
            get_youtube_client,
            get_tts_client,
            get_stock_media_client,
            get_llm_client
        )
        from .utils.file_management import FileManagement
    except ImportError:
        from utils.api_clients import (
            get_youtube_client,
            get_tts_client,
            get_stock_media_client,
            get_llm_client
        )
        from utils.file_management import FileManagement
except Exception as e:
    logger.error(f"Failed to import utility modules: {e}. Ensure utils files are present.")
    # Define dummy utility functions if import fails
    def get_youtube_client(): logger.error("YouTube client not available."); return None
    def get_tts_client(): logger.error("TTS client not available."); return None
    def get_stock_media_client(): logger.error("Stock media client not available."); return None
    def get_llm_client(): logger.error("LLM client not available."); return None
    # Provide a dummy FileManagement that logs and returns None/basic paths
    class DummyFileManagement:
        def __init__(self):
             self.base_dir = os.getcwd()
             self.data_dir = os.path.join(self.base_dir, 'data')
             os.makedirs(self.data_dir, exist_ok=True)
             logger.error("FileManagement not available. File operations will fail.")
        def save_content_to_file(self, *args, **kwargs): logger.error("FileManagement.save_content_to_file failed: not available."); return None
        def download_file(self, *args, **kwargs): logger.error("FileManagement.download_file failed: not available."); return None
        def create_temp_dir(self, prefix=""):
             temp_path = os.path.join(self.data_dir, f"mock_temp_{prefix}_{os.urandom(4).hex()}")
             os.makedirs(temp_path, exist_ok=True)
             logger.info(f"Mock temp dir created: {temp_path}")
             return temp_path
        def cleanup_directory(self, dir_path):
             logger.info(f"Mock cleanup of directory: {dir_path}")
             try:
                 if os.path.exists(dir_path) and os.path.isdir(dir_path):
                     shutil.rmtree(dir_path)
                     logger.info(f"Mock cleanup succeeded for: {dir_path}")
                     return True
             except OSError as e:
                 logger.error(f"Mock cleanup failed removing {dir_path}: {e}")
             return False
        def read_file_content(self, filepath): logger.error("FileManagement.read_file_content failed: not available."); return None
    FileManagement = DummyFileManagement


logger = logging.getLogger(__name__)

# --- Workflow State Definition ---

class WorkflowState(TypedDict):
    """Represents the state of the YouTube automation workflow."""
    initial_input: Dict[str, Any]         # User-provided initial parameters (e.g., niche, target_audience)
    topic_ideas: List[Dict[str, Any]]     # List of potential video topics found
    selected_topic: Optional[Dict[str, Any]] # The topic chosen for video creation
    script_content: Optional[Dict[str, Any]] # Generated script content (JSON)
    audio_file_path: Optional[str]        # Path to the generated audio file
    video_file_path: Optional[str]        # Path to the generated video file
    youtube_url: Optional[str]            # URL of the published YouTube video
    error_message: Optional[str]          # Any error encountered during the process
    user_approval_needed: bool            # Flag to indicate if user approval is required for certain steps
    user_approved_topic: bool             # Flag for user approval of the selected topic
    user_approved_script: bool            # Flag for user approval of the generated script
    is_video_published: bool              # Flag to indicate if video was successfully published

# --- Workflow Graph Definition ---

def create_youtube_workflow():
    """
    Creates and configures the LangGraph workflow for YouTube automation.
    This function builds the graph of nodes and edges representing the workflow steps.
    """
    workflow = StateGraph(WorkflowState)

    # --- Instantiate Agents and Clients ---
    # Agents will be instantiated here and their associated clients passed during initialization.
    # This assumes clients are available and correctly configured via get_* functions.
    topic_research_agent_instance = None
    script_gen_agent_instance = None
    audio_gen_agent_instance = None
    video_gen_agent_instance = None
    publishing_agent_instance = None
    file_management_instance = None # FileManagement is used by multiple agents

    try:
        # Initialize FileManagement once, as it's used by multiple agents and the cleanup node.
        file_management_instance = FileManagement()

        # Initialize agents with their required clients.
        topic_research_agent_instance = TopicResearchAgent(
            youtube_client=get_youtube_client(),
            llm_client=get_llm_client(),
        )
        script_gen_agent_instance = ScriptGenerationAgent(
            llm_client=get_llm_client(),
            file_management=file_management_instance,
        )
        audio_gen_agent_instance = AudioGenerationAgent(
            tts_client=get_tts_client(),
            file_management=file_management_instance
        )
        video_gen_agent_instance = VideoGenerationAgent(
            stock_media_client=get_stock_media_client(),
            file_management=file_management_instance
        )
        publishing_agent_instance = PublishingAgent(
            youtube_client=get_youtube_client(),
            file_management=file_management_instance # Though not used for output by publishing, good to have
        )
    except Exception as e:
        logger.error(f"Initialization failed: {e}. Some agents or clients may not be available.")
        # If critical clients/agents fail to initialize, the graph might not run correctly.
        # The nodes below will need to handle potential None instances of agents/clients.


    # --- Define Workflow Nodes ---

    def research_topics_node(state: WorkflowState):
        """Node for topic research."""
        logger.info("Running topic research node...")
        new_entries: Dict[str, Any] = {"topic_ideas": [], "error_message": None}
        if not topic_research_agent_instance:
            new_entries["error_message"] = "Topic Research Agent not initialized."
            return new_entries

        try:
            niche = state.get("initial_input", {}).get("niche")
            if not niche:
                raise ValueError("Niche not provided in initial input for topic research.")

            ideas = topic_research_agent_instance.run(niche)
            new_entries["topic_ideas"] = ideas
            logger.info(f"Found {len(ideas)} topic ideas.")
        except Exception as e:
            logger.error(f"Error in topic research agent: {e}")
            new_entries["error_message"] = f"Topic research failed: {str(e)}"
        return new_entries

    def select_topic_node(state: WorkflowState):
        """Node for topic selection (automated or user-prompted)."""
        logger.info("Running topic selection node...")
        new_entries: Dict[str, Any] = {
            "selected_topic": None,
            "user_approval_needed": True, # Indicate approval is needed for topic selection
            "user_approved_topic": False, # Default to false, will be updated if approved
            "error_message": None
        }
        if state["error_message"]: # Propagate error if research failed
            new_entries["error_message"] = state["error_message"]
            return new_entries

        if not state["topic_ideas"]:
            new_entries["error_message"] = "No topic ideas were generated. Cannot proceed."
            return new_entries

        try:
            # Simple selection: pick the first, or first matching criteria.
            # For automation, we can set user_approved_topic to True directly if no complex logic required.
            # Real implementation might involve user prompts via AskUserQuestion tool.
            selected = state["topic_ideas"][0] if state["topic_ideas"] else None
            if selected:
                new_entries["selected_topic"] = selected
                # For now, we'll assume auto-approval in the graph execution for testing purposes.
                # In a live session, this flag would be set by user interaction.
                # For a fully automated session, this would be a direct True assignment.
                new_entries["user_approved_topic"] = True # SIMPLIFIED: Auto-approve topic for now.
                logger.info(f"Selected topic: {selected.get('title', 'N/A')}")
            else:
                new_entries["error_message"] = "Failed to select a topic from ideas."
        except Exception as e:
            logger.error(f"Error selecting topic: {e}")
            new_entries["error_message"] = f"Topic selection failed: {str(e)}"
        return new_entries

    def generate_script_node(state: WorkflowState):
        """Node for script generation."""
        logger.info("Running script generation node...")
        new_entries: Dict[str, Any] = {
            "script_content": None,
            "user_approval_needed": True, # Script generation requires approval
            "user_approved_script": True, # Auto-approve script for automated workflow
            "error_message": None
        }
        if not script_gen_agent_instance:
             new_entries["error_message"] = "Script Generation Agent not initialized."
             return new_entries
        if not state["selected_topic"]:
            new_entries["error_message"] = "No topic selected for script generation."
            return new_entries

        try:
            script = script_gen_agent_instance.run(topic_data=state["selected_topic"])
            new_entries["script_content"] = script
            logger.info(f"Script generated for topic: {state['selected_topic'].get('title', 'N/A')}")
        except Exception as e:
            logger.error(f"Error in script generation agent: {e}")
            new_entries["error_message"] = f"Script generation failed: {str(e)}"
        return new_entries

    def generate_audio_node(state: WorkflowState):
        """Node for audio generation."""
        logger.info("Running audio generation node...")
        new_entries: Dict[str, Any] = {"audio_file_path": None, "error_message": None}
        if not audio_gen_agent_instance:
            new_entries["error_message"] = "Audio Generation Agent not initialized."
            return new_entries
        if not state["script_content"]:
            new_entries["error_message"] = "No script content available for audio generation."
            return new_entries

        try:
            audio_path = audio_gen_agent_instance.run(script_data=state["script_content"])
            new_entries["audio_file_path"] = audio_path
            logger.info(f"Audio generated and saved to: {audio_path}")
        except Exception as e:
            logger.error(f"Error in audio generation agent: {e}")
            new_entries["error_message"] = f"Audio generation failed: {str(e)}"
        return new_entries

    def generate_video_node(state: WorkflowState):
        """Node for video generation."""
        logger.info("Running video generation node...")
        new_entries: Dict[str, Any] = {"video_file_path": None, "error_message": None}
        if not video_gen_agent_instance:
             new_entries["error_message"] = "Video Generation Agent not initialized."
             return new_entries
        if not state["audio_file_path"] or not state["script_content"] or not state["selected_topic"]:
            new_entries["error_message"] = "Audio file path, script content, or selected topic missing for video generation."
            return new_entries

        try:
            video_path = video_gen_agent_instance.run(
                audio_path=state["audio_file_path"],
                script_data=state["script_content"],
                topic_data=state["selected_topic"]
            )
            new_entries["video_file_path"] = video_path
            logger.info(f"Video generated and saved to: {video_path}")
        except Exception as e:
            logger.error(f"Error in video generation agent: {e}")
            new_entries["error_message"] = f"Video generation failed: {str(e)}"
        return new_entries

    def publish_video_node(state: WorkflowState):
        """Node for publishing the video to YouTube."""
        logger.info("Running publish video node...")
        new_entries: Dict[str, Any] = {"youtube_url": None, "is_video_published": False, "error_message": None}
        if not publishing_agent_instance:
            new_entries["error_message"] = "Publishing Agent not initialized."
            return new_entries
        if not state["video_file_path"] or not state["selected_topic"]:
            new_entries["error_message"] = "Video file path or topic data missing for publishing."
            return new_entries

        try:
            topic_info = state["selected_topic"]
            video_title = topic_info.get("title", "Automated YouTube Video")
            video_description = topic_info.get("description", "Generated via automated YouTube channel project.")
            video_tags = topic_info.get("tags", [topic_info.get("title", "AI")])

            youtube_url = publishing_agent_instance.run(
                video_path=state["video_file_path"],
                title=video_title,
                description=video_description,
                tags=video_tags
            )
            if youtube_url:
                new_entries["youtube_url"] = youtube_url
                new_entries["is_video_published"] = True
                logger.info(f"Video published successfully: {youtube_url}")
            else:
                new_entries["error_message"] = "Publishing agent returned no URL, indicating failure."
                logger.warning("Publishing agent returned no URL.")
        except Exception as e:
            logger.error(f"An error occurred during YouTube video upload: {e}")
            new_entries["error_message"] = f"Video publishing failed: {str(e)}"
        return new_entries

    def cleanup_node(state: WorkflowState):
        """
        Node for cleaning up temporary files and directories.
        This node must handle cleanup robustly, even if previous steps failed.
        """
        logger.info("Running cleanup node...")
        new_entries: Dict[str, Any] = {}
        fm = file_management_instance # Use the already initialized FileManagement instance

        if not fm:
            logger.error("FileManagement instance not available for cleanup.")
            if not state["error_message"]: # Only set error if not already reported
                new_entries["error_message"] = "FileManagement not available for cleanup."
            return new_entries

        logger.info("Performing cleanup of temporary files and directories...")

        # Collect paths to potentially clean up.
        # These are artifacts that might have been created and are no longer needed.
        # This list should be comprehensive based on what agents might create.
        paths_to_potentially_clean = [
            state.get("audio_file_path"),
            state.get("video_file_path"),
            # Add any temporary directories explicitly created by agents, e.g., from video_generation agent
            # The video_generation agent cleans its own temp_media_dir internally during run.
            # If other temp dirs are created (e.g., for intermediate script saving not in data dir), add them here.
        ]

        # Also, consider cleaning up any standard temp directories created by FileManagement,
        # but only if they appear to be temporary (e.g., prefixed with 'mock_temp_').
        # A more advanced cleanup agent could manage temp files based on timestamps or tags.

        cleaned_items = []
        failed_items = []

        for path in paths_to_potentially_clean:
            if path and os.path.exists(path):
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                        logger.info(f"Cleaned up temporary file: {path}")
                        cleaned_items.append(path)
                    except OSError as e:
                        logger.error(f"Error removing temporary file {path}: {e}")
                        failed_items.append(path)
                elif os.path.isdir(path): # If path points to a directory
                    if fm.cleanup_directory(path):
                       logger.info(f"Cleaned up temporary directory: {path}")
                       cleaned_items.append(path)
                    else:
                       logger.error(f"Failed to clean up temporary directory: {path}")
                       failed_items.append(path)

        # Log summary of cleanup
        if cleaned_items:
            logger.info(f"Successfully cleaned up {len(cleaned_items)} temporary items.")
        if failed_items:
            if not state["error_message"]: # Only add error if not already present
                new_entries["error_message"] = f"Cleanup encountered errors for {len(failed_items)} items."
            logger.error(f"Cleanup failed for {len(failed_items)} items.")
        else:
            logger.info("Cleanup node completed.")

        return new_entries

    # --- Register Nodes in the Graph ---
    workflow.add_node("research_topics", research_topics_node)
    workflow.add_node("select_topic", select_topic_node)
    workflow.add_node("generate_script", generate_script_node)
    workflow.add_node("generate_audio", generate_audio_node)
    workflow.add_node("generate_video", generate_video_node)
    workflow.add_node("publish_video", publish_video_node)
    workflow.add_node("cleanup", cleanup_node)

    # --- Define Edges and Conditional Logic ---

    # Start with topic research
    workflow.set_entry_point("research_topics")

    # Research topics -> Select topic
    workflow.add_edge("research_topics", "select_topic")

    # Conditional transition after topic selection
    def route_after_topic_selection(state: WorkflowState):
        if state["error_message"]:
            logger.debug("Routing to handle_error due to error after topic selection node.")
            return "handle_error"
        # Check if topic was selected and approved (simulated as True for auto-flow)
        if state.get("selected_topic", None) and state.get("user_approved_topic", False):
            logger.debug("Routing to generate_script after topic selection (approved).")
            return "generate_script"
        else:
            # This path handles cases where topic selection failed, or user_approved_topic is False
            logger.debug("Routing to handle_error due to no approved topic selected.")
            # If error_message is already set from previous step, it will be propagated by handle_error_node.
            if not state["error_message"]: # Set a generic error if none was explicitly set.
                new_error_msg = "Topic selected but not approved, or selection failed."
                state["error_message"] = new_error_msg
                logger.warning(new_error_msg)
            return "handle_error"
    workflow.add_conditional_edges("select_topic", route_after_topic_selection, {
        "generate_script": "generate_script",
        "handle_error": "handle_error"
    })

    # Script generation -> Audio generation
    def route_after_script_generation(state: WorkflowState):
        if state["error_message"]:
            logger.debug("Routing to handle_error due to error after script generation node.")
            return "handle_error"

        # Script generation requires approval. Check if it was approved.
        # If user_approval_needed is true, user_approved_script must also be true to proceed.
        # In an automated flow, user_approved_script is set directly.
        if state.get("user_approval_needed", True) and not state.get("user_approved_script", False):
            logger.debug("Routing to handle_error: Script not approved.")
            if not state["error_message"]: # Set a specific error if none reported by agent
                new_error_msg = "Script generated but not approved by user. Workflow halted."
                state["error_message"] = new_error_msg
                logger.warning(new_error_msg)
            return "handle_error"
        else:
            # Proceed to audio generation if script is approved or approval was not needed (unlikely for script).
            logger.debug("Routing to generate_audio after script generation (approved).")
            return "generate_audio"
    workflow.add_conditional_edges("generate_script", route_after_script_generation, {
        "generate_audio": "generate_audio",
        "handle_error": "handle_error"
    })

    # Audio generation -> Video generation
    # This is a direct progression, assuming audio generation succeeds if no error.
    workflow.add_edge("generate_audio", "generate_video")

    # Video generation -> Publish video
    workflow.add_edge("generate_video", "publish_video")

    # Publish video -> Cleanup
    # The cleanup node should always run, regardless of success or failure of publishing.
    def route_after_publish(state: WorkflowState):
        logger.debug("Routing to cleanup after publish video node.")
        return "cleanup"
    workflow.add_edge("publish_video", "cleanup")

    # After cleanup, decide whether to end successfully or via error path.
    def route_after_cleanup(state: WorkflowState):
        # Check for any errors recorded during the workflow.
        if state.get("error_message"):
            logger.debug(f"Routing to handle_error after cleanup due to recorded error: {state['error_message']}")
            return "handle_error"
        # Check if the video was successfully published.
        elif state.get("is_video_published", False) and state.get("youtube_url"):
            logger.debug("Routing to success END after cleanup.")
            return "success_end" # Special label to transition to END
        else:
            # This branch covers cases where no explicit error message was set,
            # but the final goal (publishing) was not achieved.
            logger.debug("Routing to handle_error after cleanup due to no published video and no explicit error.")
            if not state["error_message"]: # Set a generic error if none exists
                new_error_msg = "Workflow completed, but video was not successfully published."
                state["error_message"] = new_error_msg
                logger.warning(new_error_msg)
            return "handle_error"
    workflow.add_conditional_edges("cleanup", route_after_cleanup, {
        "success_end": END, # Marks successful end of the workflow
        "handle_error": "handle_error"
    })

    # --- Error Handling Node ---
    def handle_error_node(state: WorkflowState):
        """Node to report final errors and terminate the workflow."""
        error_msg = state.get("error_message", "An unknown error occurred during workflow execution.")
        logger.error(f"Workflow terminated with UNHANDLED ERROR: {error_msg}")

        # Ensure state reflects failure and clear potentially successful partial outputs if workflow failed.
        return {
            "error_message": error_msg,
            "is_video_published": False,
            "youtube_url": None,
            # Explicitly clear states that indicate successful completion of subsequent steps
            "selected_topic": None, # Clear topic if publishing failed
            "script_content": None,
            "audio_file_path": None,
            "video_file_path": None,
        }

    workflow.add_node("handle_error", handle_error_node)
    # 'success_end' is a label that maps to the END state in the conditional edges.

    # Compile the workflow graph
    compiled_workflow = workflow.compile()
    logger.info("YouTube automation workflow graph compiled successfully.")
    return compiled_workflow

# Ensure logging is configured if this script is run directly
if __name__ == "__main__" and not logging.getLogger('').handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Logging configured for graph module.")

# Example of how to run the workflow (typically from src/main.py)
if __name__ == "__main__":
    logger.info("Testing AudioGenerationAgent...") # Corrected logging test call

    # --- Mock Setup for Testing ---
    # This section is for testing the graph structure and transitions using mock components.
    # It will not create actual files or make real API calls.

    # --- Mock Agent Implementations ---
    # These mocks simulate the behavior of the agents and return predefined values
    # or simulate success/failure for testing graph logic.

    # Mock Topic Research Agent
    class MockTopicResearchAgent:
        def __init__(self, youtube_client, **kwargs): logger.info("MockTopicResearchAgent initialized.")
        def run(self, niche):
            logger.info(f"Mock Research: Running for niche '{niche}'")
            if "AI" in niche:
                return [{"title": "AI in Education Trends", "description": "Latest trends...", "tags": ["AI", "Education", "Trends"]}]
            return []
    # Temporarily replace actual import with mock for this test
    # NOTE: In a real scenario, this would be handled by patching/dependency injection.
    # For this self-contained test, we can redefine the agent class directly.
    TopicResearchAgent = MockTopicResearchAgent # Override imported class

    # Mock Script Generation Agent
    class MockScriptGenerationAgent:
        def __init__(self, llm_client, file_management, **kwargs): logger.info("MockScriptGenerationAgent initialized.")
        def run(self, topic_data):
            logger.info(f"Mock Script Gen: For topic '{topic_data['title']}'")
            return {"title": topic_data["title"], "hook": "...", "introduction": "Intro...", "body": "Body...", "call_to_action": "CTA...", "outro": "Outro...", "tags": topic_data.get("tags", []), "description": "Mock script generated."}
    ScriptGenerationAgent = MockScriptGenerationAgent

    # Mock Audio Generation Agent
    class MockAudioGenerationAgent:
        def __init__(self, tts_client, file_management, **kwargs): logger.info("MockAudioGenerationAgent initialized.")
        def run(self, script_data):
            logger.info(f"Mock Audio Gen: For script '{script_data['title']}'")
            # Simulate creating an audio file path
            fm = FileManagement()
            temp_dir = fm.create_temp_dir("audio_gen_mock")
            audio_path = fm.save_content_to_file(b"dummy audio data", "output.mp3", directory=os.path.basename(temp_dir))
            return audio_path
    AudioGenerationAgent = MockAudioGenerationAgent

    # Mock Video Generation Agent
    class MockVideoGenerationAgent:
        def __init__(self, stock_media_client, file_management, **kwargs): logger.info("MockVideoGenerationAgent initialized.")
        def run(self, audio_path, script_data, topic_data):
            logger.info(f"Mock Video Gen: Using audio '{audio_path}' for topic '{topic_data['title']}'")
            # Simulate creating a video file path
            fm = FileManagement()
            temp_dir = fm.create_temp_dir("video_gen_mock")
            video_path = fm.save_content_to_file(b"dummy video data", "output.mp4", directory=os.path.basename(temp_dir))
            return video_path
    VideoGenerationAgent = MockVideoGenerationAgent

    # Mock Publishing Agent
    class MockPublishingAgent:
        def __init__(self, youtube_client, file_management, **kwargs): logger.info("MockPublishingAgent initialized.")
        def run(self, video_path, title, description, tags):
            logger.info(f"Mock Publish: Uploading video '{video_path}'")
            return f"https://www.youtube.com/watch?v=mock_youtube_id_{os.urandom(4).hex()}"
    PublishingAgent = MockPublishingAgent

    # --- Mocking Utility Clients ---
    # These mocks ensure the get_* functions return valid, mockable objects.
    class MockYouTubeApiClient:
        def __init__(self): logger.info("MockYouTubeApiClient initialized.")
        def search_videos(self, query, max_results): return [{"title": "Mock AI Video Search", "id": "mockid1", "channel_title": "Mock Channel", "published_at": "2023-01-01"}]
        def upload_video(self, video_path, title, description, tags): return f"https://www.youtube.com/watch?v=mock_upload_id_{os.urandom(4).hex()}"
    def get_youtube_client(): return MockYouTubeApiClient()

    class MockTtsClient:
        def synthesize(self, text, output_filename):
            logger.info(f"Mock TTS synthesize: '{text[:50]}...' to {output_filename}")
            with open(output_filename, "wb") as f: f.write(b"dummy audio data")
            return output_filename
    def get_tts_client(): return MockTtsClient()

    class MockStockMediaClient:
        def search(self, query, media_type, per_page):
            logger.info(f"Mock Stock Media search: '{query}' ({media_type})")
            return [{"url": f"http://mock.com/media/{query}.png", "sourceUrl": f"http://mock.com/media/{query}_original.png", "thumbnail": "...", "description": "..."}]
    def get_stock_media_client(): return MockStockMediaClient()

    class MockLLMClient:
        def generate_script(self, topic, tone, length, context):
            logger.info(f"Mock LLM generate script for topic: {topic}")
            return {"title": f"Mock Script: {topic}", "introduction": "Mock intro.", "body": "Mock body.", "outro": "Mock outro.", "tags": ["mock"], "description": "Mock desc."}
    def get_llm_client(): return MockLLMClient()

    # FileManagement mock is already defined above for agent initialization

    # --- Compile and Run Workflow ---
    logger.info("Compiling the YouTube automation workflow...")
    CompiledWorkflow = create_youtube_workflow()
    print("Workflow compiled. Simulating execution with mock data and agents...")

    # Initial state for a successful run simulation
    # Note: user_approved_topic and user_approved_script are set to True for automated testing.
    # In a real session requiring user interaction, these would be managed via AskUserQuestion.
    initial_state_simulation: WorkflowState = {
        "initial_input": {"niche": "AI Trends", "target_audience": "developers"},
        "topic_ideas": [],
        "selected_topic": None,
        "script_content": None,
        "audio_file_path": None,
        "video_file_path": None,
        "youtube_url": None,
        "error_message": None,
        "user_approval_needed": True, # Typically true for topic selection and script approval
        "user_approved_topic": True,   # Simulated auto-approval for topic
        "user_approved_script": True,  # Simulated auto-approval for script
        "is_video_published": False,
    }

    # Run the simulated workflow
    print("\n--- Starting workflow simulation ---")
    final_state = CompiledWorkflow.invoke(initial_state_simulation)

    print("\n--- Workflow Simulation Finished ---")
    print("Final State:")
    print(json.dumps(final_state, indent=2))

    if final_state.get("is_video_published") and final_state.get("youtube_url"):
        print(f"\nSimulated Video published successfully: {final_state['youtube_url']}")
    elif final_state.get("error_message"):
        print(f"\nSimulated Workflow ended with an error: {final_state['error_message']}")
    else:
        print("\nSimulated Workflow completed, but video was not published. Check state for details.")

    # --- Cleanup Mock Artifacts ---
    print("\nCleaning up mock artifacts...")
    # Clean up mock temp directories created by FileManagement mock
    if file_management_instance: # Check if it was initialized
        fm_mock_instance = file_management_instance # Use the instance created earlier
        temp_data_dir = os.path.join(fm_mock_instance.base_dir, 'data')
        if os.path.exists(temp_data_dir):
            for item in os.listdir(temp_data_dir):
                mock_item_path = os.path.join(temp_data_dir, item)
                if os.path.isdir(mock_item_path) and item.startswith("mock_temp_"):
                    try:
                        shutil.rmtree(mock_item_path)
                        logger.info(f"Cleaned up mock temp dir: {mock_item_path}")
                    except OSError as e:
                        logger.error(f"Error cleaning up mock temp dir {mock_item_path}: {e}")
    print("Mock artifact cleanup finished.")
