"""Tests for CLI commands."""

import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from github_issues_devin_automation.cli.commands import cli, calculate_confidence_score, explain_confidence_score


class TestCLICommands:
    """Test cases for CLI commands."""
    
    def test_list_issues_basic(self, mock_env_vars, mock_github_client):
        """Test basic list-issues command."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client):
            runner = CliRunner()
            result = runner.invoke(cli, ['list-issues', '--repo', 'mapau-demo-devin/running-buddy'])
            
            assert result.exit_code == 0
            assert 'Issues from mapau-demo-devin/running-buddy' in result.output
            mock_github_client.list_issues.assert_called_once()
    
    def test_list_issues_with_all_filters(self, mock_env_vars, mock_github_client):
        """Test list-issues command with all filters."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client):
            runner = CliRunner()
            result = runner.invoke(cli, [
                'list-issues',
                '--repo', 'mapau-demo-devin/running-buddy',
                '--state', 'closed',
                '--limit', '20',
                '--label', 'bug,enhancement',
                '--milestone', '1',
                '--assignee', 'developer1'
            ])
            
            assert result.exit_code == 0
            mock_github_client.list_issues.assert_called_with(
                'mapau-demo-devin/running-buddy',
                state='closed',
                limit=20,
                labels='bug,enhancement',
                milestone='1',
                assignee='developer1'
            )
    
    def test_list_issues_oppia_repo(self, mock_env_vars, mock_github_client):
        """Test list-issues command with oppia/oppia repository."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client):
            runner = CliRunner()
            result = runner.invoke(cli, ['list-issues', '--repo', 'oppia/oppia'])
            
            assert result.exit_code == 0
            assert 'Issues from oppia/oppia' in result.output
            mock_github_client.list_issues.assert_called_with(
                'oppia/oppia',
                state='open',
                limit=10,
                labels=None,
                milestone=None,
                assignee=None
            )
    
    @pytest.mark.parametrize("repo,filters", [
        ("mapau-demo-devin/running-buddy", {}),
        ("oppia/oppia", {}),
        ("mapau-demo-devin/running-buddy", {"label": "bug,enhancement"}),
        ("mapau-demo-devin/running-buddy", {"milestone": "1"}),
        ("mapau-demo-devin/running-buddy", {"assignee": "testuser"}),
        ("mapau-demo-devin/running-buddy", {"label": "bug", "milestone": "1", "assignee": "developer1"}),
        ("oppia/oppia", {"label": "enhancement", "milestone": "10"}),
    ])
    def test_list_issues_filter_combinations(self, mock_env_vars, mock_github_client, repo, filters):
        """Test list-issues command with various filter combinations."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client):
            runner = CliRunner()
            
            cmd_args = ['list-issues', '--repo', repo]
            for key, value in filters.items():
                cmd_args.extend([f'--{key}', value])
            
            result = runner.invoke(cli, cmd_args)
            
            assert result.exit_code == 0
            mock_github_client.list_issues.assert_called()
    
    def test_scope_issue_with_issue_number(self, mock_env_vars, mock_github_client, mock_devin_client, mock_user_input):
        """Test scope-issue command with specific issue number."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.DevinClient', return_value=mock_devin_client):
            
            runner = CliRunner()
            result = runner.invoke(cli, [
                'scope-issue',
                '--repo', 'mapau-demo-devin/running-buddy',
                '--issue-number', '1'
            ], input='n\n')
            
            assert result.exit_code == 0
            assert 'Analyzing issue #1' in result.output
            assert 'Implementation Confidence Score' in result.output
            mock_github_client.get_issue.assert_called_with('mapau-demo-devin/running-buddy', 1)
    
    def test_scope_issue_interactive_selection(self, mock_env_vars, mock_github_client, mock_devin_client, mock_user_input):
        """Test scope-issue command with interactive issue selection."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.commands.validate_repository_exists', return_value=(True, "")), \
             patch('github_issues_devin_automation.cli.commands.select_issue_interactively', return_value=1):
            
            runner = CliRunner()
            result = runner.invoke(cli, [
                'scope-issue',
                '--repo', 'mapau-demo-devin/running-buddy'
            ], input='n\n')
            
            assert result.exit_code == 0
            assert 'Analyzing issue #1' in result.output
    
    def test_scope_issue_with_filters(self, mock_env_vars, mock_github_client, mock_devin_client):
        """Test scope-issue command with filter parameters."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.commands.validate_repository_exists', return_value=(True, "")), \
             patch('github_issues_devin_automation.cli.commands.select_issue_interactively', return_value=1):
            
            runner = CliRunner()
            result = runner.invoke(cli, [
                'scope-issue',
                '--repo', 'mapau-demo-devin/running-buddy',
                '--label', 'bug',
                '--milestone', '1',
                '--assignee', 'developer1'
            ], input='n\n')
            
            assert result.exit_code == 0
    
    def test_scope_issue_create_devin_session(self, mock_env_vars, mock_github_client, mock_devin_client):
        """Test scope-issue command creating Devin session."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.DevinClient', return_value=mock_devin_client):
            
            runner = CliRunner()
            result = runner.invoke(cli, [
                'scope-issue',
                '--repo', 'mapau-demo-devin/running-buddy',
                '--issue-number', '1'
            ], input='y\n')
            
            assert result.exit_code == 0
            assert 'Creating Devin session' in result.output
            assert 'Created Devin session: test-session-123' in result.output
            mock_devin_client.create_session.assert_called_once()
    
    def test_complete_issue_with_issue_number(self, mock_env_vars, mock_github_client, mock_devin_client):
        """Test complete-issue command with specific issue number."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.DevinClient', return_value=mock_devin_client):
            
            runner = CliRunner()
            result = runner.invoke(cli, [
                'complete-issue',
                '--repo', 'mapau-demo-devin/running-buddy',
                '--issue-number', '1'
            ])
            
            assert result.exit_code == 0
            assert 'Processing issue #1' in result.output
            assert 'Created Devin session: test-session-123' in result.output
            mock_devin_client.create_session.assert_called_once()
    
    def test_complete_issue_interactive_selection(self, mock_env_vars, mock_github_client, mock_devin_client):
        """Test complete-issue command with interactive issue selection."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.commands.validate_repository_exists', return_value=(True, "")), \
             patch('github_issues_devin_automation.cli.commands.select_issue_interactively', return_value=2), \
             patch('github_issues_devin_automation.cli.commands._process_issue_with_devin') as mock_process:
            
            runner = CliRunner()
            result = runner.invoke(cli, [
                'complete-issue',
                '--repo', 'oppia/oppia'
            ])
            
            assert result.exit_code == 0
            mock_process.assert_called_once()
    
    def test_complete_issue_with_filters(self, mock_env_vars, mock_github_client, mock_devin_client):
        """Test complete-issue command with filter parameters."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.commands.validate_repository_exists', return_value=(True, "")), \
             patch('github_issues_devin_automation.cli.commands.select_issue_interactively', return_value=1), \
             patch('github_issues_devin_automation.cli.commands._process_issue_with_devin') as mock_process:
            
            runner = CliRunner()
            result = runner.invoke(cli, [
                'complete-issue',
                '--repo', 'mapau-demo-devin/running-buddy',
                '--label', 'enhancement',
                '--milestone', 'none',
                '--assignee', 'none'
            ])
            
            assert result.exit_code == 0
            mock_process.assert_called_once()
    
    def test_invalid_repo_format(self, mock_env_vars):
        """Test commands with invalid repository format."""
        runner = CliRunner()
        
        result = runner.invoke(cli, [
            'scope-issue',
            '--repo', 'invalid-repo-format'
        ])
        
        assert result.exit_code == 0
        assert 'Invalid repository format' in result.output
    
    def test_repository_not_found(self, mock_env_vars, mock_github_client):
        """Test commands with non-existent repository."""
        mock_github_client.get_repository.side_effect = Exception("Repository not found")
        
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.commands.validate_repository_exists', return_value=(False, "Repository not found")):
            
            runner = CliRunner()
            result = runner.invoke(cli, [
                'scope-issue',
                '--repo', 'nonexistent/repo'
            ])
            
            assert result.exit_code == 0
            assert 'Repository not found' in result.output


class TestConfidenceScore:
    """Test cases for confidence score calculation."""
    
    def test_calculate_confidence_score_bug_fix(self):
        """Test confidence score for bug fix issues."""
        issue = {
            'title': 'Fix bug in heart rate calculation',
            'body': 'The heart rate calculation is incorrect. Here is the code that needs fixing: ```python\ncode here\n```',
            'labels': [{'name': 'bug'}]
        }
        
        score, factors = calculate_confidence_score(issue)
        
        assert score >= 6.0  # Bug fixes typically have higher confidence
        assert any('Bug fix' in factor for factor in factors)
        assert any('Code examples provided' in factor for factor in factors)
    
    def test_calculate_confidence_score_documentation(self):
        """Test confidence score for documentation issues."""
        issue = {
            'title': 'Update documentation for API endpoints',
            'body': 'The documentation needs to be updated with new information.',
            'labels': [{'name': 'documentation'}]
        }
        
        score, factors = calculate_confidence_score(issue)
        
        assert score >= 6.0  # Documentation changes typically have high confidence
        assert any('Simple documentation' in factor for factor in factors)
    
    def test_calculate_confidence_score_complex_architecture(self):
        """Test confidence score for complex architectural changes."""
        issue = {
            'title': 'Refactor architecture for better scalability',
            'body': 'We need to redesign the entire architecture to support more users.',
            'labels': [{'name': 'enhancement'}]
        }
        
        score, factors = calculate_confidence_score(issue)
        
        assert score <= 5.0  # Complex changes should have lower confidence
        assert any('Complex architectural changes' in factor for factor in factors)
    
    def test_calculate_confidence_score_good_first_issue(self):
        """Test confidence score for good first issues."""
        issue = {
            'title': 'Add logging to user registration',
            'body': 'Add debug logging when users register to help with troubleshooting.',
            'labels': [{'name': 'good first issue'}]
        }
        
        score, factors = calculate_confidence_score(issue)
        
        assert score >= 6.0  # Good first issues should have higher confidence
        assert any('beginner-friendly' in factor for factor in factors)
    
    def test_explain_confidence_score_levels(self):
        """Test confidence score explanation for different levels."""
        level, color, description = explain_confidence_score(9.0, [])
        assert level == "Very High"
        assert color == "bright_green"
        assert "straightforward" in description
        
        level, color, description = explain_confidence_score(7.0, [])
        assert level == "High"
        assert color == "green"
        
        level, color, description = explain_confidence_score(5.0, [])
        assert level == "Medium"
        assert color == "yellow"
        
        level, color, description = explain_confidence_score(3.0, [])
        assert level == "Low"
        assert color == "orange"
        
        level, color, description = explain_confidence_score(1.0, [])
        assert level == "Very Low"
        assert color == "red"
