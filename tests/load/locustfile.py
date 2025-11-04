"""Locust load testing configuration for MegaAgent Pro API.

Run with: locust -f tests/load/locustfile.py --host=http://localhost:8000
"""

from __future__ import annotations

import random

from locust import HttpUser, between, task


class AgentAPIUser(HttpUser):
    """Simulated user for Agent API load testing."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    def on_start(self) -> None:
        """Called when a simulated user starts."""
        # Setup: Create a test session or authenticate
        self.test_case_id = f"test_case_{random.randint(1000, 9999)}"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_token",  # Replace with actual auth
        }

    @task(10)  # Weight: 10 (most common operation)
    def query_agent(self) -> None:
        """Test agent query endpoint."""
        payload = {
            "query": "What are the key clauses in this contract?",
            "context": {"case_id": self.test_case_id},
        }

        with self.client.post(
            "/api/v1/agent/query",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(5)
    def create_case(self) -> None:
        """Test case creation endpoint."""
        payload = {
            "client_name": f"Client {random.randint(1, 1000)}",
            "case_type": random.choice(["contract", "litigation", "compliance"]),
            "description": "Test case for load testing",
            "priority": random.choice(["low", "medium", "high"]),
        }

        with self.client.post(
            "/api/v1/cases",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
                # Store case ID for later use
                try:
                    data = response.json()
                    self.test_case_id = data.get("case_id", self.test_case_id)
                except Exception:
                    pass
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(8)
    def get_case(self) -> None:
        """Test case retrieval endpoint."""
        with self.client.get(
            f"/api/v1/cases/{self.test_case_id}",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:  # 404 is acceptable
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(3)
    def generate_document(self) -> None:
        """Test document generation endpoint."""
        payload = {
            "document_type": "letter",
            "template": "demand_letter",
            "variables": {
                "recipient": "John Doe",
                "amount": "$5,000",
                "deadline": "30 days",
            },
            "case_id": self.test_case_id,
        }

        with self.client.post(
            "/api/v1/documents/generate",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def search_cases(self) -> None:
        """Test case search endpoint."""
        params = {
            "query": "contract dispute",
            "limit": 10,
            "offset": 0,
        }

        with self.client.get(
            "/api/v1/cases/search",
            params=params,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(4)
    def validate_document(self) -> None:
        """Test document validation endpoint."""
        payload = {
            "document_content": "This is a test contract with standard clauses.",
            "validation_rules": ["completeness", "legal_compliance"],
        }

        with self.client.post(
            "/api/v1/validate",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


class HeavyAPIUser(HttpUser):
    """Simulated user for heavy/intensive operations."""

    wait_time = between(5, 10)  # Longer wait for heavy operations

    def on_start(self) -> None:
        """Called when a simulated user starts."""
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_token",
        }

    @task
    def complex_analysis(self) -> None:
        """Test complex document analysis."""
        payload = {
            "document": "Long contract text..." * 100,  # Simulate large document
            "analysis_type": "comprehensive",
            "include_rag": True,
            "include_graph": True,
        }

        with self.client.post(
            "/api/v1/analyze",
            json=payload,
            headers=self.headers,
            catch_response=True,
            timeout=60,  # Longer timeout for heavy operations
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")
