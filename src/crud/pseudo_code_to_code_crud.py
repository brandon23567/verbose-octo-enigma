from ..database import get_db
from ..models.pseudo_code_to_code_models import *
from ..schemas.code_explainer_schemas import *
from fastapi import HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
import os 
import asyncio
from google import genai
from google.genai import types
from sqlalchemy import select, and_, or_, delete
import re
import json 

load_dotenv()

GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
if not GOOGLE_GEMINI_API_KEY:
    raise ValueError("Unable to acquire the api key for the model")


gemini_api_client = genai.Client(
    api_key=GOOGLE_GEMINI_API_KEY
)


def clean_llm_output(text: str) -> str:
    # Remove ```json or ``` wrappers
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()


GEMINI_SYSTEM_INSTRUCTION = """
    You are a senior software engineer with 20 years experience.

    Take the provided pseudo code from the user and generate a working implementation of the code using python.

    Return the response ONLY in JSON format with the following structure:

    "pseudo_code": "original pseudo_code provided by user",
    "actual_code": "Implementation of the pseudo code in python",
    "title": "generate a short, descriptive title that helps the user recognize the snippet later.",
    "programming_language": "Python is the default language and all code snippet should be generated in python"

    Do not include any extra text outside the JSON.
"""


async def upload_pseudo_code_snippet(
    db: AsyncSession,
    snippet_data: CreatePseudoCodeToCodeSchema
):
    try:
        
        actual_pseudo_snippet = snippet_data.pseudo_code
        
        response = await asyncio.to_thread(
            gemini_api_client.models.generate_content,
            model="gemini-2.5-flash",
            contents=f"Take the provided pseudo code and generate python code from this: \n\n {actual_pseudo_snippet}",
            config=types.GenerateContentConfig(
                system_instruction=GEMINI_SYSTEM_INSTRUCTION,
                response_schema=CodeFromPseudoCodeLLMResponseSchema
            )
        )
        
        print("RAW RESPONSE:", response)
        print("TEXT:", getattr(response, "text", None))
        print("PARSED:", response.parsed)
        
        # parsed_data = CodeFromPseudoCodeLLMResponseSchema.model_validate(response.parsed)
        
        if response.parsed is None:
            raise ValueError(f"Model did not return valid structured output. Raw: {response.text}")
        
        
        cleaned = clean_llm_output(response.text)

        try:
            parsed_json = json.loads(cleaned)
            parsed_data = CodeFromPseudoCodeLLMResponseSchema(**parsed_json)
        except Exception as e:
            raise ValueError(f"Failed to parse LLM output: {cleaned}")
        
        new_code_output = PseudoCodeToCodeModel(
            title=parsed_data.title,
            pseudo_code=parsed_data.pseudo_code,
            actual_code=parsed_data.actual_code
        )
        
        db.save(new_code_output)
        await db.commit()
        await db.refresh(new_code_output)
        
        return new_code_output
        
    except Exception as e:
        await db.rollback()
        print(f"There was an error trying to generate the code for this: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to generate the code requested")
    
    

async def get_all_previous_pseudo_code_snippets(
    db: AsyncSession
):
    try:
        result = await db.execute(select(PseudoCodeToCodeModel))
        snippets = await result.scalars().first()
        
        return snippets
        
    except Exception as e:
        print(f"There was an error trying to get previous pseudo code snippets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was an error trying to get the snippets of pseudo code"
        )
        
        

async def get_specific_pseudo_code_snippet(
    snippet_id: str,
    db: AsyncSession
):
    query = await db.execute(select(PseudoCodeToCodeModel).where(PseudoCodeToCodeModel.id == snippet_id))
    requested_snippet = await query.scalar_one_or_none()
    
    if not requested_snippet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snippet not found")
    
    try:
        return requested_snippet
        
    except Exception as e:
        print(f"There was an error getting this specific pseudo code snippet: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch pseudo code snippet"
        )