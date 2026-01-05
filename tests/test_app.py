import os
import sys
import pytest
from unittest.mock import patch
from app.main import app, init_db, get_visitors, save_visitor
import sqlite3


@pytest.fixture
def client():
    """Create a test client for the app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Initialize the test database
        init_db()
        yield client


def test_home_endpoint(client):
    """Test the home endpoint."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'\xe6\xac\xa2\xe8\xbf\x8e\xe6\x9d\xa5\xe5\x88\xb0TAOTAO\xe5\xba\x94\xe7\x94\xa8!' in response.data  # "欢迎来到TAOTAO应用!" in bytes


def test_api_status_endpoint(client):
    """Test the API status endpoint."""
    response = client.get('/api/status')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    assert json_data['message'] == 'Flask API is running!'
    assert 'environment' in json_data


def test_health_endpoint(client):
    """Test the health endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'healthy'


def test_readiness_endpoint(client):
    """Test the readiness endpoint."""
    response = client.get('/ready')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'ready'


def test_visitor_history_endpoint(client):
    """Test the visitor history endpoint."""
    # First, access some endpoints to create visitor records
    client.get('/', headers={'User-Agent': 'test-agent-1'})
    client.get('/api/status', headers={'User-Agent': 'test-agent-2'})

    # Now test the visitor history endpoint
    response = client.get('/visitors')
    assert response.status_code == 200
    assert b'\xe8\xae\xbf\xe9\x97\xae\xe8\x80\x85\xe5\x8e\x86\xe5\x8f\xb2' in response.data  # "访问者历史" in bytes


def test_error_handling(client):
    """Test error handling for non-existent endpoint."""
    response = client.get('/nonexistent')
    assert response.status_code == 404
    json_data = response.get_json()
    assert 'error' in json_data
    assert json_data['error']['code'] == 404


def test_database_functionality():
    """Test the database functionality directly."""
    # Initialize the database
    init_db()

    # Save a test visitor
    save_visitor('192.168.1.1', 'test-agent')

    # Get visitors
    visitors = get_visitors()

    # Check that we have at least one visitor
    assert len(visitors) >= 1

    # Check that the most recent visitor has the expected IP
    latest_visitor = visitors[0]
    ip, timestamp, user_agent = latest_visitor
    assert ip == '192.168.1.1'
    assert user_agent == 'test-agent'


if __name__ == '__main__':
    pytest.main()
