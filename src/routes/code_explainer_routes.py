from fastapi import APIRouter, HTTPException, Depends, status
from ..schemas.code_explainer_schemas import *
from ..database import get_db
from ..crud.code_explainer_crud import *
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from fastapi.responses import StreamingResponse

router = APIRouter(
    prefix="/analyzer",
    tags=["Code Analyzer"]
)


@router.post("/new", status_code=status.HTTP_201_CREATED, response_model=DisplayCodeExplanationSchema)
async def upload_new_code_snippet_route(
    snippet_data: UploadCodeSnippetSchema,
    db: AsyncSession = Depends(get_db)
):
    return await upload_code_snippet(
        db=db,
        snippet_data=snippet_data
    )
    

@router.get("/saved_explanations", status_code=status.HTTP_200_OK, response_model=List[DisplayCodeExplanationSchema])
async def get_previous_explanations_route(
    db: AsyncSession = Depends(get_db)
):
    return await get_previous_explanations(db=db)


@router.delete("/delete/{snippet_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_code_snippet_route(
    snippet_id: str,
    db: AsyncSession = Depends(get_db)
):
    return await delete_code_explanation(db=db, snippet_id=snippet_id)


@router.get("/{snippet_id}", response_model=DisplayCodeExplanationSchema)
async def get_single_snippet(
    snippet_id: str,
    db: AsyncSession = Depends(get_db)
):
    snippet = await db.execute(
        select(CodeExplainerModel).where(CodeExplainerModel.id == snippet_id)
    )

    result = snippet.scalar_one_or_none()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snippet not found"
        )

    return result


@router.post("/stream")
async def upload_new_code_snippet_stream(
    snippet_data: UploadCodeSnippetSchema,
    db: AsyncSession = Depends(get_db)
):
    generator = stream_code_explanation(
        db=db,
        snippet_data=snippet_data
    )

    return StreamingResponse(generator, media_type="text/event-stream")