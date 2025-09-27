"""Tests for Devin API client."""

import pytest
from unittest.mock import Mock, patch
import requests
import time
from github_issues_devin_automation.clients.devin_client import DevinClient


class TestDevinClient:
    """Test cases for DevinClient."""
    
    def test_init_with_config(self, mock_env_vars):
        """Test DevinClient initialization with configuration."""
        client = DevinClient()
        assert client.api_key == 'test_devin_api_key'
        assert client.base_url == 'https://test-api.devin.ai/v1'
        assert client.timeout == 30
        assert client.max_retries == 2
        assert 'Authorization' in client.headers
        assert client.headers['Authorization'] == 'Bearer test_devin_api_key'
    
    def test_create_session_success(self, mock_env_vars):
        """Test successful session creation."""
        with patch('requests.request') as mock_request:
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
            assert 'url' in result
            mock_request.assert_called_once()
    
    def test_create_session_with_kwargs(self, mock_env_vars):
        """Test session creation with additional parameters."""
        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'session_id': 'test-123'}
            mock_request.return_value = mock_response
            
            client = DevinClient()
            client.create_session('Test prompt', unlisted=True, snapshot_id='snap-123')
            
            call_args = mock_request.call_args
            json_data = call_args[1]['json']
            
            assert json_data['prompt'] == 'Test prompt'
            assert json_data['unlisted'] is True
            assert json_data['snapshot_id'] == 'snap-123'
    
    def test_send_message_success(self, mock_env_vars):
        """Test successful message sending."""
        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_request.return_value = mock_response
            
            client = DevinClient()
            result = client.send_message('session-123', 'Test message')
            
            assert result is None
            mock_request.assert_called_once()
    
    def test_get_session_success(self, mock_env_vars):
        """Test successful session retrieval."""
        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'session_id': 'session-123',
                'status': 'active'
            }
            mock_request.return_value = mock_response
            
            client = DevinClient()
            result = client.get_session('session-123')
            
            assert result['session_id'] == 'session-123'
            assert result['status'] == 'active'
    
    def test_list_sessions_success(self, mock_env_vars):
        """Test successful sessions listing."""
        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'sessions': [
                    {'session_id': 'session-1'},
                    {'session_id': 'session-2'}
                ]
            }
            mock_request.return_value = mock_response
            
            client = DevinClient()
            result = client.list_sessions(limit=5)
            
            assert 'sessions' in result
            assert len(result['sessions']) == 2
            
            call_args = mock_request.call_args
            params = call_args[1]['params']
            assert params['limit'] == 5
    
    def test_retry_logic_success_after_failure(self, mock_env_vars):
        """Test retry logic succeeds after initial failure."""
        with patch('requests.request') as mock_request, \
             patch('time.sleep') as mock_sleep:
            
            mock_response_fail = Mock()
            mock_response_fail.side_effect = requests.exceptions.Timeout()
            
            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {'session_id': 'test-123'}
            
            mock_request.side_effect = [
                requests.exceptions.Timeout(),
                mock_response_success
            ]
            
            client = DevinClient()
            result = client.create_session('Test prompt')
            
            assert result['session_id'] == 'test-123'
            assert mock_request.call_count == 2
            mock_sleep.assert_called_once_with(1)  # 2^0 = 1 second wait
    
    def test_retry_logic_max_retries_exceeded(self, mock_env_vars):
        """Test retry logic fails after max retries exceeded."""
        with patch('requests.request') as mock_request, \
             patch('time.sleep') as mock_sleep:
            
            mock_request.side_effect = requests.exceptions.Timeout()
            
            client = DevinClient()
            
            with pytest.raises(requests.exceptions.RequestException, match="Request failed after 2 attempts"):
                client.create_session('Test prompt')
            
            assert mock_request.call_count == 2  # max_retries = 2
            assert mock_sleep.call_count == 1  # Only sleep between retries
    
    def test_retry_logic_http_error_no_retry(self, mock_env_vars):
        """Test HTTP errors are not retried."""
        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
            mock_request.return_value = mock_response
            
            client = DevinClient()
            
            with pytest.raises(requests.exceptions.HTTPError):
                client.create_session('Test prompt')
            
            assert mock_request.call_count == 1  # No retries for HTTP errors
    
    def test_timeout_configuration(self, mock_env_vars):
        """Test timeout is properly configured in requests."""
        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'session_id': 'test-123'}
            mock_request.return_value = mock_response
            
            client = DevinClient()
            client.create_session('Test prompt')
            
            call_args = mock_request.call_args
            assert call_args[1]['timeout'] == 30
    
    def test_headers_configuration(self, mock_env_vars):
        """Test headers are properly configured in requests."""
        with patch('requests.request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'session_id': 'test-123'}
            mock_request.return_value = mock_response
            
            client = DevinClient()
            client.create_session('Test prompt')
            
            call_args = mock_request.call_args
            headers = call_args[1]['headers']
            assert headers['Authorization'] == 'Bearer test_devin_api_key'
            assert headers['Content-Type'] == 'application/json'
