# tests/load/scenarios/auth_flow.py
"""Locust scenario: Register -> Login -> Refresh -> Logout."""

import uuid

from locust import HttpUser, between, task


class AuthFlowUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    def on_start(self):
        self.email = f"load-{uuid.uuid4().hex[:8]}@test.com"
        self.password = "S3cure!LoadTest"
        self.access_token = None
        self.refresh_token = None

    @task(1)
    def full_auth_flow(self):
        # Register
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": self.email,
                "password": self.password,
            },
        )

        # Login
        resp = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": self.email,
                "password": self.password,
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")

        # Refresh
        if self.refresh_token:
            self.client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": self.refresh_token},
            )

        # Logout
        if self.access_token:
            self.client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )

        # Reset for next iteration
        self.email = f"load-{uuid.uuid4().hex[:8]}@test.com"
