# tests/load/scenarios/mixed_workload.py
"""Locust scenario: 80% reads, 20% writes — realistic multi-user simulation."""

import uuid

from locust import HttpUser, between, task


class MixedWorkloadUser(HttpUser):
    wait_time = between(0.5, 2)
    host = "http://localhost:8080"

    @task(8)
    def browse_categories(self):
        """80% weight: read category tree."""
        self.client.get("/api/v1/catalog/categories")

    @task(2)
    def create_brand(self):
        """20% weight: create a brand."""
        self.client.post(
            "/api/v1/catalog/brands",
            json={
                "name": f"Load Brand {uuid.uuid4().hex[:6]}",
                "slug": f"load-brand-{uuid.uuid4().hex[:6]}",
            },
        )
