import random
import os
import google.generativeai as genai
import alpha_algorithm_petri_net

# Correctly set the API key in the environment variable
os.environ['API_KEY'] = 'AIzaSyDoWYB677EqkwGir6SWIUNb3O0JZHxA_rA'

# Noor' API key:
# os.environ['API_KEY'] = 'AIzaSyDoWYB677EqkwGir6SWIUNb3O0JZHxA_rA'

# Retrieve the API key from the environment variable
api_key = os.getenv('API_KEY')  # Retrieve the value of 'API_KEY'

# Ensure the API key is retrieved
if not api_key:
    raise ValueError("API_KEY is not set or is empty.")

# Configure the API with the retrieved API key
genai.configure(api_key=api_key)

# Check the API key
print("API Key:", api_key)

# Input values for number of traces, noise level, uncommon path frequency, and missing event chance
num_traces = int(input("Enter the number of traces: "))
noise_level = float(input("Enter the noise level (e.g., 0.1 for 10%): "))
uncommon_path_freq = float(input("Enter the frequency of uncommon paths (e.g., 0.05 for 5%): "))
missing_event_chance = float(input("Enter the likelihood of missing events (e.g., 0.1 for 10%): "))
test_traces = num_traces / 2

# Read the process description from a file
process_description_file = input("Enter the path to the process description file: ")

try:
    with open(process_description_file, 'r') as file:
        process_description = file.read()
    print("Process Description Read Successfully:")
    print(process_description)
except FileNotFoundError:
    print(f"Error: The file '{process_description_file}' was not found.")
    exit()

# Create a GenerativeModel object
model = genai.GenerativeModel("gemini-1.5-flash")

# Updated prompt with input parameters for trace generation
response = model.generate_content(f"""
Generate an event log based on the following process description:
- Identify and assign a unique alphabet 'A' to each unique task.
- For noise events use : 'X', 'Y' (random noise, irrelevant to the process).
- The number of traces to generate: {num_traces}.
- The noise level (random, irrelevant events): {noise_level}.
- The frequency of uncommon paths: {uncommon_path_freq}.
- The likelihood of missing events in each trace: {missing_event_chance}.
- a missing event is a step skipped in a trace.
- Give just the event logs vertically.
- Give test traces that are different from the actual traces. 
- The number of test traces: {test_traces}.
- The event log should have actual traces, followed by test traces and then the process steps with headings for actual traces and test traces.
- The event log should be formatted like the following:
  ['B', 'C', 'D', 'E', 'C', 'D']
  ['A', 'B', 'C', 'D', 'E']
  ['A', 'B', 'C', 'D', 'A', 'B', 'C', 'D']
  ['A', 'B', 'C', 'E', 'A', 'B']
Process Description:
{process_description}
""")

# Check if the response is valid
if response and response.text:
    print("Event Log Generated:", response.text)

    # Write the event log to a file
    with open("event_log.txt", "w") as file:
        file.write(response.text)

    print("Event log has been written to event_log.txt.")
    
    # Call the alpha miner's main function
    #alpha_main()
else:
    print("Error: No event log was generated.")

alpha_algorithm_petri_net.main();



