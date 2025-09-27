"""Shared test fixtures and configuration for GitHub Issues Devin Automation tests."""

import pytest
from unittest.mock import Mock, patch
import os
from typing import Dict, Any, List


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        'GITHUB_TOKEN': 'test_github_token',
        'DEVIN_API_KEY': 'test_devin_api_key',
        'DEVIN_API_BASE_URL': 'https://test-api.devin.ai/v1',
        'DEVIN_API_TIMEOUT': '30',
        'DEVIN_API_MAX_RETRIES': '2'
    }):
        yield


@pytest.fixture
def sample_github_issues():
    """Sample GitHub issues data for testing."""
    return [
        {
            'number': 1,
            'title': 'Fix bug in heart rate calculation',
            'body': 'The heart rate calculation is incorrect when using mock data. Need to fix the formula.',
            'state': 'open',
            'user': {'login': 'testuser1'},
            'labels': [
                {'name': 'bug'},
                {'name': 'priority-high'}
            ],
            'milestone': {
                'title': 'v1.0',
                'number': 1
            },
            'assignee': {
                'login': 'developer1'
            }
        },
        {
            'number': 2,
            'title': 'Add new feature for pace tracking',
            'body': 'Implement a new feature that tracks running pace over time and provides analytics.',
            'state': 'open',
            'user': {'login': 'testuser2'},
            'labels': [
                {'name': 'enhancement'},
                {'name': 'good first issue'}
            ],
            'milestone': None,
            'assignee': None
        },
        {
            'number': 3,
            'title': 'Update documentation for API endpoints',
            'body': 'The API documentation is outdated and needs to be refreshed with current endpoints.',
            'state': 'closed',
            'user': {'login': 'testuser3'},
            'labels': [
                {'name': 'documentation'}
            ],
            'milestone': {
                'title': 'v0.9',
                'number': 2
            },
            'assignee': {
                'login': 'developer2'
            }
        }
    ]


@pytest.fixture
def sample_oppia_issues():
    """Sample Oppia repository issues for testing."""
    return [
        {
            'number': 101,
            'title': 'Improve lesson creation workflow',
            'body': 'The current lesson creation process is too complex for new users. We need to simplify the UI.',
            'state': 'open',
            'user': {'login': 'oppia-contributor'},
            'labels': [
                {'name': 'enhancement'},
                {'name': 'UI/UX'}
            ],
            'milestone': {
                'title': 'Release 3.0',
                'number': 10
            },
            'assignee': {
                'login': 'ui-developer'
            }
        },
        {
            'number': 102,
            'title': 'Fix memory leak in exploration player',
            'body': 'There is a memory leak when playing long explorations. Need to investigate and fix.',
            'state': 'open',
            'user': {'login': 'oppia-dev'},
            'labels': [
                {'name': 'bug'},
                {'name': 'performance'}
            ],
            'milestone': None,
            'assignee': None
        }
    ]


@pytest.fixture
def sample_repository_info():
    """Sample repository information for testing."""
    return {
        'running-buddy': {
            'name': 'running-buddy',
            'full_name': 'mapau-demo-devin/running-buddy',
            'description': 'A smart running companion app',
            'private': False,
            'owner': {'login': 'mapau-demo-devin'}
        },
        'oppia': {
            'name': 'oppia',
            'full_name': 'oppia/oppia',
            'description': 'A free, online learning platform',
            'private': False,
            'owner': {'login': 'oppia'}
        }
    }


@pytest.fixture
def mock_devin_session_response():
    """Mock Devin API session creation response."""
    return {
        'session_id': 'test-session-123',
        'url': 'https://app.devin.ai/sessions/test-session-123',
        'status': 'created'
    }


@pytest.fixture
def mock_github_client(sample_github_issues, sample_oppia_issues, sample_repository_info):
    """Mock GitHub client with predefined responses."""
    mock_client = Mock()
    
    def mock_list_issues(repo, state='open', limit=10, return_headers=False, labels=None, milestone=None, assignee=None):
        if repo == 'mapau-demo-devin/running-buddy':
            issues = sample_github_issues
        elif repo == 'oppia/oppia':
            issues = sample_oppia_issues
        else:
            issues = []
        
        filtered_issues = []
        for issue in issues:
            if state != 'all' and issue['state'] != state:
                continue
            
            if labels:
                label_names = [label['name'] for label in issue['labels']]
                required_labels = [l.strip() for l in labels.split(',')]
                if not any(label in label_names for label in required_labels):
                    continue
            
            if milestone:
                if milestone == 'none' and issue['milestone'] is not None:
                    continue
                elif milestone != 'none' and milestone != '*':
                    if issue['milestone'] is None or str(issue['milestone']['number']) != milestone:
                        continue
            
            if assignee:
                if assignee == 'none' and issue['assignee'] is not None:
                    continue
                elif assignee != 'none' and assignee != '*':
                    if issue['assignee'] is None or issue['assignee']['login'] != assignee:
                        continue
            
            filtered_issues.append(issue)
        
        filtered_issues = filtered_issues[:limit]
        
        if return_headers:
            headers = {'link': 'rel="next"' if len(filtered_issues) == limit else ''}
            return filtered_issues, headers
        return filtered_issues
    
    def mock_get_issue(repo, issue_number):
        if repo == 'mapau-demo-devin/running-buddy':
            issues = sample_github_issues
        elif repo == 'oppia/oppia':
            issues = sample_oppia_issues
        else:
            from requests.exceptions import HTTPError
            response = Mock()
            response.status_code = 404
            raise HTTPError(response=response)
        
        for issue in issues:
            if issue['number'] == issue_number:
                return issue
        
        from requests.exceptions import HTTPError
        response = Mock()
        response.status_code = 404
        raise HTTPError(response=response)
    
    def mock_get_repository(repo):
        repo_name = repo.split('/')[-1]
        if repo_name in sample_repository_info:
            return sample_repository_info[repo_name]
        
        from requests.exceptions import HTTPError
        response = Mock()
        response.status_code = 404
        raise HTTPError(response=response)
    
    def mock_has_many_issues(repo, threshold=10, state='open', labels=None, milestone=None, assignee=None):
        issues = mock_list_issues(repo, state=state, limit=threshold + 1, labels=labels, milestone=milestone, assignee=assignee)
        return len(issues) > threshold
    
    mock_client.list_issues.side_effect = mock_list_issues
    mock_client.get_issue.side_effect = mock_get_issue
    mock_client.get_repository.side_effect = mock_get_repository
    mock_client.has_many_issues.side_effect = mock_has_many_issues
    
    return mock_client


@pytest.fixture
def mock_devin_client(mock_devin_session_response):
    """Mock Devin client with predefined responses."""
    mock_client = Mock()
    
    mock_client.create_session.return_value = mock_devin_session_response
    mock_client.send_message.return_value = None
    mock_client.get_session.return_value = {'session_id': 'test-session-123', 'status': 'active'}
    mock_client.list_sessions.return_value = {'sessions': [mock_devin_session_response]}
    
    return mock_client


@pytest.fixture
def mock_user_input():
    """Mock user input for interactive prompts."""
    with patch('click.prompt') as mock_prompt, \
         patch('inquirer.prompt') as mock_inquirer:
        mock_prompt.return_value = 'y'
        mock_inquirer.return_value = {'issue': 1}
        yield mock_prompt, mock_inquirer
