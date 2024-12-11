import os
import subprocess
import json
from typing import Tuple
from io import BytesIO
from PIL import Image
import streamlit as st
from crewai import LLM, Agent, Task, Crew
import autogen
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
project_path = "D:/reacts-app"  # Change this to your desired React project path

# AutoGen Configuration
llm_config = {
    "config_list": [
        {
            "api_type": "groq",
            "model": "mixtral-8x7b-32768",
            "api_key": os.getenv("GROQ_API_KEY"),
        }
    ],
}

Project_Code_Generator = autogen.AssistantAgent(
    name="Project_Code_Generator",
    llm_config=llm_config,
    system_message="""
    Always generate project code in multiple code blocks, put # filename: <filename with file-address> in the first line inside each code block.
    """,
    description="""This Agent generates project code in multiple code blocks after receiving user input.""",
)

groupchat = autogen.GroupChat(
    agents=[Project_Code_Generator],
    messages=[],
    max_round=500,
)

manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

# CrewAI Configuration
llm_vision = LLM(
    model="groq/llama-3.2-90b-vision-preview",
    api_key=os.getenv("GROQ_API_KEY"),
)

# Helper Classes
class ShellCommandTool:
    def __init__(self, working_dir="."):
        self.working_dir = working_dir

    def run_command(self, command):
        try:
            os.makedirs(self.working_dir, exist_ok=True)
            result = subprocess.run(command, shell=True, cwd=self.working_dir, capture_output=True, text=True)
            return result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return f"Error executing command: {e}"

# CrewAI Tasks
def extract_from_flowchart(image) -> str:
    """
    Extract text from a flowchart image using CrewAI.
    """
    vision_agent = Agent(
        role="Flowchart Analyzer",
        goal="Extract text from the uploaded flowchart image for generating React code.",
        backstory="summarizes the image given",
        llm=llm_vision,
    )
    task = Task(
        description="Analyze the flowchart image and summarize it.",
        agent=vision_agent,
        expected_output="Text",
        image=image,
    )
    crews = Crew(agents=[vision_agent], tasks=[task])
    result = crews.kickoff()
    return result.raw if result.raw else "Failed to analyze flowchart."

def initialize_react_project(project_path: str) -> str:
    """
    Initialize a React project if not already set up.
    """
    tool = ShellCommandTool(working_dir=project_path)
    return tool.run_command("npx create-react-app .")

def start_react_server(project_path: str) -> str:
    """
    Start the React development server.
    """
    tool = ShellCommandTool(working_dir=project_path)
    return tool.run_command("npm start")

def update_app_js(project_path: str, generated_code: str) -> str:
    """
    Update the `App.js` file with the generated React code.
    """
    app_js_path = os.path.join(project_path, "src", "App.js")
    try:
        with open(app_js_path, "w", encoding="utf-8") as file:
            file.write(generated_code)
        return "App.js updated successfully with generated code."
    except Exception as e:
        return f"Error updating App.js: {e}"

def generate_react_code(description: str) -> str:
    """
    Generate React code using AutoGen's Project_Code_Generator.
    """
    message = f"Generate a complete React app based on the following description:\n\n{description}"
    chat_result = manager.groupchat.agents[0].generate_reply([
        {"role": "user", "content": message}  # Include the "role" property
    ])
    return chat_result["content"] if "content" in chat_result else "Code generation failed."

# Streamlit UI
st.title("Dynamic React Application Generator")

# File upload for flowchart
uploaded_file = st.file_uploader("Upload a flowchart image (PNG, JPG, etc.):", type=["png", "jpg", "jpeg"])

if uploaded_file:
    st.write("Analyzing the uploaded flowchart...")

    # Step 1: Analyze flowchart with CrewAI
    flowchart_image = Image.open(BytesIO(uploaded_file.read()))
    extracted_text = extract_from_flowchart(flowchart_image)
    st.write("Extracted Text from Flowchart:")
    st.write(extracted_text)

    # Step 2: Generate React code with AutoGen
    if extracted_text:
        st.write("Generating React code from extracted text...")
        react_code = generate_react_code(extracted_text)
        st.write("Generated React Code:")
        st.code(react_code)

        # Step 3: Setup environment and run the server using CrewAI
        st.write("Setting up React environment...")
        init_output = initialize_react_project(project_path)
        st.code(init_output)

        st.write("Updating App.js with generated code...")
        update_status = update_app_js(project_path, react_code)
        st.success(update_status)

        st.write("Starting the React development server...")
        server_output = start_react_server(project_path)
        st.code(server_output)
        st.components.v1.iframe("http://localhost:3000", width=800, height=600)
    else:
        st.error("Failed to extract meaningful text from the uploaded flowchart.")

