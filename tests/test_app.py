"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def fresh_activities(client):
    """Get fresh activities state before each test"""
    response = client.get("/activities")
    return response.json()


class TestActivitiesEndpoint:
    """Tests for the /activities endpoint"""

    def test_get_activities_returns_list(self, client):
        """Test that /activities returns a dictionary of activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        activities = response.json()
        assert isinstance(activities, dict)
        assert len(activities) > 0

    def test_activities_have_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        activities = response.json()

        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_activities_contain_chess_club(self, client):
        """Test that Chess Club activity exists"""
        response = client.get("/activities")
        activities = response.json()
        assert "Chess Club" in activities


class TestSignupEndpoint:
    """Tests for the signup endpoint"""

    def test_signup_success(self, client, fresh_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball%20Team/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]

    def test_signup_adds_participant(self, client):
        """Test that signup adds participant to the activity"""
        # Get initial participant count
        response = client.get("/activities")
        initial_count = len(response.json()["Basketball Team"]["participants"])

        # Signup a new participant
        client.post("/activities/Basketball%20Team/signup?email=newstudent@mergington.edu")

        # Check that participant was added
        response = client.get("/activities")
        new_count = len(response.json()["Basketball Team"]["participants"])
        assert new_count == initial_count + 1
        assert "newstudent@mergington.edu" in response.json()["Basketball Team"]["participants"]

    def test_signup_nonexistent_activity(self, client):
        """Test signup for a nonexistent activity"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_duplicate_email(self, client):
        """Test signup fails when student is already signed up"""
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already signed up

        response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_at_capacity(self, client):
        """Test signup fails when activity is at capacity"""
        # First, get an activity and fill it up
        response = client.get("/activities")
        activities = response.json()

        # Find an activity we can fill
        for activity_name, activity_data in activities.items():
            available_spots = activity_data["max_participants"] - len(
                activity_data["participants"]
            )
            if available_spots <= 2:
                # Sign up until at capacity
                for i in range(available_spots):
                    client.post(
                        f"/activities/{activity_name}/signup?email=test{i}@mergington.edu"
                    )

                # Try to sign up one more
                response = client.post(
                    f"/activities/{activity_name}/signup?email=overflow@mergington.edu"
                )
                assert response.status_code == 400
                assert "full capacity" in response.json()["detail"]
                break


class TestUnregisterEndpoint:
    """Tests for the unregister endpoint"""

    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        # First signup
        client.post("/activities/Tennis%20Club/signup?email=unregister@mergington.edu")

        # Then unregister
        response = client.post(
            "/activities/Tennis%20Club/unregister?email=unregister@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]

    def test_unregister_removes_participant(self, client):
        """Test that unregister removes participant from the activity"""
        email = "remove@mergington.edu"

        # Signup
        client.post(f"/activities/Tennis%20Club/signup?email={email}")

        # Verify signup
        response = client.get("/activities")
        assert email in response.json()["Tennis Club"]["participants"]

        # Unregister
        client.post(f"/activities/Tennis%20Club/unregister?email={email}")

        # Verify removal
        response = client.get("/activities")
        assert email not in response.json()["Tennis Club"]["participants"]

    def test_unregister_nonexistent_activity(self, client):
        """Test unregister for nonexistent activity"""
        response = client.post(
            "/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_not_signed_up(self, client):
        """Test unregister fails when student is not signed up"""
        response = client.post(
            "/activities/Tennis%20Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirects_to_static(self, client):
        """Test that / redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"
