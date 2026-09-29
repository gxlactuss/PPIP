from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth.jwt import get_current_user_id
from database.db import get_session
from database.models.dsa import SolvedProblem
from database.models.interview import InterviewSession, InterviewStatus
from database.models.quiz import QuizResult
from database.models.user import User

router = APIRouter(prefix="/api/progress", tags=["progress"])


class OverallProgressSummary(BaseModel):
    user_id: int
    full_name: Optional[str] = None
    target_role: Optional[str] = None
    target_company: Optional[str] = None
    total_dsa_solved: int
    solved_dsa_slugs: list[str]
    total_quizzes_completed: int
    quiz_best_scores: dict[str, int]
    total_interviews: int
    completed_interviews: int


@router.get("", response_model=OverallProgressSummary)
@router.get("/", response_model=OverallProgressSummary)
def get_user_progress(
    user_id: str = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    uid = int(user_id)
    user = session.get(User, uid)

    # Solved DSA problems
    solved = session.exec(
        select(SolvedProblem).where(SolvedProblem.user_id == uid)
    ).all()
    solved_slugs = [s.slug for s in solved]

    # Quiz results and best scores
    quiz_results = session.exec(
        select(QuizResult).where(QuizResult.user_id == uid)
    ).all()
    best_scores: dict[str, int] = {}
    for qr in quiz_results:
        if qr.score_percentage > best_scores.get(qr.quiz_id, -1):
            best_scores[qr.quiz_id] = qr.score_percentage

    # Interview sessions
    interviews = session.exec(
        select(InterviewSession).where(InterviewSession.user_id == uid)
    ).all()
    completed_count = sum(
        1 for iv in interviews if iv.status == InterviewStatus.COMPLETED
    )

    return OverallProgressSummary(
        user_id=uid,
        full_name=user.full_name if user else None,
        target_role=user.target_role if user else None,
        target_company=user.target_company if user else None,
        total_dsa_solved=len(solved_slugs),
        solved_dsa_slugs=solved_slugs,
        total_quizzes_completed=len(quiz_results),
        quiz_best_scores=best_scores,
        total_interviews=len(interviews),
        completed_interviews=completed_count,
    )
