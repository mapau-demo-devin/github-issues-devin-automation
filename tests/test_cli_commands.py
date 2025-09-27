import pytest
import click
from click.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock
import requests

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cli import cli
from github_issues_devin_automation.cli.commands import calculate_confidence_score, explain_confidence_score


class TestCLICommands:
    
    def setup_method(self):
        """Set up test runner for each test"""
        self.runner = CliRunner()

    @patch('cli.GitHubClient')
    def test_list_issues_basic(self, mock_github_class, mock_env_vars, sample_issues):
        """Test basic list-issues command"""
        mock_client = Mock()
        mock_client.list_issues.return_value = sample_issues
        mock_client.has_many_issues.return_value = False
        mock_github_class.return_value = mock_client
        
        result = self.runner.invoke(cli, [
            'list-issues',
            '--repo', 'mapau-demo-devin/running-buddy'
        ])
        
        assert result.exit_code == 0
        assert 'Fix login' in result.output and 'bug' in result.output
        assert 'Add dark' in result.output and 'mode' in result.output
        mock_client.list_issues.assert_called_once_with(
            'mapau-demo-devin/running-buddy',
            state='open',
            limit=10,
            labels=None,
            milestone=None,
            assignee=None
        )

    @patch('cli.GitHubClient')
    def test_list_issues_with_all_filters(self, mock_github_class, mock_env_vars, sample_issues, test_repos, filter_combinations):
        """Test list-issues command with all filter combinations on both test repos"""
        mock_client = Mock()
        mock_client.list_issues.return_value = sample_issues
        mock_client.has_many_issues.return_value = False
        mock_github_class.return_value = mock_client
        
        for repo in test_repos:
            for filters in filter_combinations:
                cmd = ['list-issues', '--repo', repo]
                
                if 'label' in filters:
                    cmd.extend(['--label', filters['label']])
                if 'milestone' in filters:
                    cmd.extend(['--milestone', filters['milestone']])
                if 'assignee' in filters:
                    cmd.extend(['--assignee', filters['assignee']])
                
                result = self.runner.invoke(cli, cmd)
                assert result.exit_code == 0, f"Failed for repo {repo} with filters {filters}: {result.output}"

    @patch('cli.GitHubClient')
    def test_list_issues_error_handling(self, mock_github_class, mock_env_vars):
        """Test list-issues error handling"""
        mock_client = Mock()
        mock_client.list_issues.side_effect = ValueError("Assignee 'invalid_user' not found")
        mock_github_class.return_value = mock_client
        
        result = self.runner.invoke(cli, [
            'list-issues',
            '--repo', 'mapau-demo-devin/running-buddy',
            '--assignee', 'invalid_user'
        ])
        
        assert result.exit_code == 0  # CLI handles error gracefully
        assert 'Error:' in result.output
        assert 'invalid_user' in result.output

    @patch('cli.DevinClient')
    @patch('cli.GitHubClient')
    @patch('cli.validate_repository_exists')
    @patch('cli.validate_repo_format')
    @patch('cli.validate_issue_number')
    def test_scope_issue_basic(self, mock_validate_issue, mock_validate_repo, mock_validate_exists,
                              mock_github_class, mock_devin_class, mock_env_vars, sample_issues):
        """Test basic scope-issue command"""
        mock_validate_repo.return_value = True
        mock_validate_issue.return_value = True
        mock_validate_exists.return_value = (True, "")
        
        mock_github_client = Mock()
        mock_github_client.get_issue.return_value = sample_issues[0]
        mock_github_class.return_value = mock_github_client
        
        mock_devin_client = Mock()
        mock_devin_client.create_session.return_value = {
            'session_id': 'test-session-123',
            'url': 'https://app.devin.ai/sessions/test-session-123'
        }
        mock_devin_class.return_value = mock_devin_client
        
        result = self.runner.invoke(cli, [
            'scope-issue',
            '--repo', 'mapau-demo-devin/running-buddy',
            '--issue-number', '1'
        ], input='n\n')
        
        assert result.exit_code == 0
        assert 'Analyzing issue #1' in result.output
        assert 'Confidence' in result.output
        assert 'Skipping Devin session creation' in result.output
        mock_github_client.get_issue.assert_called_once_with('mapau-demo-devin/running-buddy', 1)
        mock_devin_client.create_session.assert_not_called()

    @patch('cli.DevinClient')
    @patch('cli.GitHubClient')
    @patch('cli.validate_repository_exists')
    @patch('cli.validate_repo_format')
    @patch('cli.validate_issue_number')
    def test_scope_issue_with_devin_session(self, mock_validate_issue, mock_validate_repo, mock_validate_exists,
                                           mock_github_class, mock_devin_class, mock_env_vars, sample_issues):
        """Test scope-issue command that creates Devin session"""
        mock_validate_repo.return_value = True
        mock_validate_issue.return_value = True
        mock_validate_exists.return_value = (True, "")
        
        mock_github_client = Mock()
        mock_github_client.get_issue.return_value = sample_issues[0]
        mock_github_class.return_value = mock_github_client
        
        mock_devin_client = Mock()
        mock_devin_client.create_session.return_value = {
            'session_id': 'test-session-123',
            'url': 'https://app.devin.ai/sessions/test-session-123'
        }
        mock_devin_class.return_value = mock_devin_client
        
        result = self.runner.invoke(cli, [
            'scope-issue',
            '--repo', 'mapau-demo-devin/running-buddy',
            '--issue-number', '1'
        ], input='y\n')
        
        assert result.exit_code == 0
        assert 'Creating Devin session' in result.output
        assert 'test-session-123' in result.output
        mock_devin_client.create_session.assert_called_once()

    @patch('cli.select_issue_interactively')
    @patch('cli.DevinClient')
    @patch('cli.GitHubClient')
    @patch('cli.validate_repository_exists')
    @patch('cli.validate_repo_format')
    def test_scope_issue_interactive_selection(self, mock_validate_repo, mock_validate_exists,
                                              mock_github_class, mock_devin_class, mock_interactive,
                                              mock_env_vars, sample_issues):
        """Test scope-issue with interactive issue selection"""
        mock_validate_repo.return_value = True
        mock_validate_exists.return_value = (True, "")
        mock_interactive.return_value = 1
        
        mock_github_client = Mock()
        mock_github_client.get_issue.return_value = sample_issues[0]
        mock_github_class.return_value = mock_github_client
        
        mock_devin_client = Mock()
        mock_devin_client.create_session.return_value = {
            'session_id': 'test-session-123',
            'url': 'https://app.devin.ai/sessions/test-session-123'
        }
        mock_devin_class.return_value = mock_devin_client
        
        result = self.runner.invoke(cli, [
            'scope-issue',
            '--repo', 'mapau-demo-devin/running-buddy'
        ], input='n\n')
        
        assert result.exit_code == 0
        mock_interactive.assert_called_once()

    @patch('cli.DevinClient')
    @patch('cli.GitHubClient')
    @patch('cli.validate_repository_exists')
    @patch('cli.validate_repo_format')
    @patch('cli.validate_issue_number')
    def test_complete_issue_basic(self, mock_validate_issue, mock_validate_repo, mock_validate_exists,
                                 mock_github_class, mock_devin_class, mock_env_vars, sample_issues):
        """Test basic complete-issue command"""
        mock_validate_repo.return_value = True
        mock_validate_issue.return_value = True
        mock_validate_exists.return_value = (True, "")
        
        mock_github_client = Mock()
        mock_github_client.get_issue.return_value = sample_issues[0]
        mock_github_class.return_value = mock_github_client
        
        mock_devin_client = Mock()
        mock_devin_client.create_session.return_value = {
            'session_id': 'test-session-456',
            'url': 'https://app.devin.ai/sessions/test-session-456'
        }
        mock_devin_class.return_value = mock_devin_client
        
        result = self.runner.invoke(cli, [
            'complete-issue',
            '--repo', 'mapau-demo-devin/running-buddy',
            '--issue-number', '1'
        ])
        
        assert result.exit_code == 0
        assert 'Completing issue #1' in result.output
        assert 'test-session-456' in result.output
        mock_github_client.get_issue.assert_called_once_with('mapau-demo-devin/running-buddy', 1)
        mock_devin_client.create_session.assert_called_once()

    @patch('cli.select_issue_interactively')
    @patch('cli.DevinClient')
    @patch('cli.GitHubClient')
    @patch('cli.validate_repository_exists')
    @patch('cli.validate_repo_format')
    def test_complete_issue_interactive_selection(self, mock_validate_repo, mock_validate_exists,
                                                 mock_github_class, mock_devin_class, mock_interactive,
                                                 mock_env_vars, sample_issues):
        """Test complete-issue with interactive issue selection"""
        mock_validate_repo.return_value = True
        mock_validate_exists.return_value = (True, "")
        mock_interactive.return_value = 2
        
        mock_github_client = Mock()
        mock_github_client.get_issue.return_value = sample_issues[1]
        mock_github_class.return_value = mock_github_client
        
        mock_devin_client = Mock()
        mock_devin_client.create_session.return_value = {
            'session_id': 'test-session-789',
            'url': 'https://app.devin.ai/sessions/test-session-789'
        }
        mock_devin_class.return_value = mock_devin_client
        
        result = self.runner.invoke(cli, [
            'complete-issue',
            '--repo', 'mapau-demo-devin/running-buddy'
        ])
        
        assert result.exit_code == 0
        mock_interactive.assert_called_once()
        mock_devin_client.create_session.assert_called_once()

    @patch('cli.GitHubClient')
    @patch('cli.validate_repository_exists')
    @patch('cli.validate_repo_format')
    def test_scope_issue_validation_errors(self, mock_validate_repo, mock_validate_exists,
                                          mock_github_class, mock_env_vars):
        """Test scope-issue validation error handling"""
        mock_validate_repo.return_value = False
        
        result = self.runner.invoke(cli, [
            'scope-issue',
            '--repo', 'invalid-repo-format',
            '--issue-number', '1'
        ])
        
        assert result.exit_code == 0
        assert 'Invalid repository format' in result.output
        
        mock_validate_repo.return_value = True
        mock_validate_exists.return_value = (False, "Repository 'test/repo' not found")
        
        result = self.runner.invoke(cli, [
            'scope-issue',
            '--repo', 'test/repo',
            '--issue-number', '1'
        ])
        
        assert result.exit_code == 0
        assert 'not found' in result.output

    @patch('cli.GitHubClient')
    @patch('cli.validate_repository_exists')
    @patch('cli.validate_repo_format')
    @patch('cli.validate_issue_number')
    def test_scope_issue_http_errors(self, mock_validate_issue, mock_validate_repo, mock_validate_exists,
                                    mock_github_class, mock_env_vars):
        """Test scope-issue HTTP error handling"""
        mock_validate_repo.return_value = True
        mock_validate_issue.return_value = True
        mock_validate_exists.return_value = (True, "")
        
        mock_github_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_github_client.get_issue.side_effect = http_error
        mock_github_class.return_value = mock_github_client
        
        result = self.runner.invoke(cli, [
            'scope-issue',
            '--repo', 'mapau-demo-devin/running-buddy',
            '--issue-number', '999'
        ])
        
        assert result.exit_code == 0
        assert 'Issue #999 not found' in result.output

    def test_all_commands_on_both_repos(self, mock_env_vars, test_repos):
        """Test that all commands can be invoked on both test repositories"""
        with patch('cli.GitHubClient') as mock_github_class, \
             patch('cli.DevinClient') as mock_devin_class, \
             patch('cli.validate_repository_exists') as mock_validate_exists, \
             patch('cli.validate_repo_format') as mock_validate_repo, \
             patch('cli.validate_issue_number') as mock_validate_issue:
            
            mock_validate_repo.return_value = True
            mock_validate_issue.return_value = True
            mock_validate_exists.return_value = (True, "")
            
            mock_github_client = Mock()
            mock_github_client.list_issues.return_value = []
            mock_github_client.has_many_issues.return_value = False
            mock_github_client.get_issue.return_value = {
                'number': 1, 'title': 'Test issue', 'body': 'Test body',
                'user': {'login': 'testuser'}, 'labels': [], 'milestone': None, 'assignee': None
            }
            mock_github_class.return_value = mock_github_client
            
            mock_devin_client = Mock()
            mock_devin_client.create_session.return_value = {
                'session_id': 'test-session', 'url': 'https://test.com'
            }
            mock_devin_class.return_value = mock_devin_client
            
            commands_to_test = [
                ['list-issues'],
                ['scope-issue', '--issue-number', '1'],
                ['complete-issue', '--issue-number', '1']
            ]
            
            for repo in test_repos:
                for cmd in commands_to_test:
                    full_cmd = cmd + ['--repo', repo]
                    if 'scope-issue' in cmd:
                        result = self.runner.invoke(cli, full_cmd, input='n\n')
                    else:
                        result = self.runner.invoke(cli, full_cmd)
                    
                    assert result.exit_code == 0, f"Command {cmd} failed for repo {repo}: {result.output}"


class TestConfidenceScoring:
    """Test confidence scoring functions separately"""
    
    def test_calculate_confidence_score_bug_fix(self):
        """Test confidence scoring for bug fixes"""
        issue = {
            'title': 'Fix login bug',
            'body': 'The login form validation is broken. Users can submit empty credentials.',
            'labels': [{'name': 'bug'}]
        }
        
        score, factors = calculate_confidence_score(issue)
        
        assert score >= 6.0  # Bug fixes should have higher confidence
        assert any('Bug fix' in factor for factor in factors)
        assert any('Confirmed bug' in factor for factor in factors)

    def test_calculate_confidence_score_feature_addition(self):
        """Test confidence scoring for feature additions"""
        issue = {
            'title': 'Add dark mode support',
            'body': 'Implement dark mode theme for better user experience.',
            'labels': [{'name': 'enhancement'}]
        }
        
        score, factors = calculate_confidence_score(issue)
        
        assert score >= 4.0  # Feature additions should have moderate confidence
        assert any('Feature addition' in factor for factor in factors)
        assert any('Feature enhancement' in factor for factor in factors)

    def test_calculate_confidence_score_good_first_issue(self):
        """Test confidence scoring for beginner-friendly issues"""
        issue = {
            'title': 'Fix typo in README',
            'body': 'There is a spelling mistake in the documentation.',
            'labels': [{'name': 'good first issue'}, {'name': 'documentation'}]
        }
        
        score, factors = calculate_confidence_score(issue)
        
        assert score >= 8.0  # Good first issues should have very high confidence
        assert any('beginner-friendly' in factor for factor in factors)
        assert any('documentation' in factor for factor in factors)

    def test_calculate_confidence_score_complex_architecture(self):
        """Test confidence scoring for complex architectural changes"""
        issue = {
            'title': 'Refactor architecture for microservices migration',
            'body': 'This is a breaking change that requires significant architectural redesign.',
            'labels': [{'name': 'breaking-change'}]
        }
        
        score, factors = calculate_confidence_score(issue)
        
        assert score <= 4.0  # Complex changes should have lower confidence
        assert any('architectural changes' in factor for factor in factors)

    def test_calculate_confidence_score_magic_numbers(self):
        """Test confidence scoring for magic number extraction"""
        issue = {
            'title': 'Extract magic numbers to constants',
            'body': 'Replace hardcoded values with named constants for better maintainability.',
            'labels': [{'name': 'refactor'}]
        }
        
        score, factors = calculate_confidence_score(issue)
        
        assert score >= 6.0  # Magic number extraction should have high confidence
        assert any('extracting constants' in factor for factor in factors)

    def test_explain_confidence_score_levels(self):
        """Test confidence score explanation levels"""
        level, color, description = explain_confidence_score(9.0, [])
        assert level == "Very High"
        assert color == "bright_green"
        assert "straightforward" in description
        
        level, color, description = explain_confidence_score(7.0, [])
        assert level == "High"
        assert color == "green"
        assert "good clarity" in description
        
        level, color, description = explain_confidence_score(5.0, [])
        assert level == "Medium"
        assert color == "yellow"
        assert "investigation" in description
        
        level, color, description = explain_confidence_score(3.0, [])
        assert level == "Low"
        assert color == "orange"
        assert "complex" in description
        
        level, color, description = explain_confidence_score(1.0, [])
        assert level == "Very Low"
        assert color == "red"
        assert "very complex" in description

    def test_confidence_score_bounds(self):
        """Test that confidence scores are properly bounded"""
        issue_minimal = {'title': '', 'body': '', 'labels': []}
        score, _ = calculate_confidence_score(issue_minimal)
        assert 1.0 <= score <= 10.0
        
        issue_maximal = {
            'title': 'Fix typo in documentation',
            'body': 'Simple spelling mistake in README file. ' + 'x' * 500,  # Long description
            'labels': [{'name': 'good first issue'}, {'name': 'bug'}, {'name': 'documentation'}]
        }
        score, _ = calculate_confidence_score(issue_maximal)
        assert 1.0 <= score <= 10.0
