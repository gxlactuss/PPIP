import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

import database.db as db
from app.auth.jwt import create_access_token, hash_password
from app.main import app
from database.models.user import User


class TargetCompanyTests(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        url = f"sqlite:///{self.path}"
        self.engine = create_engine(url, connect_args={"check_same_thread": False})
        self.patches = [
            mock.patch.object(db, "engine", self.engine),
            mock.patch.object(db, "DATABASE_URL", url),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        self.engine.dispose()
        try:
            os.remove(self.path)
        except PermissionError:
            pass

    def test_existing_users_table_gains_the_column(self):
        conn = sqlite3.connect(self.path)
        try:
            conn.execute(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR, hashed_password VARCHAR)"
            )
            conn.commit()
        finally:
            conn.close()

        db.init_db()

        conn = sqlite3.connect(self.path)
        try:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        finally:
            conn.close()
        self.assertIn("target_company", columns)

    def test_patch_me_round_trips_target_company(self):
        with TestClient(app) as client:
            with Session(self.engine) as session:
                user = User(email="a@example.com", hashed_password=hash_password("password123"))
                session.add(user)
                session.commit()
                session.refresh(user)
                user_id = user.id

            headers = {"Authorization": f"Bearer {create_access_token(str(user_id))}"}

            response = client.patch("/api/auth/me", json={"target_company": "Amazon"}, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["target_company"], "Amazon")

            response = client.patch("/api/auth/me", json={"target_company": None}, headers=headers)
            self.assertIsNone(response.json()["target_company"])


if __name__ == "__main__":
    unittest.main()
