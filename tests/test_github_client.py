import pytest
import requests
from unittest.mock import Mock, patch
from github_client import GitHubClient


class TestGitHubClient:
    
    def test_init_with_token(self, mock_env_vars):
        """Test GitHubClient initialization with valid token"""
        client = GitHubClient()
        assert client.token == 'test_github_token'
        assert client.base_url == 'https://api.github.com'
        assert 'Authorization' in client.headers
        assert 'Accept' in client.headers

    def test_init_without_token(self):
        """Test GitHubClient initialization without token raises error"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="GITHUB_TOKEN environment variable is required"):
                GitHubClient()

    @patch('requests.get')
    def test_list_issues_success(self, mock_get, mock_env_vars, sample_issues):
        """Test successful issue listing"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_issues
        mock_get.return_value = mock_response
        
        client = GitHubClient()
        issues = client.list_issues('mapau-demo-devin/running-buddy')
        
        assert len(issues) == 3
        assert issues[0]['number'] == 1
        assert issues[0]['title'] == 'Fix login bug'
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_list_issues_with_filters(self, mock_get, mock_env_vars, sample_issues):
        """Test issue listing with all filter types"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_issues
        mock_get.return_value = mock_response
        
        client = GitHubClient()
        issues = client.list_issues(
            'mapau-demo-devin/running-buddy',
            state='all',
            limit=20,
            labels='bug,enhancement',
            milestone='1',
            assignee='developer1'
        )
        
        assert len(issues) == 3
        call_args = mock_get.call_args
        params = call_args[1]['params']
        assert params['state'] == 'all'
        assert params['per_page'] == 20
        assert params['labels'] == 'bug,enhancement'
        assert params['milestone'] == '1'
        assert params['assignee'] == 'developer1'

    @patch('requests.get')
    def test_list_issues_invalid_assignee(self, mock_get, mock_env_vars):
        """Test handling of invalid assignee filter"""
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            'message': 'Validation Failed',
            'errors': [{'field': 'assignee', 'code': 'invalid'}]
        }
        mock_get.return_value = mock_response
        
        client = GitHubClient()
        with pytest.raises(ValueError, match="Assignee 'invalid_user' not found or invalid"):
            client.list_issues('mapau-demo-devin/running-buddy', assignee='invalid_user')

    @patch('requests.get')
    def test_list_issues_invalid_milestone(self, mock_get, mock_env_vars):
        """Test handling of invalid milestone filter"""
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            'message': 'Validation Failed',
            'errors': [{'field': 'milestone', 'code': 'invalid'}]
        }
        mock_get.return_value = mock_response
        
        client = GitHubClient()
        with pytest.raises(ValueError, match="Milestone '999' not found or invalid"):
            client.list_issues('mapau-demo-devin/running-buddy', milestone='999')

    @patch('requests.get')
    def test_get_issue_success(self, mock_get, mock_env_vars, sample_issues):
        """Test successful single issue retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_issues[0]
        mock_get.return_value = mock_response
        
        client = GitHubClient()
        issue = client.get_issue('mapau-demo-devin/running-buddy', 1)
        
        assert issue['number'] == 1
        assert issue['title'] == 'Fix login bug'
        mock_get.assert_called_once_with(
            'https://api.github.com/repos/mapau-demo-devin/running-buddy/issues/1',
            headers=client.headers
        )

    @patch('requests.get')
    def test_get_issue_not_found(self, mock_get, mock_env_vars):
        """Test handling of non-existent issue"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_get.return_value = mock_response
        
        client = GitHubClient()
        with pytest.raises(requests.exceptions.HTTPError):
            client.get_issue('mapau-demo-devin/running-buddy', 999)

    @patch('requests.get')
    def test_get_repository_success(self, mock_get, mock_env_vars, sample_repository):
        """Test successful repository retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_repository
        mock_get.return_value = mock_response
        
        client = GitHubClient()
        repo = client.get_repository('mapau-demo-devin/running-buddy')
        
        assert repo['name'] == 'running-buddy'
        assert repo['full_name'] == 'mapau-demo-devin/running-buddy'

    @patch('requests.get')
    def test_has_many_issues_true(self, mock_get, mock_env_vars, sample_issues):
        """Test has_many_issues returns True when threshold exceeded"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_issues * 5  # 15 issues
        mock_response.headers = {'link': 'rel="next"'}
        mock_get.return_value = mock_response
        
        client = GitHubClient()
        result = client.has_many_issues('mapau-demo-devin/running-buddy', threshold=10)
        
        assert result is True

    @patch('requests.get')
    def test_has_many_issues_false(self, mock_get, mock_env_vars, sample_issues):
        """Test has_many_issues returns False when threshold not exceeded"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_issues[:2]  # 2 issues
        mock_response.headers = {}
        mock_get.return_value = mock_response
        
        client = GitHubClient()
        result = client.has_many_issues('mapau-demo-devin/running-buddy', threshold=10)
        
        assert result is False
