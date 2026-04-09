from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db import get_db
from schemas import TodoCreate, TodoRead
from service import create_todo, list_todos

router = APIRouter()


@router.get("/sample", status_code=status.HTTP_200_OK)
def sample_api() -> dict[str, str]:
    return {
        "message": "Sample API is working.",
        "status": "success",
    }


@router.post("/todos", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
def add_todo(payload: TodoCreate, db: Session = Depends(get_db)) -> TodoRead:
    if not payload.title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Title cannot be blank.",
        )
    return create_todo(db, payload)


@router.get("/todos", response_model=list[TodoRead], status_code=status.HTTP_200_OK)
def view_todos(db: Session = Depends(get_db)) -> list[TodoRead]:
    return list_todos(db)
