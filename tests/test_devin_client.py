import pytest
import requests
from unittest.mock import Mock, patch
from devin_client import DevinClient


class TestDevinClient:
    
    def test_init_with_api_key(self, mock_env_vars):
        """Test DevinClient initialization with valid API key"""
        client = DevinClient()
        assert client.api_key == 'test_devin_api_key'
        assert client.base_url == 'https://api.devin.ai/v1'
        assert client.timeout == 120
        assert client.max_retries == 3
        assert 'Authorization' in client.headers
        assert 'Content-Type' in client.headers

    def test_init_without_api_key(self):
        """Test DevinClient initialization without API key raises error"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="DEVIN_API_KEY environment variable is required"):
                DevinClient()

    @patch('requests.request')
    def test_create_session_success(self, mock_request, mock_env_vars):
        """Test successful session creation"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'session_id': 'test-session-123',
            'url': 'https://app.devin.ai/sessions/test-session-123'
        }
        mock_request.return_value = mock_response
        
        client = DevinClient()
        result = client.create_session('Test prompt')
        
        assert result['session_id'] == 'test-session-123'
        assert result['url'] == 'https://app.devin.ai/sessions/test-session-123'
        mock_request.assert_called_once()
        
        call_args = mock_request.call_args
        assert call_args[1]['json']['prompt'] == 'Test prompt'

    @patch('requests.request')
    def test_create_session_with_kwargs(self, mock_request, mock_env_vars):
        """Test session creation with additional parameters"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'session_id': 'test-session-456',
            'url': 'https://app.devin.ai/sessions/test-session-456'
        }
        mock_request.return_value = mock_response
        
        client = DevinClient()
        result = client.create_session(
            'Test prompt',
            snapshot_id='snap-123',
            unlisted=True
        )
        
        assert result['session_id'] == 'test-session-456'
        call_args = mock_request.call_args
        assert call_args[1]['json']['prompt'] == 'Test prompt'
        assert call_args[1]['json']['snapshot_id'] == 'snap-123'
        assert call_args[1]['json']['unlisted'] is True

    @patch('requests.request')
    def test_send_message_success(self, mock_request, mock_env_vars):
        """Test successful message sending"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        client = DevinClient()
        result = client.send_message('test-session-123', 'Hello Devin')
        
        assert result is None  # send_message returns None
        mock_request.assert_called_once()
        
        call_args = mock_request.call_args
        assert call_args[1]['json']['message'] == 'Hello Devin'

    @patch('requests.request')
    def test_get_session_success(self, mock_request, mock_env_vars):
        """Test successful session retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'session_id': 'test-session-123',
            'status': 'active',
            'created_at': '2023-01-01T00:00:00Z'
        }
        mock_request.return_value = mock_response
        
        client = DevinClient()
        result = client.get_session('test-session-123')
        
        assert result['session_id'] == 'test-session-123'
        assert result['status'] == 'active'

    @patch('requests.request')
    def test_list_sessions_success(self, mock_request, mock_env_vars):
        """Test successful sessions listing"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'sessions': [
                {'session_id': 'session-1', 'status': 'active'},
                {'session_id': 'session-2', 'status': 'completed'}
            ]
        }
        mock_request.return_value = mock_response
        
        client = DevinClient()
        result = client.list_sessions(limit=5)
        
        assert len(result['sessions']) == 2
        call_args = mock_request.call_args
        assert call_args[1]['params']['limit'] == 5

    @patch('requests.request')
    def test_request_with_retry_timeout(self, mock_request, mock_env_vars):
        """Test retry logic on timeout"""
        mock_request.side_effect = [
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
            Mock(status_code=200, json=lambda: {'success': True})
        ]
        
        client = DevinClient()
        with patch('time.sleep'):  # Speed up test by mocking sleep
            result = client._make_request_with_retry('GET', 'https://test.com')
        
        assert result['success'] is True
        assert mock_request.call_count == 3

    @patch('requests.request')
    def test_request_with_retry_max_attempts(self, mock_request, mock_env_vars):
        """Test retry logic exhausts max attempts"""
        mock_request.side_effect = requests.exceptions.Timeout()
        
        client = DevinClient()
        with patch('time.sleep'):  # Speed up test by mocking sleep
            with pytest.raises(requests.exceptions.RequestException):
                client._make_request_with_retry('GET', 'https://test.com')
        
        assert mock_request.call_count == 3  # max_retries

    @patch('requests.request')
    def test_request_http_error_no_retry(self, mock_request, mock_env_vars):
        """Test HTTP errors are not retried"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_request.return_value = mock_response
        
        client = DevinClient()
        with pytest.raises(requests.exceptions.HTTPError):
            client._make_request_with_retry('GET', 'https://test.com')
        
        assert mock_request.call_count == 1  # No retry for HTTP errors
