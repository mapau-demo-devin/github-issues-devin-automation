#!/usr/bin/env python3
"""
GitHub Issues Devin Automation CLI

A command-line tool for integrating GitHub Issues with Devin AI.
"""

import os
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from github_client import GitHubClient
from devin_client import DevinClient

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
def list_issues(repo, state, limit):
    """List GitHub issues from a repository"""
    github_client = GitHubClient()
    
    try:
        issues = github_client.list_issues(repo, state=state, limit=limit)
        
        table = Table(title=f"Issues from {repo}")
        table.add_column("Number", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("State", style="green")
        table.add_column("Author", style="yellow")
        
        for issue in issues:
            table.add_row(
                str(issue['number']),
                issue['title'][:50] + "..." if len(issue['title']) > 50 else issue['title'],
                issue['state'],
                issue['user']['login']
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error listing issues: {e}[/red]")

@cli.command()
@click.option('--repo', required=True, help='Repository in format owner/repo')
@click.option('--issue-number', required=True, type=int, help='Issue number to scope')
def scope_issue(repo, issue_number):
    """Scope an issue using Devin AI and assign confidence score"""
    github_client = GitHubClient()
    devin_client = DevinClient()
    
    try:
        issue = github_client.get_issue(repo, issue_number)
        console.print(f"[blue]Scoping issue #{issue_number}: {issue['title']}[/blue]")
        
        prompt = f"""
        Please analyze this GitHub issue and provide:
        1. A detailed scope analysis
        2. A confidence score (1-10) for implementation difficulty
        3. Estimated time to complete
        4. Key technical considerations
        
        Issue: {issue['title']}
        Description: {issue['body']}
        Repository: {repo}
        """
        
        session = devin_client.create_session(prompt)
        console.print(f"[green]Created Devin session: {session['session_id']}[/green]")
        console.print(f"[blue]Session URL: {session['url']}[/blue]")
        
    except Exception as e:
        console.print(f"[red]Error scoping issue: {e}[/red]")

@cli.command()
@click.option('--repo', required=True, help='Repository in format owner/repo')
@click.option('--issue-number', required=True, type=int, help='Issue number to complete')
def complete_issue(repo, issue_number):
    """Complete an issue using Devin AI"""
    github_client = GitHubClient()
    devin_client = DevinClient()
    
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
        
    except Exception as e:
        console.print(f"[red]Error completing issue: {e}[/red]")

if __name__ == '__main__':
    cli()
