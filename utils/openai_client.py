from fastapi import  HTTPException
from openai import OpenAI
import logging
import os

# Initialize OpenAI client
openai_model = os.getenv("OPENAI_MODEL", "gpt-4")
openai_api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=openai_api_key)
def create_openai_chat(messages):
    try:
        response = client.chat.completions.create(
            model=openai_model,
            messages=messages,
            temperature=0.5,
            max_tokens=2000,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        logging.info("Successful response from OpenAI")
        return response
    except Exception as e:
        logging.error("OpenAI API call failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OpenAI API call failed: {str(e)}")
