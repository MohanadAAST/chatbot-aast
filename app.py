from time import sleep
from fastapi import FastAPI, HTTPException
import openai
import os
from dotenv import load_dotenv
from collections import deque

# Load environment variables
load_dotenv()

# OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# FastAPI app initialization
app = FastAPI()

# Global variables
emails_dict = {}
assistant_id = "asst_PLlCZlWaawUIhPUBdIFUXiJj"

# Initialize a cache
cache_size = 30
cache = deque(maxlen=cache_size)

# Function to add to cache
def add_to_cache(email, user_input, response):
    cache.append((email, user_input, response))

# Function to check cache
def check_cache(email, user_input):
    for item in cache:
        if item[0] == email and item[1] == user_input:
            return item[2]
    return None

# Endpoint to process message
@app.get("/process_message/")
async def process_message(email: str, user_input: str):
    # Check if response is already in cache
    cached_response = check_cache(email, user_input)
    if cached_response:
        return {"message": cached_response}

    # Process message if not in cache
    if email in emails_dict:
        thread_id = emails_dict[email]
    else:
        thread = openai.Client().beta.threads.create()
        thread_id = thread.id
        emails_dict[email] = thread_id

    message = openai.Client().beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_input
    )
    run = openai.Client().beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )
    
    # Polling loop to wait for the run to complete
    while True:
        run_status = openai.Client().beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
        print(f"Run status: {run_status.status}")
        if run_status.status == 'completed':
            break
        sleep(1)  # Wait for a second before checking again

    # Retrieve messages after the run is completed
    messages = openai.Client().beta.threads.messages.list(
        thread_id=thread_id
    )
    response_message = "No response found"  # Default response
    for msg in messages.data:
        if msg.role == "assistant":
            response_message = msg.content[0].text.value  # Adjust based on the actual structure
            break

    # Add response to cache
    add_to_cache(email, user_input, response_message)

    return {"message": response_message}
