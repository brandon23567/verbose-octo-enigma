from ..models.code_explainer_models import *
from ..schemas.code_explainer_schemas import *
from sqlalchemy import select, delete, and_, or_ 
from ..database import get_db
from fastapi import HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
import os 
from google import genai
from google.genai import types
import asyncio
from sqlalchemy.orm import load_only
import json
import re

load_dotenv()

GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
if not GOOGLE_GEMINI_API_KEY:
    raise ValueError("Unable to acquire the api key for the model")


gemini_api_client = genai.Client(
    api_key=GOOGLE_GEMINI_API_KEY
)

GEMINI_SYSTEM_INSTRUCTION = """
    You are a senior software engineer with 20 years experience.

    Explain the provided code snippet clearly and concisely.

    Return the response ONLY in JSON format with the following structure:

    
    "code_snippet": "original code snippet provided by user",
    "explanation": "clear explanation of what the code does, why it works, and one alternative approach",
    "title": "generate a short, descriptive title that helps the user recognize the snippet later."
    

    Do not include any extra text outside the JSON.
"""


# this should handle both the uploading to the snippet to the db and the explanation from the llm
# but we visit the llm first
async def upload_code_snippet(
    db: AsyncSession,
    snippet_data: UploadCodeSnippetSchema
):
    try:
        actual_code_snippet = snippet_data.code_snippet
        
        response = await asyncio.to_thread(
            gemini_api_client.models.generate_content,
            model="gemini-2.5-flash",
            contents=f"Explain the following code snippet:\n\n{actual_code_snippet}",
            config=types.GenerateContentConfig(
                system_instruction=GEMINI_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=CodeExplanationLLMSchema
            )
        )
        
        parsed_data = CodeExplanationLLMSchema.model_validate(response.parsed)
        
        new_snippet = CodeExplainerModel(
            code_snippet=parsed_data.code_snippet,
            explanation=parsed_data.explanation,
            title=parsed_data.title
        )
        
        db.add(new_snippet)
        await db.commit()
        await db.refresh(new_snippet)
        
        return new_snippet
        
    except Exception as e:
        await db.rollback()
        print(f"There was an error uploading your snippet: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to upload snippet")
    
    
    
async def get_previous_explanations(
    db: AsyncSession
):

    try:

        query = await db.execute(
            select(CodeExplainerModel).order_by(
                CodeExplainerModel.date_created.desc()
            )
        )

        snippets = query.scalars().all()

        return [
            DisplayCodeExplanationSchema.model_validate(snippet)
            for snippet in snippets
        ]

    except Exception as e:

        print(f"There was an error trying to get previous explanations: {str(e)}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch previous explanations"
        )
    

async def delete_code_explanation(
    db: AsyncSession,
    snippet_id: str
):
    valid_code_snippet = await db.execute(select(CodeExplainerModel).where(CodeExplainerModel.id == snippet_id))
    snippet_validity = valid_code_snippet.scalar_one_or_none()
    if not snippet_validity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snippet not found"
        )
        
    try:
        await db.delete(snippet_validity)
        await db.commit()
        
        return { "message": "Code snippet has been deleted" }
        
    except Exception as e:
        await db.rollback()
        print(f"There was an error trying to delete the code explanation: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to delete this code snippet")
    

async def stream_code_explanation(
    db: AsyncSession,
    snippet_data: UploadCodeSnippetSchema
):

    actual_code_snippet = snippet_data.code_snippet
    full_response = ""

    try:

        def run_stream():
            return gemini_api_client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=f"""
                    Explain the following code snippet in detail.

                    Return JSON with fields:
                        title
                        code_snippet
                        explanation

                    Code:
                        {actual_code_snippet}
                """,
                config=types.GenerateContentConfig(
                    system_instruction=GEMINI_SYSTEM_INSTRUCTION,
                    response_mime_type="application/json"
                )
            )

        # Run Gemini call in thread
        response = await asyncio.to_thread(run_stream)

        # Collect JSON chunks
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
                await asyncio.sleep(0)

        # Clean markdown wrappers
        cleaned = re.search(r"\{.*\}", full_response, re.DOTALL).group()

        # Parse JSON safely
        try:
            parsed_data = CodeExplanationLLMSchema.model_validate(
                json.loads(cleaned)
            )
        except Exception as parse_error:
            raise ValueError(f"LLM returned invalid JSON: {cleaned}") from parse_error

        # -------------------------
        # SAVE TO DATABASE FIRST
        # -------------------------

        new_snippet = CodeExplainerModel(
            code_snippet=parsed_data.code_snippet,
            explanation=parsed_data.explanation,
            title=parsed_data.title
        )

        db.add(new_snippet)

        print("Saving snippet to DB...")

        await db.commit()

        await db.refresh(new_snippet)

        print("Saved snippet:", new_snippet.id)

        # -------------------------
        # STREAM EXPLANATION
        # -------------------------

        explanation_text = parsed_data.explanation

        for word in explanation_text.split(" "):
            yield f"data: {word} "
            await asyncio.sleep(0.015)

        yield "data: [DONE]\n\n"

    except Exception as e:

        await db.rollback()

        error_message = f"Streaming error: {str(e)}"
        print(error_message)

        yield f"data: ERROR: {error_message}\n\n"