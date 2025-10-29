#!/usr/bin/env python3
"""
Comprehensive Test Suite for Document Generation Monitor

Tests all stages of text generation and dynamic document loading:
1. API endpoints
2. Document generation workflow
3. Real-time updates
4. Human-in-the-loop approval
5. Exhibit upload
6. WebSocket communication
7. Session persistence
"""
from __future__ import annotations

import asyncio
from datetime import datetime
import json
from pathlib import Path
import time

import httpx
import websockets

# Configuration
API_BASE = "http://localhost:8000/api"
WS_BASE = "ws://localhost:8000/ws/document"
TIMEOUT = 60  # seconds


class Colors:
    """ANSI color codes for terminal output"""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}")
    print(f"{text}")
    print(f"{'='*80}{Colors.ENDC}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


class TestResults:
    """Track test results"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def add_pass(self, test_name, details=""):
        self.passed += 1
        self.tests.append({"name": test_name, "status": "PASS", "details": details})
        print_success(f"{test_name}")
        if details:
            print(f"  {details}")

    def add_fail(self, test_name, error):
        self.failed += 1
        self.tests.append({"name": test_name, "status": "FAIL", "error": str(error)})
        print_error(f"{test_name}: {error}")

    def print_summary(self):
        total = self.passed + self.failed
        print_header("TEST SUMMARY")
        print(f"Total tests: {total}")
        print_success(f"Passed: {self.passed}")
        if self.failed > 0:
            print_error(f"Failed: {self.failed}")
        print(f"\nSuccess rate: {(self.passed/total*100):.1f}%")


results = TestResults()


# ═══════════════════════════════════════════════════════════════════════════
# TEST 1: API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════


async def test_api_endpoints():
    """Test all API endpoints are accessible"""
    print_header("TEST 1: API ENDPOINTS")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test 1.1: Root endpoint
        try:
            response = await client.get("http://localhost:8000/")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            results.add_pass("1.1 Root endpoint", f"Message: {data['message']}")
        except Exception as e:
            results.add_fail("1.1 Root endpoint", e)

        # Test 1.2: API docs
        try:
            response = await client.get("http://localhost:8000/docs")
            assert response.status_code == 200
            results.add_pass("1.2 API documentation endpoint")
        except Exception as e:
            results.add_fail("1.2 API documentation endpoint", e)


# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: DOCUMENT GENERATION WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════


async def test_document_generation():
    """Test document generation workflow"""
    print_header("TEST 2: DOCUMENT GENERATION WORKFLOW")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 2.1: Start generation
        try:
            response = await client.post(
                f"{API_BASE}/generate-petition",
                json={
                    "case_id": "test-case-001",
                    "document_type": "petition",
                    "user_id": "test-user",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "thread_id" in data
            assert data["status"] == "generating"

            thread_id = data["thread_id"]
            results.add_pass("2.1 Start generation", f"Thread ID: {thread_id}")

            # Test 2.2: Get initial preview
            response = await client.get(f"{API_BASE}/document/preview/{thread_id}")
            assert response.status_code == 200
            preview_data = response.json()

            assert "sections" in preview_data
            assert "metadata" in preview_data
            assert "logs" in preview_data
            assert len(preview_data["sections"]) == 5  # 5 sections

            results.add_pass(
                "2.2 Get initial preview",
                f"Sections: {len(preview_data['sections'])}, " f"Status: {preview_data['status']}",
            )

            # Test 2.3: Monitor generation progress
            print_info("Monitoring generation progress (waiting 10 seconds)...")
            await asyncio.sleep(10)

            response = await client.get(f"{API_BASE}/document/preview/{thread_id}")
            updated_data = response.json()

            # Check if at least one section started generating
            in_progress = sum(
                1 for s in updated_data["sections"] if s["status"] in ["in_progress", "completed"]
            )
            assert in_progress > 0

            results.add_pass(
                "2.3 Generation progress", f"Sections in progress/completed: {in_progress}/5"
            )

            return thread_id

        except Exception as e:
            results.add_fail("2.x Document generation", e)
            return None


# ═══════════════════════════════════════════════════════════════════════════
# TEST 3: REAL-TIME UPDATES (WebSocket)
# ═══════════════════════════════════════════════════════════════════════════


async def test_websocket_updates(thread_id):
    """Test WebSocket real-time updates"""
    print_header("TEST 3: WEBSOCKET REAL-TIME UPDATES")

    if not thread_id:
        print_warning("Skipping WebSocket test (no thread_id)")
        return

    try:
        uri = f"{WS_BASE}/{thread_id}"
        updates_received = []

        async with websockets.connect(uri) as websocket:
            results.add_pass("3.1 WebSocket connection established")

            # Receive updates for 15 seconds
            print_info("Listening for real-time updates (15 seconds)...")

            try:
                async with asyncio.timeout(15):
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        updates_received.append(data)

                        # Print update info
                        if "metadata" in data:
                            progress = data["metadata"]["progress_percentage"]
                            print_info(f"  Update received: {progress:.1f}% complete")

            except TimeoutError:
                pass

            # Verify we received updates
            assert len(updates_received) > 0
            results.add_pass(
                "3.2 Real-time updates received", f"Total updates: {len(updates_received)}"
            )

            # Test ping-pong
            await websocket.send("ping")
            response = await websocket.recv()
            assert response == "pong"
            results.add_pass("3.3 WebSocket ping-pong")

    except Exception as e:
        results.add_fail("3.x WebSocket updates", e)


# ═══════════════════════════════════════════════════════════════════════════
# TEST 4: TEXT GENERATION & DYNAMIC CONTENT
# ═══════════════════════════════════════════════════════════════════════════


async def test_text_generation(thread_id):
    """Test progressive text generation and content updates"""
    print_header("TEST 4: TEXT GENERATION & DYNAMIC CONTENT")

    if not thread_id:
        print_warning("Skipping text generation test (no thread_id)")
        return

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Wait for first section to complete
            print_info("Waiting for Introduction section to complete...")

            max_attempts = 20
            for _ in range(max_attempts):
                response = await client.get(f"{API_BASE}/document/preview/{thread_id}")
                data = response.json()

                intro_section = next(
                    (s for s in data["sections"] if s["section_id"] == "intro"), None
                )

                if intro_section and intro_section["status"] == "completed":
                    # Verify HTML content was generated
                    assert len(intro_section["content_html"]) > 0
                    assert "<h1>" in intro_section["content_html"]
                    assert "<h2>" in intro_section["content_html"]
                    assert "<p" in intro_section["content_html"]

                    results.add_pass(
                        "4.1 Introduction section generated",
                        f"Content length: {len(intro_section['content_html'])} chars",
                    )

                    # Check for proper formatting
                    assert "PETITION FOR IMMIGRANT CLASSIFICATION" in intro_section["content_html"]
                    results.add_pass("4.2 Content formatting correct")

                    # Check tokens used
                    assert intro_section.get("tokens_used", 0) > 0
                    results.add_pass(
                        "4.3 Token usage tracked", f"Tokens: {intro_section['tokens_used']}"
                    )
                    break

                await asyncio.sleep(2)
            else:
                raise AssertionError("Introduction section did not complete in time")

        except Exception as e:
            results.add_fail("4.x Text generation", e)


# ═══════════════════════════════════════════════════════════════════════════
# TEST 5: HUMAN-IN-THE-LOOP APPROVAL
# ═══════════════════════════════════════════════════════════════════════════


async def test_human_approval(thread_id):
    """Test human-in-the-loop approval workflow"""
    print_header("TEST 5: HUMAN-IN-THE-LOOP APPROVAL")

    if not thread_id:
        print_warning("Skipping HITL test (no thread_id)")
        return

    async with httpx.AsyncClient(timeout=40.0) as client:
        try:
            # Wait for approval to be required (awards section, ~14 seconds)
            print_info("Waiting for approval request (awards section)...")

            max_attempts = 25
            approval_detected = False

            for _ in range(max_attempts):
                response = await client.get(f"{API_BASE}/document/preview/{thread_id}")
                data = response.json()

                if data["status"] == "pending_approval":
                    approval_detected = True
                    results.add_pass("5.1 Approval request detected", f"Status: {data['status']}")

                    # Get pending approval details
                    approval_response = await client.get(f"{API_BASE}/pending-approval/{thread_id}")
                    assert approval_response.status_code == 200
                    approval_data = approval_response.json()

                    assert "section_id" in approval_data
                    assert "content_html" in approval_data
                    results.add_pass(
                        "5.2 Approval details retrieved",
                        f"Section: {approval_data['section_name']}",
                    )

                    # Test approval
                    print_info("Simulating user approval...")
                    approve_response = await client.post(
                        f"{API_BASE}/approve/{thread_id}",
                        json={
                            "approved": True,
                            "comments": "Automated test approval - content looks good",
                        },
                    )
                    assert approve_response.status_code == 200
                    approve_data = approve_response.json()
                    assert approve_data["accepted"] is True

                    results.add_pass(
                        "5.3 Approval submitted successfully", f"Message: {approve_data['message']}"
                    )

                    # Verify generation continues
                    await asyncio.sleep(3)
                    response = await client.get(f"{API_BASE}/document/preview/{thread_id}")
                    continued_data = response.json()
                    assert continued_data["status"] != "pending_approval"

                    results.add_pass("5.4 Generation continued after approval")
                    break

                await asyncio.sleep(2)

            if not approval_detected:
                results.add_fail("5.x HITL approval", "Approval not triggered within expected time")

        except Exception as e:
            results.add_fail("5.x HITL approval", e)


# ═══════════════════════════════════════════════════════════════════════════
# TEST 6: EXHIBIT UPLOAD
# ═══════════════════════════════════════════════════════════════════════════


async def test_exhibit_upload(thread_id):
    """Test exhibit file upload and display"""
    print_header("TEST 6: EXHIBIT UPLOAD & DYNAMIC LOADING")

    if not thread_id:
        print_warning("Skipping exhibit upload test (no thread_id)")
        return

    try:
        # Create a test file
        test_file_path = Path("test_exhibit.txt")
        test_content = b"This is a test exhibit file for automated testing."
        test_file_path.write_bytes(test_content)

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Upload exhibit
            with open(test_file_path, "rb") as f:
                files = {"file": ("test_award.pdf", f, "application/pdf")}
                data = {"exhibit_id": "2.1.TEST"}

                response = await client.post(
                    f"{API_BASE}/upload-exhibit/{thread_id}", data=data, files=files
                )

            assert response.status_code == 200
            upload_data = response.json()
            assert upload_data["success"] is True
            assert upload_data["exhibit_id"] == "2.1.TEST"

            results.add_pass(
                "6.1 Exhibit uploaded successfully", f"File: {upload_data['filename']}"
            )

            # Verify exhibit appears in document preview
            response = await client.get(f"{API_BASE}/document/preview/{thread_id}")
            preview_data = response.json()

            uploaded_exhibit = next(
                (e for e in preview_data["exhibits"] if e["exhibit_id"] == "2.1.TEST"), None
            )
            assert uploaded_exhibit is not None
            assert uploaded_exhibit["file_size"] == len(test_content)

            results.add_pass(
                "6.2 Exhibit appears in document", f"Size: {uploaded_exhibit['file_size']} bytes"
            )

            # Check logs for upload event
            upload_log = next(
                (log for log in preview_data["logs"] if "2.1.TEST" in log["message"]), None
            )
            assert upload_log is not None
            results.add_pass("6.3 Upload logged in event log")

        # Cleanup
        test_file_path.unlink()

    except Exception as e:
        results.add_fail("6.x Exhibit upload", e)


# ═══════════════════════════════════════════════════════════════════════════
# TEST 7: PAUSE/RESUME
# ═══════════════════════════════════════════════════════════════════════════


async def test_pause_resume():
    """Test pause and resume functionality"""
    print_header("TEST 7: PAUSE/RESUME WORKFLOW")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Start new generation for this test
            response = await client.post(
                f"{API_BASE}/generate-petition",
                json={
                    "case_id": "test-pause-001",
                    "document_type": "petition",
                    "user_id": "test-user",
                },
            )
            thread_id = response.json()["thread_id"]

            # Wait a bit for generation to start
            await asyncio.sleep(3)

            # Pause
            response = await client.post(f"{API_BASE}/pause/{thread_id}")
            assert response.status_code == 200
            pause_data = response.json()
            assert pause_data["status"] == "paused"
            results.add_pass("7.1 Generation paused successfully")

            # Verify status is paused
            response = await client.get(f"{API_BASE}/document/preview/{thread_id}")
            preview_data = response.json()
            assert preview_data["status"] == "paused"
            results.add_pass("7.2 Paused status confirmed")

            # Resume
            response = await client.post(f"{API_BASE}/resume/{thread_id}")
            assert response.status_code == 200
            resume_data = response.json()
            assert resume_data["status"] == "generating"
            results.add_pass("7.3 Generation resumed successfully")

            # Verify generation continues
            await asyncio.sleep(3)
            response = await client.get(f"{API_BASE}/document/preview/{thread_id}")
            preview_data = response.json()
            assert preview_data["status"] != "paused"
            results.add_pass("7.4 Generation continuing after resume")

        except Exception as e:
            results.add_fail("7.x Pause/Resume", e)


# ═══════════════════════════════════════════════════════════════════════════
# TEST 8: COMPLETE WORKFLOW
# ═══════════════════════════════════════════════════════════════════════════


async def test_complete_workflow():
    """Test complete end-to-end workflow"""
    print_header("TEST 8: COMPLETE END-TO-END WORKFLOW")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Start generation
            response = await client.post(
                f"{API_BASE}/generate-petition",
                json={
                    "case_id": "test-complete-001",
                    "document_type": "petition",
                    "user_id": "test-user",
                },
            )
            thread_id = response.json()["thread_id"]
            start_time = time.time()

            print_info(f"Started generation: {thread_id}")

            # Monitor until completion
            completed = False
            max_wait = 45  # seconds

            while time.time() - start_time < max_wait:
                response = await client.get(f"{API_BASE}/document/preview/{thread_id}")
                data = response.json()

                # Handle approval if needed
                if data["status"] == "pending_approval":
                    print_info("  Handling approval request...")
                    await client.post(
                        f"{API_BASE}/approve/{thread_id}",
                        json={"approved": True, "comments": "Automated approval"},
                    )

                # Check if completed
                if data["status"] == "completed":
                    completed = True
                    elapsed = time.time() - start_time

                    # Verify all sections completed
                    completed_sections = sum(
                        1 for s in data["sections"] if s["status"] == "completed"
                    )
                    assert completed_sections == 5

                    results.add_pass("8.1 All sections generated", f"Time: {elapsed:.1f}s")

                    # Verify metadata
                    assert data["metadata"]["progress_percentage"] == 100
                    assert data["metadata"]["total_tokens"] > 0
                    results.add_pass(
                        "8.2 Metadata complete", f"Tokens: {data['metadata']['total_tokens']}"
                    )

                    # Test PDF download
                    pdf_response = await client.get(f"{API_BASE}/download-petition-pdf/{thread_id}")
                    assert pdf_response.status_code == 200
                    assert b"%PDF" in pdf_response.content
                    results.add_pass(
                        "8.3 PDF download successful", f"Size: {len(pdf_response.content)} bytes"
                    )

                    break

                await asyncio.sleep(2)

            if not completed:
                raise AssertionError(f"Workflow did not complete in {max_wait}s")

        except Exception as e:
            results.add_fail("8.x Complete workflow", e)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN TEST RUNNER
# ═══════════════════════════════════════════════════════════════════════════


async def run_all_tests():
    """Run all tests in sequence"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║        DOCUMENT GENERATION MONITOR - COMPREHENSIVE TEST SUITE             ║")
    print("║                                                                            ║")
    print("║  Testing all stages of text generation and dynamic document loading       ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}\n")

    print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"API Base URL: {API_BASE}")
    print_info(f"WebSocket Base URL: {WS_BASE}\n")

    # Run tests
    await test_api_endpoints()
    thread_id = await test_document_generation()

    if thread_id:
        # Run tests that depend on thread_id in parallel where possible
        await test_text_generation(thread_id)
        await test_websocket_updates(thread_id)
        await test_human_approval(thread_id)
        await test_exhibit_upload(thread_id)

    # Run independent tests
    await test_pause_resume()
    await test_complete_workflow()

    # Print summary
    results.print_summary()

    # Save results to file
    report_path = Path("test_results.json")
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": results.passed + results.failed,
        "passed": results.passed,
        "failed": results.failed,
        "success_rate": f"{(results.passed/(results.passed + results.failed)*100):.1f}%",
        "tests": results.tests,
    }

    report_path.write_text(json.dumps(report_data, indent=2))
    print_info(f"\nDetailed results saved to: {report_path}")

    return results.failed == 0


if __name__ == "__main__":
    import sys

    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_warning("\n\nTests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"\n\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
