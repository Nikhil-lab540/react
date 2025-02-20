import os
import autogen
from typing_extensions import Annotated, Union
import re
from typing import List, Tuple
import subprocess
import json
from typing import Dict, List
from autogen import Agent

config_list = autogen.config_list_from_json(
    env_or_file=r"OAI_CONFIG_LIST.json"
)


llm_config = {
    "temperature": 0,
    "config_list": config_list,
}


AppRunner = autogen.AssistantAgent(
    name="AppRunner",
    llm_config=llm_config,
    system_message="""
    NOTE: This agent does not generate code.
    After Project-Code files got Successfully Saved by Admin. It Run React application using the following command: npm start.
    It always suggest function to execute by Admin.
    This Agent AppRunner, has to suggest function to Admin everytime, if the resposne from last_speaker having npm start in the response.
    ***It always suggest function to execute by Admin.
    """,
    description="""
    NOTE: This agent does not generate code.
    This AppRunner will runs next after, 'Project_Code_Generator' and 'Engineer'.
    After files got Successfully Saved. It Run React application using the following command: npm start.
    It always suggest function to execute by Admin.
    This Agent AppRunner, has to suggest function to Admin everytime, if the resposne from last_speaker having npm start in the response.
    ***It always suggest function to execute by Admin.
    """,
)


engineer = autogen.AssistantAgent(
    name="Engineer",
    llm_config=llm_config,
    system_message="""
    NOTE: This agent does not generate code.
    It always suggest function to execute by Admin.
    This Agent Engineer, has to suggest function to Admin everytime, if the resposne from last_speaker having filename: in the response.
    ***It always suggest function to execute by Admin.
    """,
    description="""
    NOTE: This agent does not generate code.It always suggest function to execute by Admin.
    Eachtime at his turn it has to save code everytime if the resposne from last_speaker having filename: in the response.
    This Agent Engineer, everytime saves the code, if the last_speaker response having code.
    It always suggest function to execute by Admin.
     """,
)

Project_Code_Generator = autogen.AssistantAgent(
    name="Project_Code_Generator",
    llm_config=llm_config,
    system_message="""
    Always generate project code in multiple code blocks, put # filename: <filename with file-address> in the first line inside each code block.
    """,
    description="""This Agent generates project code in multiple code blocks after receiving user input from Admin.""",
)

user_proxy = autogen.UserProxyAgent(
    name="Admin",
    human_input_mode="ALWAYS",
    code_execution_config=False,
    system_message="""
    You take the user input and assign agents for it. Assign Agent: 'Project_Code_Generator' to generate code,
    and after 'Project_Code_Generator' generates the project code, always assign Agent: 'Engineer'.
    Suggest tool 'save_code_blocks' to Engineer so that Engineer can modify & save the code generated by Admin.""",
    description=""" This Agent assigns 'Project_Code_Generator' to generate code and, after the project code is generated, assigns 'Engineer' and suggests the function 'save_code_blocks' to Engineer to save the generated code.
    After 'Project_Code_Generator' and 'Engineer', It has to initiate AppRuner and its function to start the Project by: npm start.
    """,
)


speaker_selection = {
    user_proxy: [Project_Code_Generator],
    Project_Code_Generator: [engineer],
    engineer: [AppRunner],
    AppRunner: [AppRunner, user_proxy],
    user_proxy: [],

      # Allow AppRunner to return to user_proxy after running
}


groupchat = autogen.GroupChat(
    agents=[engineer, user_proxy, Project_Code_Generator, AppRunner],
    messages=[],
    max_round=500,
    allowed_or_disallowed_speaker_transitions=speaker_selection,
    speaker_transitions_type="allowed",
)


manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

default_path = "D:/react-app/new-folder11/"  # Using raw string for Windows path
default_path1 = "D:/react-app/"  # Using raw string for Windows path

# Dependency check and installation logic
workdir = os.path.join(default_path1, "new-folder11")
os.makedirs(workdir, exist_ok=True)


def check_dependencies():
    """Check if package.json exists and all dependencies are installed."""
    package_json_path = os.path.join(workdir, "package.json")
    node_modules_path = os.path.join(workdir, "node_modules")

    if not os.path.exists(package_json_path):
        return False

    if not os.path.exists(node_modules_path):
        return False

    try:
        # Read package.json
        with open(package_json_path, 'r') as f:
            package_data = json.load(f)

        # Check if all dependencies are installed
        for dep_type in ['dependencies', 'devDependencies']:
            if dep_type in package_data:
                for dep in package_data[dep_type]:
                    dep_path = os.path.join(node_modules_path, dep)
                    if not os.path.exists(dep_path):
                        return False
        return True
    except Exception as e:
        print(f"Error checking dependencies: {e}")
        return False


def install_missing_dependencies():
    """Install only missing dependencies."""
    try:
        package_json_path = os.path.join(workdir, "package.json")
        if not os.path.exists(package_json_path):
            print("Installing base React application...")
            subprocess.run(
                "npx create-react-app .",  # Create a React app first
                shell=True,
                cwd=workdir,
                check=True
            )

        # After React setup, now set up Vite
        print("Setting up Vite for the project...")
        subprocess.run(
            "npm install vite @vitejs/plugin-react",  # Install Vite and React plugin for Vite
            shell=True,
            cwd=workdir,
            check=True
        )

        print("Vite setup complete.")

        # Check node_modules
        if not os.path.exists(os.path.join(workdir, "node_modules")):
            print("Installing dependencies...")
            subprocess.run(
                "npm install",
                shell=True,
                cwd=workdir,
                check=True
            )
        else:
            print("Dependencies already installed, skipping installation.")

        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False


@user_proxy.register_for_execution()
@AppRunner.register_for_llm(
    description="Run React application using the following command: 'npm start'. This will start the development server Application running in the browser.")
def run_app() -> Tuple[int, str]:
    """
    Run the app using npm start in the default path and wait for the compilation process to finish.
   
    Returns:
        Tuple[int, str]: Status code and message
    """
    try:
        # Start the npm process
        process = subprocess.Popen(
            ["npm", "start"],
            cwd=default_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )

        # Collect output in real-time
        output_lines = []
        while True:
            output_line = process.stdout.readline()
            if output_line == "" and process.poll() is not None:
                break  # Exit the loop when the process ends

            if output_line:
                output_lines.append(output_line.strip())
                print(output_line.strip())  # Optional: Print the output to console/logs

                # Check for "webpack compiled successfully"
                if "webpack compiled successfully" in output_line.lower():
                    process.terminate()  # Optionally terminate process to clean up
                    return 0, "App started and compiled successfully. Ready for use."

        # If the process exits without finding the success message
        return 1, "App terminated before completing compilation. Output:\n" + "\n".join(output_lines)
   
    except Exception as e:
        return 1, f"Error while trying to run the app: {str(e)}"
   

@user_proxy.register_for_execution()
@engineer.register_for_llm(description="save code everytime, if it has filename: in the response.")
def save_code_blocks() -> Tuple[int, str]:
    """
    Save code blocks from group chat messages to their respective files.

    Returns:
        Tuple[int, str]: Status code and message.
    """
    try:
        # Pattern to match code blocks
        code_block_pattern = r'[\w-]*\n(.*?)'
        saved_files = []

        for msg in groupchat.messages:
            content = msg.get('content', '').strip()
            if not content:
                continue

            code_blocks = re.finditer(code_block_pattern, content, re.DOTALL)

            for block in code_blocks:
                code = block.group(1)
                if not code.strip():
                    continue

                # Look for filename in the first line
                filename_match = re.search(r'filename:\s*([\w/.-]+)', code.split('\n')[0])
                if filename_match:
                    filename = filename_match.group(1).strip()
                    code = '\n'.join(code.split('\n')[1:]).strip()

                    # Skip if filename includes restricted paths (e.g., node_modules)
                    if 'node_modules' in filename:
                        continue

                    # Create directories if needed
                    full_path = os.path.join(default_path, filename)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)

                    # Save the code block to the file
                    with open(full_path, "w", encoding="utf-8") as file:
                        file.write(code + "\n")
                    saved_files.append(filename)

        if saved_files:
            return 0, f"Successfully saved files: {', '.join(saved_files)}"
        else:
            return 1, "No valid code blocks found in messages to save."

    except Exception as e:
        return 1, f"Error processing messages: {str(e)}"




# Example usage
if not check_dependencies():
    if not install_missing_dependencies():
        print("Failed to set up React environment.")
    else:
        print("React environment setup complete.")
else:
    print("All dependencies are already installed.")

chat_result = user_proxy.initiate_chat(
    manager,
    message="""
    Give the simple project code of a colorful dashboard in React.js along with its package.json code.
    """,
)