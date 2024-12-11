import subprocess
import os
import streamlit as st
from crewai import LLM, Agent, Task, Crew
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define a ShellCommandTool to execute shell commands
class ShellCommandTool:
    def __init__(self, working_dir="."):
        self.working_dir = working_dir

    def run_command(self, command):
        """Run a shell command in the specified working directory."""
        try:
            os.makedirs(self.working_dir, exist_ok=True)
            result = subprocess.run(command, shell=True, cwd=self.working_dir, capture_output=True, text=True)
            return result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return f"Error executing command: {e}"

# Function to check if the React app is already set up
def check_node_modules(project_path):
    """Check if node_modules exists, indicating the React app setup is complete."""
    return os.path.exists(os.path.join(project_path, "node_modules"))

# Function to analyze a flowchart image and generate React code
def generate_code_from_flowchart(flowchart_image):
    """Generate website code based on the uploaded flowchart."""
    prompt = """
    You are an expert React developer. Analyze the provided flowchart and generate a complete React application using **pure inline CSS**. The application should:
1. **Exclude External CSS**: Do not use any CSS classes or external CSS files.
2. **Use Inline Styles Only**: All styles must be defined as JavaScript objects and applied using the `style` attribute in the JSX.
3. **Modular and Maintainable Structure**: Reflect the flowchart's hierarchy and relationships in the code.
4. **Clean and Readable Code**: Write well-formatted and commented code.

Example output:

```javascript
import React from 'react';

function App() {
    // Define styles as JavaScript objects
    const containerStyles = {
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '20px',
        backgroundColor: '#f0f0f0',
    };

    const buttonStyles = {
        padding: '10px 20px',
        border: 'none',
        borderRadius: '5px',
        cursor: 'pointer',
        backgroundColor: '#007BFF',
        color: 'white',
        fontSize: '1rem',
    };

    const imageStyles = {
        width: '100%',
        height: '200px',
        borderRadius: '10px',
        objectFit: 'cover',
        padding: '10px',
    };

    return (
        <div style={containerStyles}>
            <button style={buttonStyles}>Click Me!</button>
            <img src="https://picsum.photos/200/300" alt="Sample" style={imageStyles} />
        </div>
    );
}

export default App;

    ```
    Return the generated code enclosed in triple backticks (```javascript).
    """
    task = Task(
        description="Generate React application code with inline CSS styles from the flowchart.",
        expected_output="React application code with logic and styling.",
        agent=app_code_generator,
        image=flowchart_image,
        prompt=prompt
    )

    # Execute the task with Crew
    crew = Crew(agents=[app_code_generator], tasks=[task], verbose=True)
    crew.kickoff(inputs={})

    # Extract code from the task output
    generated_code = extract_code_from_output(str(task.output.raw)) if task.output else None
    return generated_code

# Function to extract the code block from agent output
def extract_code_from_output(agent_output):
    """Extract code between triple backticks (` ```javascript `)."""
    start_idx = agent_output.find("```javascript")
    if start_idx == -1:  # Try locating other code delimiters if not found
        start_idx = agent_output.find("```")
    end_idx = agent_output.rfind("```")
    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        return agent_output[start_idx + len("```javascript"):end_idx].strip()
    return "No valid code block found."

# Function to update App.js with generated code
def update_app_js_with_generated_code(project_path, generated_code):
    app_js_path = os.path.join(project_path, 'src', 'App.js')
    try:
        with open(app_js_path, 'w') as file:
            file.write(generated_code)
        return "App.js updated successfully with generated code."
    except Exception as e:
        return f"Error updating App.js: {e}"

# Initialize ShellCommandTool
project_path = st.text_input("Enter the path for the new React project:", "D:/my-react-app")
shell_tool = ShellCommandTool(working_dir=project_path)

# Initialize LLM
llm = LLM(
    model="groq/llama-3.2-11b-vision-preview",
    api_key=os.getenv("GROQ_API_KEY")
)

# Define Application Code Generator Agent
app_code_generator = Agent(
    role="Application Code Generator",
    goal="Generate React applications with inline CSS from flowcharts.",
    backstory="This agent generates complete React applications by analyzing flowcharts and producing components with inline styles.",
    llm=llm,
    verbose=True
)

# Streamlit UI
st.title("Dynamic React Application Generator")

# File upload for flowchart
uploaded_file = st.file_uploader("Upload a flowchart image (PNG, JPG, etc.):", type=["png", "jpg", "jpeg"])

if st.button("Generate and Add Application"):
    if uploaded_file:
        st.write("Analyzing the uploaded flowchart...")
        flowchart_image = Image.open(BytesIO(uploaded_file.read()))

        # Generate React code from the flowchart
        generated_code = generate_code_from_flowchart(flowchart_image)

        if generated_code:
            st.success("Code generated successfully!")
            st.code(generated_code)

            # Set up React project if not already initialized
            if not check_node_modules(project_path):
                st.write("Setting up React app structure...")
                react_app_output = shell_tool.run_command("npx create-react-app .")
                st.code(react_app_output)

                st.write("Installing dependencies...")
                install_output = shell_tool.run_command("npm install web-vitals")
                st.code(install_output)

            # Update App.js with the generated code
            st.write("Updating App.js with the generated code...")
            update_status = update_app_js_with_generated_code(project_path, generated_code)
            st.success(update_status)

            # Start the React development server
            st.write("Starting the React development server...")
            server_output = shell_tool.run_command("npm start")
            st.code(server_output)
            st.components.v1.iframe("http://localhost:3000", width=800, height=600)
        else:
            st.error("Failed to generate code. Please try again with a clearer flowchart.")
    else:
        st.error("Please upload a flowchart to proceed.")

