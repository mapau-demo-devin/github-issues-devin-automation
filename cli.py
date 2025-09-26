#!/usr/bin/env python3
"""
GitHub Issues Devin Automation CLI

A command-line tool for integrating GitHub Issues with Devin AI.
"""

import os
import re
import click
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import inquirer

from github_client import GitHubClient
from devin_client import DevinClient
from github_issues_devin_automation.cli.utils import (
    validate_repo_format,
    validate_issue_number, 
    validate_repository_exists
)
from github_issues_devin_automation.cli.commands import (
    calculate_confidence_score,
    explain_confidence_score
)

load_dotenv()
console = Console()


@click.group()
def cli():
    """GitHub Issues Devin Automation CLI"""
    pass

@cli.command()
@click.option('--repo', required=True, help='Repository in format owner/repo')
@click.option('--state', default='open', help='Issue state (open, closed, all)')
@click.option('--limit', default=10, help='Maximum number of issues to display')
@click.option('--label', help='Filter by label names (comma-separated for multiple)')
@click.option('--milestone', help='Filter by milestone (number, "*" for any, "none" for none)')
@click.option('--assignee', help='Filter by assignee (username, "*" for any, "none" for unassigned)')
def list_issues(repo, state, limit, label, milestone, assignee):
    """List GitHub issues from a repository"""
    github_client = GitHubClient()
    
    try:
        issues = github_client.list_issues(repo, state=state, limit=limit, labels=label, milestone=milestone, assignee=assignee)
        
        filter_info = []
        if label:
            filter_info.append(f"labels: {label}")
        if milestone:
            filter_info.append(f"milestone: {milestone}")
        if assignee:
            filter_info.append(f"assignee: {assignee}")
        
        title = f"Issues from {repo}"
        if filter_info:
            title += f" (filtered by {', '.join(filter_info)})"
        
        table = Table(title=title)
        table.add_column("Number", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("State", style="green")
        table.add_column("Author", style="yellow")
        table.add_column("Labels", style="magenta")
        table.add_column("Milestone", style="blue")
        table.add_column("Assignee", style="red")
        
        for issue in issues:
            labels_text = ', '.join([label['name'] for label in issue.get('labels', [])])
            milestone_text = issue.get('milestone', {}).get('title', '') if issue.get('milestone') else ''
            assignee_text = issue.get('assignee', {}).get('login', '') if issue.get('assignee') else ''
            
            table.add_row(
                str(issue['number']),
                issue['title'][:50] + "..." if len(issue['title']) > 50 else issue['title'],
                issue['state'],
                issue['user']['login'],
                labels_text[:20] + "..." if len(labels_text) > 20 else labels_text,
                milestone_text[:15] + "..." if len(milestone_text) > 15 else milestone_text,
                assignee_text
            )
        
        console.print(table)
        
        if github_client.has_many_issues(repo, threshold=limit, state=state, labels=label, milestone=milestone, assignee=assignee):
            console.print(f"\n[yellow]Note: Showing {limit} issues by default. You can view more issues by using the --limit argument.[/yellow]")
        
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print(f"[yellow]Tip: Check that the filter values exist in the repository[/yellow]")
    except Exception as e:
        console.print(f"[red]Error listing issues: {e}[/red]")

def select_issue_interactively(github_client: GitHubClient, repo: str, state: str = 'open', labels: str = None, milestone: str = None, assignee: str = None) -> int:
    """
    Interactively select an issue from a repository using arrow keys.
    
    Args:
        github_client: GitHub client instance
        repo: Repository in format 'owner/repo'
        state: Issue state to filter by
        labels: Comma-separated list of label names to filter by
        milestone: Milestone number, title, "*" for any, "none" for none
        assignee: Username, "*" for any assigned, "none" for unassigned
    
    Returns:
        Selected issue number
    """
    try:
        if github_client.has_many_issues(repo, threshold=10, state=state, labels=labels, milestone=milestone, assignee=assignee):
            console.print(f"[yellow]This repository has more than 10 {state} issues.[/yellow]")
            while True:
                try:
                    limit = click.prompt("How many issues would you like to display?", type=int, default=20)
                    if limit > 0:
                        break
                    console.print("[red]Please enter a positive number.[/red]")
                except click.Abort:
                    raise click.ClickException("Operation cancelled")
        else:
            limit = 50
        
        issues = github_client.list_issues(repo, state=state, limit=limit, labels=labels, milestone=milestone, assignee=assignee)
    except ValueError as e:
        raise click.ClickException(str(e))
    
    if not issues:
        raise click.ClickException(f"No {state} issues found in repository {repo}")
    
    issue_choices = []
    for issue in issues:
        title = issue['title']
        if len(title) > 60:
            title = title[:60] + "..."
        choice_text = f"#{issue['number']}: {title} (by {issue['user']['login']})"
        issue_choices.append((choice_text, issue['number']))
    
    try:
        console.print(f"\n[blue]Select an issue from {repo}[/blue]")
        console.print("[dim]Use arrow keys to navigate, Enter to select[/dim]\n")
        
        questions = [
            inquirer.List('issue',
                         message="Select an issue",
                         choices=issue_choices,
                         carousel=True)
        ]
        
        answers = inquirer.prompt(questions)
        if answers is None:
            raise click.ClickException("Operation cancelled")
        
        return answers['issue']
        
    except KeyboardInterrupt:
        raise click.ClickException("Operation cancelled")


@cli.command()
@click.option('--repo', required=True, help='Repository in format owner/repo')
@click.option('--issue-number', type=int, help='Issue number to scope (optional - will prompt if not provided)')
@click.option('--label', help='Filter by label names (comma-separated for multiple)')
@click.option('--milestone', help='Filter by milestone (number, "*" for any, "none" for none)')
@click.option('--assignee', help='Filter by assignee (username, "*" for any, "none" for unassigned)')
def scope_issue(repo, issue_number, label, milestone, assignee):
    """Analyze issue complexity and provide confidence score"""
    if not validate_repo_format(repo):
        console.print(f"[red]Error: Invalid repository format '{repo}'[/red]")
        console.print(f"[yellow]Expected format: owner/repo (e.g., 'mapau-demo-devin/running-buddy')[/yellow]")
        return
    
    github_client = GitHubClient()
    
    repo_exists, repo_error = validate_repository_exists(github_client, repo)
    if not repo_exists:
        console.print(f"[red]Error: {repo_error}[/red]")
        console.print(f"[yellow]Tip: Verify the repository name and your access permissions[/yellow]")
        return
    
    if issue_number is None:
        try:
            issue_number = select_issue_interactively(github_client, repo, labels=label, milestone=milestone, assignee=assignee)
        except click.ClickException as e:
            console.print(f"[red]Error: {e}[/red]")
            return
    else:
        if not validate_issue_number(issue_number):
            console.print(f"[red]Error: Invalid issue number '{issue_number}'[/red]")
            console.print(f"[yellow]Issue numbers must be positive integers[/yellow]")
            return
    
    try:
        issue = github_client.get_issue(repo, issue_number)
        console.print(f"\n[blue]Analyzing issue #{issue_number}: {issue['title']}[/blue]")
        
        score, factors = calculate_confidence_score(issue)
        level, color, description = explain_confidence_score(score, factors)
        
        score_panel = Panel(
            f"[bold {color}]{level} Confidence ({score}/10)[/bold {color}]\n\n"
            f"{description}\n\n"
            f"[dim]Factors considered:[/dim]\n" + 
            "\n".join([f"• {factor}" for factor in factors]),
            title="🎯 Implementation Confidence Score",
            border_style=color
        )
        console.print(score_panel)
        
        console.print(f"\n[yellow]Would you like to create a Devin session to work on this issue?[/yellow]")
        user_input = click.prompt("Create Devin session? (y/N)", default="n", show_default=True)
        
        if user_input.lower() in ['y', 'yes']:
            console.print(f"\n[blue]Creating Devin session for issue #{issue_number}...[/blue]")
            
            devin_client = DevinClient()
            prompt = f"""
            Please implement a solution for this GitHub issue:
            
            Issue: {issue['title']}
            Description: {issue['body']}
            Repository: {repo}
            
            Confidence Score: {score}/10 ({level})
            Key factors: {', '.join(factors[:3])}
            
            Steps:
            1. Clone the repository
            2. Analyze the codebase
            3. Implement the requested feature/fix
            4. Create tests if appropriate
            5. Create a pull request
            """
            
            session = devin_client.create_session(prompt)
            console.print(f"[green]Created Devin session: {session['session_id']}[/green]")
            console.print(f"[blue]Session URL: {session['url']}[/blue]")
        else:
            console.print("[dim]Skipping Devin session creation.[/dim]")
        
    except requests.exceptions.HTTPError as e:
        # Note: After pre-flight repository validation passes, we assume 404 errors
        # from get_issue() indicate non-existent issues. However, edge cases exist:
        # - Different permissions (repo accessible but not specific issues)
        # - Timing issues (repo moved/renamed between repo check and issue check)
        # - API inconsistencies or temporary GitHub API issues
        # - Private issues visible only to certain users
        if e.response.status_code == 404:
            console.print(f"[red]Error: Issue #{issue_number} not found in repository {repo}[/red]")
            console.print(f"[yellow]Tip: Use 'list-issues --repo {repo}' to see available issues[/yellow]")
        else:
            console.print(f"[red]HTTP Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Error scoping issue: {e}[/red]")

@cli.command()
@click.option('--repo', required=True, help='Repository in format owner/repo')
@click.option('--issue-number', type=int, help='Issue number to complete (optional - will prompt if not provided)')
@click.option('--label', help='Filter by label names (comma-separated for multiple)')
@click.option('--milestone', help='Filter by milestone (number, "*" for any, "none" for none)')
@click.option('--assignee', help='Filter by assignee (username, "*" for any, "none" for unassigned)')
def complete_issue(repo, issue_number, label, milestone, assignee):
    """Complete an issue using Devin AI"""
    if not validate_repo_format(repo):
        console.print(f"[red]Error: Invalid repository format '{repo}'[/red]")
        console.print(f"[yellow]Expected format: owner/repo (e.g., 'mapau-demo-devin/running-buddy')[/yellow]")
        return
    
    github_client = GitHubClient()
    devin_client = DevinClient()
    
    repo_exists, repo_error = validate_repository_exists(github_client, repo)
    if not repo_exists:
        console.print(f"[red]Error: {repo_error}[/red]")
        console.print(f"[yellow]Tip: Verify the repository name and your access permissions[/yellow]")
        return
    
    if issue_number is None:
        try:
            issue_number = select_issue_interactively(github_client, repo, labels=label, milestone=milestone, assignee=assignee)
        except click.ClickException as e:
            console.print(f"[red]Error: {e}[/red]")
            return
    else:
        if not validate_issue_number(issue_number):
            console.print(f"[red]Error: Invalid issue number '{issue_number}'[/red]")
            console.print(f"[yellow]Issue numbers must be positive integers[/yellow]")
            return
    
    try:
        issue = github_client.get_issue(repo, issue_number)
        console.print(f"[blue]Completing issue #{issue_number}: {issue['title']}[/blue]")
        
        prompt = f"""
        Please implement a solution for this GitHub issue:
        
        Issue: {issue['title']}
        Description: {issue['body']}
        Repository: {repo}
        
        Steps:
        1. Clone the repository
        2. Analyze the codebase
        3. Implement the requested feature/fix
        4. Create tests if appropriate
        5. Create a pull request
        """
        
        session = devin_client.create_session(prompt)
        console.print(f"[green]Created Devin session: {session['session_id']}[/green]")
        console.print(f"[blue]Session URL: {session['url']}[/blue]")
        
    except requests.exceptions.HTTPError as e:
        # Note: After pre-flight repository validation passes, we assume 404 errors
        # from get_issue() indicate non-existent issues. However, edge cases exist:
        # - Different permissions (repo accessible but not specific issues)
        # - Timing issues (repo moved/renamed between repo check and issue check)
        # - API inconsistencies or temporary GitHub API issues
        # - Private issues visible only to certain users
        if e.response.status_code == 404:
            console.print(f"[red]Error: Issue #{issue_number} not found in repository {repo}[/red]")
            console.print(f"[yellow]Tip: Use 'list-issues --repo {repo}' to see available issues[/yellow]")
        else:
            console.print(f"[red]HTTP Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Error completing issue: {e}[/red]")

if __name__ == '__main__':
    cli()
