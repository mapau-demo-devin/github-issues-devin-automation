"""Integration tests for GitHub Issues Devin Automation CLI."""

import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from github_issues_devin_automation.cli.commands import cli


class TestIntegrationWorkflows:
    """Test cases for complete CLI workflows."""
    
    def test_complete_workflow_running_buddy(self, mock_env_vars, mock_github_client, mock_devin_client):
        """Test complete workflow: list issues -> scope issue -> complete issue for running-buddy."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.DevinClient', return_value=mock_devin_client):
            
            runner = CliRunner()
            
            result1 = runner.invoke(cli, ['list-issues', '--repo', 'mapau-demo-devin/running-buddy'])
            assert result1.exit_code == 0
            assert 'Issues from mapau-demo-devin/running-buddy' in result1.output
            
            result2 = runner.invoke(cli, [
                'scope-issue',
                '--repo', 'mapau-demo-devin/running-buddy',
                '--issue-number', '1'
            ], input='n\n')
            assert result2.exit_code == 0
            assert 'Implementation Confidence Score' in result2.output
            
            result3 = runner.invoke(cli, [
                'complete-issue',
                '--repo', 'mapau-demo-devin/running-buddy',
                '--issue-number', '1'
            ])
            assert result3.exit_code == 0
            assert 'Created Devin session' in result3.output
            
            assert mock_devin_client.create_session.call_count == 1
    
    def test_complete_workflow_oppia(self, mock_env_vars, mock_github_client, mock_devin_client):
        """Test complete workflow for oppia/oppia repository."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.DevinClient', return_value=mock_devin_client):
            
            runner = CliRunner()
            
            result1 = runner.invoke(cli, [
                'list-issues',
                '--repo', 'oppia/oppia',
                '--label', 'enhancement',
                '--state', 'open'
            ])
            assert result1.exit_code == 0
            assert 'Issues from oppia/oppia' in result1.output
            
            result2 = runner.invoke(cli, [
                'scope-issue',
                '--repo', 'oppia/oppia',
                '--issue-number', '101',
                '--label', 'enhancement'
            ], input='y\n')
            assert result2.exit_code == 0
            assert 'Creating Devin session' in result2.output
            
            assert mock_devin_client.create_session.call_count == 1
    
    def test_all_filter_combinations_running_buddy(self, mock_env_vars, mock_github_client):
        """Test all filter combinations on running-buddy repository."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client):
            runner = CliRunner()
            
            filter_combinations = [
                {},
                {'label': 'bug'},
                {'milestone': '1'},
                {'assignee': 'developer1'},
                {'label': 'bug', 'milestone': '1'},
                {'label': 'enhancement', 'assignee': 'developer1'},
                {'milestone': '1', 'assignee': 'developer1'},
                {'label': 'bug,enhancement', 'milestone': '1', 'assignee': 'developer1'},
                {'assignee': 'none'},
                {'milestone': 'none'},
                {'assignee': '*'},
                {'milestone': '*'},
            ]
            
            for filters in filter_combinations:
                cmd_args = ['list-issues', '--repo', 'mapau-demo-devin/running-buddy']
                for key, value in filters.items():
                    cmd_args.extend([f'--{key}', value])
                
                result = runner.invoke(cli, cmd_args)
                assert result.exit_code == 0, f"Failed with filters: {filters}"
                mock_github_client.list_issues.assert_called()
    
    def test_all_filter_combinations_oppia(self, mock_env_vars, mock_github_client):
        """Test all filter combinations on oppia/oppia repository."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client):
            runner = CliRunner()
            
            filter_combinations = [
                {},
                {'label': 'enhancement'},
                {'milestone': '10'},
                {'assignee': 'ui-developer'},
                {'label': 'bug,performance'},
                {'state': 'closed'},
                {'state': 'all', 'limit': '20'},
            ]
            
            for filters in filter_combinations:
                cmd_args = ['list-issues', '--repo', 'oppia/oppia']
                for key, value in filters.items():
                    cmd_args.extend([f'--{key}', value])
                
                result = runner.invoke(cli, cmd_args)
                assert result.exit_code == 0, f"Failed with filters: {filters}"
                mock_github_client.list_issues.assert_called()
    
    def test_error_scenarios(self, mock_env_vars, mock_github_client, mock_devin_client):
        """Test various error scenarios."""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['list-issues', '--repo', 'invalid-format'])
        assert result.exit_code == 0  # CLI handles error gracefully
        
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.commands.validate_repository_exists', return_value=(False, "Repository not found")):
            
            result = runner.invoke(cli, ['scope-issue', '--repo', 'nonexistent/repo'])
            assert result.exit_code == 0
            assert 'Repository not found' in result.output
        
        with patch('github_issues_devin_automation.cli.commands.validate_issue_number', return_value=False):
            result = runner.invoke(cli, [
                'scope-issue',
                '--repo', 'mapau-demo-devin/running-buddy',
                '--issue-number', '0'
            ])
            assert result.exit_code == 0
            assert 'Invalid issue number' in result.output
    
    def test_api_call_isolation(self, mock_env_vars, mock_github_client, mock_devin_client):
        """Test that no real API calls are made during testing."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.DevinClient', return_value=mock_devin_client), \
             patch('requests.get') as mock_requests_get, \
             patch('requests.post') as mock_requests_post:
            
            runner = CliRunner()
            
            runner.invoke(cli, ['list-issues', '--repo', 'mapau-demo-devin/running-buddy'])
            runner.invoke(cli, ['scope-issue', '--repo', 'mapau-demo-devin/running-buddy', '--issue-number', '1'], input='y\n')
            runner.invoke(cli, ['complete-issue', '--repo', 'oppia/oppia', '--issue-number', '101'])
            
            mock_requests_get.assert_not_called()
            mock_requests_post.assert_not_called()
            
            assert mock_github_client.list_issues.call_count >= 1
            assert mock_github_client.get_issue.call_count >= 2
            assert mock_devin_client.create_session.call_count >= 2
    
    def test_both_repositories_without_sessions(self, mock_env_vars, mock_github_client, mock_devin_client):
        """Test that both repositories can be tested without creating real sessions."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.DevinClient', return_value=mock_devin_client):
            
            runner = CliRunner()
            
            result1 = runner.invoke(cli, ['list-issues', '--repo', 'mapau-demo-devin/running-buddy'])
            assert result1.exit_code == 0
            
            result2 = runner.invoke(cli, [
                'scope-issue',
                '--repo', 'mapau-demo-devin/running-buddy',
                '--issue-number', '1'
            ], input='y\n')
            assert result2.exit_code == 0
            assert 'test-session-123' in result2.output
            
            result3 = runner.invoke(cli, ['list-issues', '--repo', 'oppia/oppia'])
            assert result3.exit_code == 0
            
            result4 = runner.invoke(cli, [
                'complete-issue',
                '--repo', 'oppia/oppia',
                '--issue-number', '101'
            ])
            assert result4.exit_code == 0
            assert 'test-session-123' in result4.output
            
            assert mock_devin_client.create_session.call_count == 2
            
            github_calls = [call[0] for call in mock_github_client.list_issues.call_args_list]
            assert any('running-buddy' in str(call) for call in github_calls)
            assert any('oppia' in str(call) for call in github_calls)
    
    def test_comprehensive_command_coverage(self, mock_env_vars, mock_github_client, mock_devin_client):
        """Test that all commands run without error with various configurations."""
        with patch('github_issues_devin_automation.cli.commands.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.GitHubClient', return_value=mock_github_client), \
             patch('github_issues_devin_automation.cli.utils.DevinClient', return_value=mock_devin_client), \
             patch('github_issues_devin_automation.cli.commands.validate_repository_exists', return_value=(True, "")), \
             patch('github_issues_devin_automation.cli.commands.select_issue_interactively', return_value=1):
            
            runner = CliRunner()
            
            test_cases = [
                ['list-issues', '--repo', 'mapau-demo-devin/running-buddy'],
                ['list-issues', '--repo', 'oppia/oppia', '--state', 'closed'],
                ['list-issues', '--repo', 'mapau-demo-devin/running-buddy', '--label', 'bug', '--limit', '20'],
                ['list-issues', '--repo', 'oppia/oppia', '--milestone', '10', '--assignee', 'ui-developer'],
                
                ['scope-issue', '--repo', 'mapau-demo-devin/running-buddy', '--issue-number', '1'],
                ['scope-issue', '--repo', 'oppia/oppia', '--issue-number', '101'],
                ['scope-issue', '--repo', 'mapau-demo-devin/running-buddy', '--label', 'enhancement'],
                
                ['complete-issue', '--repo', 'mapau-demo-devin/running-buddy', '--issue-number', '2'],
                ['complete-issue', '--repo', 'oppia/oppia', '--issue-number', '102'],
                ['complete-issue', '--repo', 'mapau-demo-devin/running-buddy', '--assignee', 'none'],
            ]
            
            for cmd_args in test_cases:
                result = runner.invoke(cli, cmd_args, input='n\n')
                assert result.exit_code == 0, f"Command failed: {' '.join(cmd_args)}"
            
            assert mock_github_client.list_issues.call_count >= 4
            assert mock_github_client.get_issue.call_count >= 4
