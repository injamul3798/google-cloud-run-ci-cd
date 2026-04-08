from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Todo
from schemas import TodoCreate


def create_todo(db: Session, payload: TodoCreate) -> Todo:
    todo = Todo(title=payload.title.strip())
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


def list_todos(db: Session) -> list[Todo]:
    statement = select(Todo).order_by(Todo.created_at.desc(), Todo.id.desc())
    return list(db.scalars(statement).all())
