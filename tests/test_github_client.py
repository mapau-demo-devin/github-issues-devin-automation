"""Tests for GitHub API client."""

import pytest
from unittest.mock import Mock, patch
import requests
from github_issues_devin_automation.clients.github_client import GitHubClient


class TestGitHubClient:
    """Test cases for GitHubClient."""
    
    def test_init_with_token(self, mock_env_vars):
        """Test GitHubClient initialization with token."""
        client = GitHubClient()
        assert client.token == 'test_github_token'
        assert client.base_url == 'https://api.github.com'
        assert 'Authorization' in client.headers
        assert client.headers['Authorization'] == 'token test_github_token'
    
    def test_list_issues_basic(self, mock_env_vars):
        """Test basic issue listing."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {'number': 1, 'title': 'Test Issue', 'state': 'open'}
            ]
            mock_get.return_value = mock_response
            
            client = GitHubClient()
            issues = client.list_issues('test/repo')
            
            assert len(issues) == 1
            assert issues[0]['number'] == 1
            mock_get.assert_called_once()
    
    def test_list_issues_with_filters(self, mock_env_vars):
        """Test issue listing with all filters."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_get.return_value = mock_response
            
            client = GitHubClient()
            client.list_issues(
                'test/repo',
                state='closed',
                limit=20,
                labels='bug,enhancement',
                milestone='1',
                assignee='testuser'
            )
            
            call_args = mock_get.call_args
            params = call_args[1]['params']
            
            assert params['state'] == 'closed'
            assert params['per_page'] == 20
            assert params['labels'] == 'bug,enhancement'
            assert params['milestone'] == '1'
            assert params['assignee'] == 'testuser'
    
    def test_list_issues_with_return_headers(self, mock_env_vars):
        """Test issue listing with headers returned."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_response.headers = {'link': 'rel="next"'}
            mock_get.return_value = mock_response
            
            client = GitHubClient()
            issues, headers = client.list_issues('test/repo', return_headers=True)
            
            assert isinstance(issues, list)
            assert isinstance(headers, dict)
            assert 'link' in headers
    
    def test_list_issues_422_error_handling(self, mock_env_vars):
        """Test handling of 422 validation errors."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 422
            mock_response.json.return_value = {
                'message': 'Validation Failed',
                'errors': [
                    {'field': 'assignee', 'code': 'invalid'}
                ]
            }
            mock_get.return_value = mock_response
            
            client = GitHubClient()
            
            with pytest.raises(ValueError, match="Assignee .* not found or invalid"):
                client.list_issues('test/repo', assignee='nonexistent')
    
    def test_get_issue_success(self, mock_env_vars):
        """Test successful issue retrieval."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'number': 1,
                'title': 'Test Issue',
                'body': 'Test body'
            }
            mock_get.return_value = mock_response
            
            client = GitHubClient()
            issue = client.get_issue('test/repo', 1)
            
            assert issue['number'] == 1
            assert issue['title'] == 'Test Issue'
    
    def test_get_issue_not_found(self, mock_env_vars):
        """Test issue not found error."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
            mock_get.return_value = mock_response
            
            client = GitHubClient()
            
            with pytest.raises(requests.exceptions.HTTPError):
                client.get_issue('test/repo', 999)
    
    def test_get_repository_success(self, mock_env_vars):
        """Test successful repository retrieval."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'name': 'test-repo',
                'full_name': 'test/repo',
                'description': 'Test repository'
            }
            mock_get.return_value = mock_response
            
            client = GitHubClient()
            repo = client.get_repository('test/repo')
            
            assert repo['name'] == 'test-repo'
            assert repo['full_name'] == 'test/repo'
    
    def test_has_many_issues_true(self, mock_env_vars):
        """Test has_many_issues returns True when threshold exceeded."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{'number': i} for i in range(11)]
            mock_response.headers = {'link': 'rel="next"'}
            mock_get.return_value = mock_response
            
            client = GitHubClient()
            result = client.has_many_issues('test/repo', threshold=10)
            
            assert result is True
    
    def test_has_many_issues_false(self, mock_env_vars):
        """Test has_many_issues returns False when threshold not exceeded."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{'number': i} for i in range(5)]
            mock_response.headers = {}
            mock_get.return_value = mock_response
            
            client = GitHubClient()
            result = client.has_many_issues('test/repo', threshold=10)
            
            assert result is False
    
    def test_has_many_issues_with_filters(self, mock_env_vars):
        """Test has_many_issues with filter parameters."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_response.headers = {}
            mock_get.return_value = mock_response
            
            client = GitHubClient()
            client.has_many_issues(
                'test/repo',
                threshold=5,
                state='closed',
                labels='bug',
                milestone='1',
                assignee='testuser'
            )
            
            call_args = mock_get.call_args
            params = call_args[1]['params']
            
            assert params['state'] == 'closed'
            assert params['labels'] == 'bug'
            assert params['milestone'] == '1'
            assert params['assignee'] == 'testuser'
