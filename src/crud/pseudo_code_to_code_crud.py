from ..database import get_db
from ..models.pseudo_code_to_code_models import *
from ..schemas.code_explainer_schemas import *
from fastapi import HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
import os 
import asyncio


load_dotenv()

GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
if not GOOGLE_GEMINI_API_KEY:
    raise ValueError("Unable to acquire the api key for the model")


gemini_api_client = genai.Client(
    api_key=GOOGLE_GEMINI_API_KEY
)


GEMINI_SYSTEM_INSTRUCTION = """
    You are a senior software engineer with 20 years experience.

    Take the provided pseudo code from the user and generate a working implementation of the code using python.

    Return the response ONLY in JSON format with the following structure:

    "pseudo_code": "original pseudo_code provided by user",
    "actual_code": "clear explanation of what the code does, why it works, and one alternative approach",
    "title": "generate a short, descriptive title that helps the user recognize the snippet later."

    Do not include any extra text outside the JSON.
"""


async def upload_pseudo_code_snippet(
    db: AsyncSession,
    snippet_data: CreatePseudoCodeToCodeSchema
):
    try:
        print("")
        
        actual_pseudo_snippet = snippet_data.pseudo_code
        
        response = await asyncio.to_thread(
            gemini_api_client.models.generate_content,
            model="gemini-2.5-flash",
            contents=f"Take the provided pseudo code and generate python code from this: \n\n {actual_pseudo_snippet}"
        )
        
    except Exception as e:
        print(f"There was an error trying to generate the code for this: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to generate the code requested")