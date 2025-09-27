"""Tests for CLI utility functions."""

import pytest
from unittest.mock import Mock, patch
import requests
import click
from github_issues_devin_automation.cli.utils import (
    validate_repo_format,
    validate_issue_number,
    validate_repository_exists,
    handle_common_errors,
    _process_issue_with_devin,
    select_issue_interactively
)


class TestValidationFunctions:
    """Test cases for validation functions."""
    
    @pytest.mark.parametrize("repo,expected", [
        ("owner/repo", True),
        ("mapau-demo-devin/running-buddy", True),
        ("oppia/oppia", True),
        ("user123/my-repo_name", True),
        ("invalid-repo", False),
        ("owner/", False),
        ("/repo", False),
        ("owner//repo", False),
        ("", False),
        ("owner/repo/extra", False),
    ])
    def test_validate_repo_format(self, repo, expected):
        """Test repository format validation."""
        assert validate_repo_format(repo) == expected
    
    @pytest.mark.parametrize("issue_number,expected", [
        (1, True),
        (100, True),
        (999999, True),
        (0, False),
        (-1, False),
        (-100, False),
    ])
    def test_validate_issue_number(self, issue_number, expected):
        """Test issue number validation."""
        assert validate_issue_number(issue_number) == expected
    
    def test_validate_repository_exists_success(self, mock_env_vars):
        """Test successful repository validation."""
        mock_client = Mock()
        mock_client.get_repository.return_value = {'name': 'test-repo'}
        
        exists, error = validate_repository_exists(mock_client, 'owner/repo')
        
        assert exists is True
        assert error == ""
        mock_client.get_repository.assert_called_once_with('owner/repo')
    
    def test_validate_repository_exists_not_found(self, mock_env_vars):
        """Test repository not found validation."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_client.get_repository.side_effect = requests.exceptions.HTTPError(response=mock_response)
        
        exists, error = validate_repository_exists(mock_client, 'owner/nonexistent')
        
        assert exists is False
        assert "not found or not accessible" in error
    
    def test_validate_repository_exists_access_denied(self, mock_env_vars):
        """Test repository access denied validation."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 403
        mock_client.get_repository.side_effect = requests.exceptions.HTTPError(response=mock_response)
        
        exists, error = validate_repository_exists(mock_client, 'owner/private')
        
        assert exists is False
        assert "Access denied" in error
    
    def test_validate_repository_exists_auth_failed(self, mock_env_vars):
        """Test repository authentication failed validation."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_client.get_repository.side_effect = requests.exceptions.HTTPError(response=mock_response)
        
        exists, error = validate_repository_exists(mock_client, 'owner/repo')
        
        assert exists is False
        assert "Authentication failed" in error


class TestErrorHandling:
    """Test cases for error handling."""
    
    def test_handle_common_errors_decorator_success(self):
        """Test error handling decorator with successful function."""
        @handle_common_errors
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
    
    def test_handle_common_errors_decorator_404(self):
        """Test error handling decorator with 404 error."""
        @handle_common_errors
        def test_function():
            mock_response = Mock()
            mock_response.status_code = 404
            raise requests.exceptions.HTTPError(response=mock_response)
        
        with patch('github_issues_devin_automation.cli.utils.console') as mock_console:
            test_function()
            mock_console.print.assert_called()
    
    def test_handle_common_errors_decorator_general_exception(self):
        """Test error handling decorator with general exception."""
        @handle_common_errors
        def test_function():
            raise ValueError("Test error")
        
        with patch('github_issues_devin_automation.cli.utils.console') as mock_console:
            test_function()
            mock_console.print.assert_called()


class TestProcessIssueWithDevin:
    """Test cases for Devin issue processing."""
    
    def test_process_issue_with_devin_success(self, mock_env_vars, mock_github_client, mock_devin_client, mock_devin_session_response):
        """Test successful issue processing with Devin."""
        with patch('github_issues_devin_automation.cli.utils.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.DevinClient', return_value=mock_devin_client), \
             patch('github_issues_devin_automation.cli.utils.console') as mock_console:
            
            _process_issue_with_devin('mapau-demo-devin/running-buddy', 1, 'Test prompt: {title}')
            
            mock_github_client.get_issue.assert_called_once_with('mapau-demo-devin/running-buddy', 1)
            mock_devin_client.create_session.assert_called_once()
            mock_console.print.assert_called()
    
    def test_process_issue_with_devin_issue_not_found(self, mock_env_vars, mock_github_client, mock_devin_client):
        """Test issue processing when issue is not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_github_client.get_issue.side_effect = requests.exceptions.HTTPError(response=mock_response)
        
        with patch('github_issues_devin_automation.cli.utils.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.DevinClient', return_value=mock_devin_client), \
             patch('github_issues_devin_automation.cli.utils.console') as mock_console:
            
            _process_issue_with_devin('mapau-demo-devin/running-buddy', 999, 'Test prompt')
            
            mock_console.print.assert_called()
            mock_devin_client.create_session.assert_not_called()
    
    def test_process_issue_with_devin_session_kwargs(self, mock_env_vars, mock_github_client, mock_devin_client):
        """Test issue processing with session kwargs."""
        with patch('github_issues_devin_automation.cli.utils.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.DevinClient', return_value=mock_devin_client):
            
            _process_issue_with_devin(
                'mapau-demo-devin/running-buddy', 
                1, 
                'Test prompt: {title} - Score: {score}',
                score=8.5,
                level='High'
            )
            
            call_args = mock_devin_client.create_session.call_args[0]
            prompt = call_args[0]
            assert 'Score: 8.5' in prompt


class TestInteractiveIssueSelection:
    """Test cases for interactive issue selection."""
    
    def test_select_issue_interactively_success(self, mock_env_vars, mock_github_client, sample_github_issues):
        """Test successful interactive issue selection."""
        mock_github_client.has_many_issues.return_value = False
        mock_github_client.list_issues.return_value = sample_github_issues
        
        with patch('inquirer.prompt') as mock_inquirer, \
             patch('github_issues_devin_automation.cli.utils.console'):
            
            mock_inquirer.return_value = {'issue': 1}
            
            result = select_issue_interactively(mock_github_client, 'mapau-demo-devin/running-buddy')
            
            assert result == 1
            mock_inquirer.assert_called_once()
    
    def test_select_issue_interactively_many_issues(self, mock_env_vars, mock_github_client, sample_github_issues):
        """Test interactive selection when repository has many issues."""
        mock_github_client.has_many_issues.return_value = True
        mock_github_client.list_issues.return_value = sample_github_issues
        
        with patch('inquirer.prompt') as mock_inquirer, \
             patch('click.prompt') as mock_click_prompt, \
             patch('github_issues_devin_automation.cli.utils.console'):
            
            mock_click_prompt.return_value = 15
            mock_inquirer.return_value = {'issue': 2}
            
            result = select_issue_interactively(mock_github_client, 'mapau-demo-devin/running-buddy')
            
            assert result == 2
            mock_click_prompt.assert_called()
            mock_inquirer.assert_called_once()
    
    def test_select_issue_interactively_with_filters(self, mock_env_vars, mock_github_client, sample_github_issues):
        """Test interactive selection with filter parameters."""
        closed_issue = sample_github_issues[2]  # Issue #3 is already closed
        mock_github_client.has_many_issues.return_value = False
        mock_github_client.list_issues.return_value = [closed_issue]
        
        with patch('inquirer.prompt') as mock_inquirer, \
             patch('github_issues_devin_automation.cli.utils.console'):
            
            mock_inquirer.return_value = {'issue': 3}
            
            result = select_issue_interactively(
                mock_github_client,
                'mapau-demo-devin/running-buddy',
                state='closed',
                labels='documentation',
                milestone='2',
                assignee='developer2'
            )
            
            assert result == 3
    
    def test_select_issue_interactively_no_issues(self, mock_env_vars, mock_github_client):
        """Test interactive selection when no issues are found."""
        mock_github_client.has_many_issues.return_value = False
        mock_github_client.list_issues.return_value = []
        
        with pytest.raises(click.ClickException, match="No .* issues found"):
            select_issue_interactively(mock_github_client, 'mapau-demo-devin/running-buddy')
    
    def test_select_issue_interactively_cancelled(self, mock_env_vars, mock_github_client, sample_github_issues):
        """Test interactive selection when user cancels."""
        mock_github_client.has_many_issues.return_value = False
        mock_github_client.list_issues.return_value = sample_github_issues
        
        with patch('inquirer.prompt') as mock_inquirer, \
             patch('github_issues_devin_automation.cli.utils.console'):
            
            mock_inquirer.return_value = None  # User cancelled
            
            with pytest.raises(click.ClickException, match="Operation cancelled"):
                select_issue_interactively(mock_github_client, 'mapau-demo-devin/running-buddy')
    
    def test_select_issue_interactively_keyboard_interrupt(self, mock_env_vars, mock_github_client, sample_github_issues):
        """Test interactive selection with keyboard interrupt."""
        mock_github_client.has_many_issues.return_value = False
        mock_github_client.list_issues.return_value = sample_github_issues
        
        with patch('inquirer.prompt') as mock_inquirer, \
             patch('github_issues_devin_automation.cli.utils.console'):
            
            mock_inquirer.side_effect = KeyboardInterrupt()
            
            with pytest.raises(click.ClickException, match="Operation cancelled"):
                select_issue_interactively(mock_github_client, 'mapau-demo-devin/running-buddy')
    
    def test_select_issue_interactively_value_error(self, mock_env_vars, mock_github_client):
        """Test interactive selection with value error from filters."""
        mock_github_client.list_issues.side_effect = ValueError("Invalid assignee")
        
        with patch('github_issues_devin_automation.cli.utils.console'):
            with pytest.raises(click.ClickException, match="Invalid assignee"):
                select_issue_interactively(mock_github_client, 'mapau-demo-devin/running-buddy', assignee='nonexistent')
