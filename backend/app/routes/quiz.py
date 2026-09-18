from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.core.auth import get_current_user_id
from app.database import get_session
from app.models.quiz import QuizDifficulty, QuizResult, QuizTopic, QuizQuestion as QuizQuestionModel
from app.schemas.quiz import QuizQuestion as QuizQuestionSchema, QuizResultRead, QuizSubmit

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


@router.get("/questions", response_model=list[QuizQuestionSchema])
def get_quiz_questions(
    topic: QuizTopic,
    difficulty: QuizDifficulty,
    session: Session = Depends(get_session)
):
    questions = session.exec(
        select(QuizQuestionModel).where(QuizQuestionModel.topic == topic, QuizQuestionModel.difficulty == difficulty)
    ).all()
    return questions
@router.post("/submit", response_model=QuizResultRead)
def submit_quiz(
    payload: QuizSubmit,
    user_id: str = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Save quiz result to PostgreSQL."""
    db_result = QuizResult(
        user_id=int(user_id),
        quiz_id=payload.quiz_id,
        score=payload.score,  # Uses the score sent from the client/frontend
    )
    
    session.add(db_result)  
    session.commit()
    session.refresh(db_result)
    
    return db_result

@router.get("/history", response_model=list[QuizResultRead])
def get_quiz_history(
    user_id: str = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    results = session.exec(
        select(QuizResult).where(QuizResult.user_id == int(user_id))
    ).all()
    return results
