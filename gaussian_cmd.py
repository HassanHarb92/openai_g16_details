import sys
import re
import json
import openai
from openai import AssistantEventHandler, OpenAI
from typing_extensions import override

# Initialize the OpenAI client
#client = OpenAI(api_key="your-openai-api-key")
client = OpenAI()
# Create the assistant
assistant = client.beta.assistants.create(
    name="Gaussian Command Assistant",
    instructions="You are an expert in computational chemistry. Explain each Gaussian command keyword.",
    model="gpt-4o",
    tools=[{"type": "file_search"}],
)

# Function to read the .log file
def read_log_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return content

# Function to extract Gaussian commands
def extract_gaussian_commands(content):
    # Find the line that starts with " #"
    command_start = re.search(r'^ #p.*', content, re.MULTILINE)
    if not command_start:
        return None

    # Find the first line with ---- after the command_start
    commands = []
    lines = content[command_start.start():].splitlines()
    for line in lines:
        if line.strip().startswith(' ------'):
            break
        commands.append(line.strip())

    # Combine commands into a single line
    combined_commands = ' '.join(commands)
    return combined_commands

# Create a class for handling OpenAI events
class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    @override
    def on_message_done(self, message) -> None:
        # Print a citation to the file searched
        message_content = message.content[0].text
        annotations = message_content.annotations
        citations = []
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(
                annotation.text, f"[{index}]"
            )
            if file_citation := getattr(annotation, "file_citation", None):
                cited_file = client.files.retrieve(file_citation.file_id)
                citations.append(f"[{index}] {cited_file.filename}")

        print(message_content.value)
        print("\n".join(citations))

# Main function
def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <path_to_log_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    content = read_log_file(file_path)
    commands = extract_gaussian_commands(content)

    if commands:
        print("Gaussian Commands Found:")
        print(commands)

        # Split the commands into individual keywords
        keywords = re.split(r'\s+', commands)

        # Use OpenAI to get explanations for each keyword
        explanations = {}
        for keyword in keywords:
            response = client.Completion.create(
                engine="davinci",
                prompt=f"Explain the following Gaussian command keyword: {keyword}",
                max_tokens=150
            )
            explanation = response.choices[0].text.strip()
            explanations[keyword] = explanation

        # Create JSON output
        output = {
            "commands": commands,
            "explanations": explanations
        }

        output_json = json.dumps(output, indent=4)
        print("\nJSON Output:")
        print(output_json)

        # Create a thread and attach the file to the message
        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": "Explain the Gaussian command keywords.",
                    "attachments": [
                        {"file_id": client.files.create(file=open(file_path, "rb"), purpose="assistants").id, "tools": [{"type": "file_search"}]}
                    ],
                }
            ]
        )

        # Use the stream SDK helper with the EventHandler class to create the run and stream the response
        with client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=assistant.id,
            instructions="Please address the user as Jane Doe. The user has a premium account.",
            event_handler=EventHandler(),
        ) as stream:
            stream.until_done()

    else:
        print("No Gaussian commands found in the specified file.")

if __name__ == "__main__":
    main()

