import pytest
import os
from unittest.mock import Mock, patch
from github_client import GitHubClient
from devin_client import DevinClient


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    with patch.dict(os.environ, {
        'GITHUB_TOKEN': 'test_github_token',
        'DEVIN_API_KEY': 'test_devin_api_key',
        'DEVIN_API_BASE_URL': 'https://api.devin.ai/v1',
        'DEVIN_API_TIMEOUT': '120',
        'DEVIN_API_MAX_RETRIES': '3'
    }):
        yield


@pytest.fixture
def sample_issues():
    """Sample GitHub issues for testing"""
    return [
        {
            'number': 1,
            'title': 'Fix login bug',
            'state': 'open',
            'body': 'The login form is not validating properly. Users can submit empty credentials.',
            'user': {'login': 'testuser1'},
            'labels': [{'name': 'bug'}, {'name': 'high-priority'}],
            'milestone': {'title': 'v1.0.0'},
            'assignee': {'login': 'developer1'}
        },
        {
            'number': 2,
            'title': 'Add dark mode support',
            'state': 'open',
            'body': 'Implement dark mode theme for better user experience.',
            'user': {'login': 'testuser2'},
            'labels': [{'name': 'enhancement'}, {'name': 'good first issue'}],
            'milestone': None,
            'assignee': None
        },
        {
            'number': 3,
            'title': 'Extract magic numbers to constants',
            'state': 'open',
            'body': 'Replace hardcoded values with named constants for better maintainability.',
            'user': {'login': 'testuser3'},
            'labels': [{'name': 'refactor'}],
            'milestone': {'title': 'v1.1.0'},
            'assignee': {'login': 'developer2'}
        }
    ]


@pytest.fixture
def sample_repository():
    """Sample repository data for testing"""
    return {
        'name': 'running-buddy',
        'full_name': 'mapau-demo-devin/running-buddy',
        'description': 'A smart running companion',
        'private': False,
        'owner': {'login': 'mapau-demo-devin'}
    }


@pytest.fixture
def mock_github_client(mock_env_vars, sample_issues, sample_repository):
    """Mock GitHub client with predefined responses"""
    with patch('github_client.GitHubClient') as mock_class:
        mock_instance = Mock(spec=GitHubClient)
        mock_instance.list_issues.return_value = sample_issues
        mock_instance.get_issue.return_value = sample_issues[0]
        mock_instance.get_repository.return_value = sample_repository
        mock_instance.has_many_issues.return_value = False
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_devin_client(mock_env_vars):
    """Mock Devin client to prevent actual session creation"""
    with patch('devin_client.DevinClient') as mock_class:
        mock_instance = Mock(spec=DevinClient)
        mock_instance.create_session.return_value = {
            'session_id': 'test-session-123',
            'url': 'https://app.devin.ai/sessions/test-session-123'
        }
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_requests():
    """Mock requests module for HTTP calls"""
    with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
        yield mock_get, mock_post


@pytest.fixture
def test_repos():
    """Test repository names"""
    return ['mapau-demo-devin/running-buddy', 'oppia/oppia']


@pytest.fixture
def filter_combinations():
    """All possible filter combinations for testing"""
    return [
        {},
        {'label': 'bug'},
        {'label': 'enhancement,good first issue'},
        {'milestone': '1'},
        {'milestone': '*'},
        {'milestone': 'none'},
        {'assignee': 'developer1'},
        {'assignee': '*'},
        {'assignee': 'none'},
        {'label': 'bug', 'milestone': '1'},
        {'label': 'enhancement', 'assignee': 'developer1'},
        {'milestone': '*', 'assignee': 'none'},
        {'label': 'bug', 'milestone': '1', 'assignee': 'developer1'}
    ]
