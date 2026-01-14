from google import genai
from google.genai import types
from medguard.agent.schema import query_function_declaration, query_inventory
from dotenv import load_dotenv

load_dotenv()

# client and tool config

client = genai.Client()
tools = types.Tool(function_declarations=[query_function_declaration])
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

# if response.candidates[0].content.parts[0].function_call:
# function_call = response.candidates[0].content.parts[0].function_call
# print(f"Function to call: {function_call.name}")
# print(f"Arguments: {function_call.args}")
#  In a real app, you would call your function here:
#  result = query_inventory(**function_call.args)
# else:
# print("No function call found in the response.")
# print(response.text)

print(
    response.candidates[0].content.parts[0].function_call
)  # get functionCall obj from gemini
# id=None args={'facility_id': 'FAC_001', 'medication_id': 'MED_001'} name='query_inventory' partial_args=None will_continue=None


# parse response
tool_call = response.candidates[0].content.parts[0].function_call

if tool_call.name == "query_inventory":
    result = query_inventory(**tool_call.args)
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
