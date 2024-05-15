import sys
import json
from openai import OpenAI

# Instantiate the OpenAI client
client = OpenAI()

def extract_gaussian_commands(filepath):
    """Extract Gaussian command line from the log file."""
    start = False
    command_line = ""
    with open(filepath, "r") as file:
        for line in file:
            if line.strip() == "----------------------------------------------------------------------":
                if start:
                    break
                start = True
            elif start:
                command_line += line.strip()
    return command_line


filepath = sys.argv[1]

command_line = extract_gaussian_commands(filepath)
print("Command line:", command_line)

# Open a file named 'cmd.txt' in write mode
with open('logs/cmd.txt', 'w') as file:
    # Write the contents of command_line to the file
    file.write(command_line)

