import os
from typing import List, Dict, Any
from google import genai
from google.genai import types
from dotenv import load_dotenv

from medguard.agent.registry import registry

import medguard.agent.tools

load_dotenv()

tools = registry.tools_list

client = genai.Client()
tools = registry.tools_list
config = types.GenerateContentConfig(tools=[tools])

# user prompt
contents = [
    types.Content(
        role="user",
        parts=[types.Part(text="Get the quantity of MED_001 at FAC_001")],
    )
]
# send request
response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=contents,
    config=config,
)

print(response.candidates[0].content.parts[0].function_call)

# parse response
tool_call = response.candidates[0].content.parts[0].function_call

if tool_call.name == "query_inventory":
    result = registry.execute(tool_call.name, dict(tool_call.args))
    # print(result)
    # {'facility_id': 'FAC_001', 'medication_id': 'MED_001', 'quantity': 471}

# create response back to user
function_response_part = types.Part.from_function_response(
    name=tool_call.name, response={"result": result}
)

# Append function call and result of the function execution to contents
contents.append(
    response.candidates[0].content
)  # Append the content from the model's response.
contents.append(
    types.Content(role="user", parts=[function_response_part])
)  # Append the function response

client = genai.Client()
final_response = client.models.generate_content(
    model="gemini-3-flash-preview",
    config=config,
    contents=contents,
)

print(final_response.text)
# The quantity of MED_001 at FAC_001 is 471.
