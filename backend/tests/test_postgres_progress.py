import json
import os
import unittest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth.jwt import create_access_token, hash_password
from app.main import app
from database.db import engine
from database.models.dsa import SolvedProblem
from database.models.interview import InterviewSession, InterviewStatus
from database.models.quiz import QuizResult
from database.models.user import User


class PostgresProgressIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Only run if connected to PostgreSQL
        if engine.dialect.name != "postgresql":
            raise unittest.SkipTest("PostgreSQL is not configured as the active engine")

    def setUp(self):
        self.test_email = "progress_test_user@example.com"
        with Session(engine) as session:
            # Clean up any leftover test data
            user = session.exec(select(User).where(User.email == self.test_email)).first()
            if user:
                user_id = user.id
                for sp in session.exec(select(SolvedProblem).where(SolvedProblem.user_id == user_id)).all():
                    session.delete(sp)
                for qr in session.exec(select(QuizResult).where(QuizResult.user_id == user_id)).all():
                    session.delete(qr)
                for iv in session.exec(select(InterviewSession).where(InterviewSession.user_id == user_id)).all():
                    session.delete(iv)
                session.delete(user)
                session.commit()

            # Create test user
            self.user = User(
                email=self.test_email,
                hashed_password=hash_password("password123"),
                full_name="Progress Tester",
                target_role="Backend Developer",
                target_company="Google",
                is_verified=True,
                onboarded=True,
            )
            session.add(self.user)
            session.commit()
            session.refresh(self.user)
            self.user_id = self.user.id

        self.token = create_access_token(str(self.user_id))
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.client = TestClient(app)

    def tearDown(self):
        with Session(engine) as session:
            user = session.exec(select(User).where(User.email == self.test_email)).first()
            if user:
                user_id = user.id
                for sp in session.exec(select(SolvedProblem).where(SolvedProblem.user_id == user_id)).all():
                    session.delete(sp)
                for qr in session.exec(select(QuizResult).where(QuizResult.user_id == user_id)).all():
                    session.delete(qr)
                for iv in session.exec(select(InterviewSession).where(InterviewSession.user_id == user_id)).all():
                    session.delete(iv)
                session.delete(user)
                session.commit()

    def test_quiz_progress_saved_in_postgres(self):
        # 1. Submit quiz attempt 1 (score 70)
        res1 = self.client.post(
            "/api/quiz/submit",
            json={
                "quiz_id": "quiz-os-01",
                "total_questions": 10,
                "correct_answers": 7,
                "score_percentage": 70,
            },
            headers=self.headers,
        )
        self.assertEqual(res1.status_code, 200, res1.text)
        data1 = res1.json()
        self.assertEqual(data1["quiz_id"], "quiz-os-01")
        self.assertEqual(data1["score_percentage"], 70)

        # 2. Submit quiz attempt 2 for same quiz (higher score 90)
        res2 = self.client.post(
            "/api/quiz/submit",
            json={
                "quiz_id": "quiz-os-01",
                "total_questions": 10,
                "correct_answers": 9,
                "score_percentage": 90,
            },
            headers=self.headers,
        )
        self.assertEqual(res2.status_code, 200)

        # 3. Check progress endpoint returns best score 90
        prog_res = self.client.get("/api/quiz/progress", headers=self.headers)
        self.assertEqual(prog_res.status_code, 200)
        prog_items = prog_res.json()
        os_item = next((item for item in prog_items if item["quiz_id"] == "quiz-os-01"), None)
        self.assertIsNotNone(os_item)
        self.assertEqual(os_item["best_score"], 90)

        # 4. Check history endpoint returns both attempts
        hist_res = self.client.get("/api/quiz/history", headers=self.headers)
        self.assertEqual(hist_res.status_code, 200)
        attempts = [a for a in hist_res.json() if a["quiz_id"] == "quiz-os-01"]
        self.assertEqual(len(attempts), 2)

        # 5. Direct DB check in PostgreSQL
        with Session(engine) as session:
            rows = session.exec(
                select(QuizResult).where(QuizResult.user_id == self.user_id)
            ).all()
            self.assertEqual(len(rows), 2)

    def test_dsa_solved_progress_saved_in_postgres(self):
        # 1. Mark 'two-sum' and 'lru-cache' as solved
        r1 = self.client.post("/api/dsa/solved", json={"slug": "two-sum"}, headers=self.headers)
        self.assertEqual(r1.status_code, 204)
        r2 = self.client.post("/api/dsa/solved", json={"slug": "lru-cache"}, headers=self.headers)
        self.assertEqual(r2.status_code, 204)

        # 2. Fetch solved list from API
        get_res = self.client.get("/api/dsa/solved", headers=self.headers)
        self.assertEqual(get_res.status_code, 200)
        solved = get_res.json()
        self.assertIn("two-sum", solved)
        self.assertIn("lru-cache", solved)

        # 3. Verify in PostgreSQL database
        with Session(engine) as session:
            rows = session.exec(
                select(SolvedProblem).where(SolvedProblem.user_id == self.user_id)
            ).all()
            slugs = {r.slug for r in rows}
            self.assertIn("two-sum", slugs)
            self.assertIn("lru-cache", slugs)

        # 4. Unmark 'two-sum'
        del_res = self.client.delete("/api/dsa/solved/two-sum", headers=self.headers)
        self.assertEqual(del_res.status_code, 204)

        # 5. Confirm deletion
        get_res2 = self.client.get("/api/dsa/solved", headers=self.headers)
        self.assertNotIn("two-sum", get_res2.json())
        self.assertIn("lru-cache", get_res2.json())

    def test_interview_session_progress_saved_in_postgres(self):
        # Direct DB session creation for interview progress
        with Session(engine) as session:
            from datetime import datetime, timezone
            interview = InterviewSession(
                user_id=self.user_id,
                target_role="Backend Developer",
                mode="core_cs",
                status=InterviewStatus.IN_PROGRESS,
                transcript_json=json.dumps([
                    {
                        "speaker": "ai",
                        "text": "What is an index?",
                        "at": datetime.now(timezone.utc).isoformat(),
                    }
                ]),
            )
            session.add(interview)
            session.commit()
            session.refresh(interview)
            interview_id = interview.id

        # Read back via API
        res = self.client.get(f"/api/interview/{interview_id}", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["id"], interview_id)
        self.assertEqual(data["target_role"], "Backend Developer")
        self.assertEqual(data["status"], "in_progress")

    def test_overall_progress_endpoint(self):
        # Add solved problem
        self.client.post("/api/dsa/solved", json={"slug": "binary-search"}, headers=self.headers)

        # Submit quiz
        self.client.post(
            "/api/quiz/submit",
            json={
                "quiz_id": "dsa-trees-01",
                "total_questions": 5,
                "correct_answers": 4,
                "score_percentage": 80,
            },
            headers=self.headers,
        )

        # Fetch overall progress summary
        res = self.client.get("/api/progress", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["user_id"], self.user_id)
        self.assertEqual(data["total_dsa_solved"], 1)
        self.assertIn("binary-search", data["solved_dsa_slugs"])
        self.assertEqual(data["total_quizzes_completed"], 1)
        self.assertEqual(data["quiz_best_scores"].get("dsa-trees-01"), 80)
        self.assertEqual(data["target_company"], "Google")



if __name__ == "__main__":
    unittest.main()
