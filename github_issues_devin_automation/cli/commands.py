"""
CLI command definitions for GitHub Issues Devin Automation.
"""

import click
import inquirer
import requests
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..clients.github_client import GitHubClient
from ..clients.devin_client import DevinClient
from ..prompts.templates import (
    COMPLETE_ISSUE_PROMPT,
    IMPLEMENTATION_PROMPT,
)
from .utils import (
    validate_repo_format,
    validate_issue_number,
    validate_repository_exists,
    handle_common_errors,
    _process_issue_with_devin,
    select_issue_interactively,
    console
)



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
@handle_common_errors
def list_issues(repo, state, limit, label, milestone, assignee):
    """List GitHub issues from a repository"""
    github_client = GitHubClient()

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
        labels_text = ', '.join([str(label['name']) for label in issue.get('labels', [])])
        milestone_text = str(issue.get('milestone', {}).get('title', '')) if issue.get('milestone') else ''
        assignee_text = str(issue.get('assignee', {}).get('login', '')) if issue.get('assignee') else ''

        table.add_row(
            str(issue['number']),
            str(issue['title'])[:50] + "..." if len(str(issue['title'])) > 50 else str(issue['title']),
            str(issue['state']),
            str(issue['user']['login']),
            labels_text[:20] + "..." if len(labels_text) > 20 else labels_text,
            milestone_text[:15] + "..." if len(milestone_text) > 15 else milestone_text,
            assignee_text
        )

    console.print(table)

    if github_client.has_many_issues(repo, threshold=limit, state=state, labels=label, milestone=milestone, assignee=assignee):
        console.print(f"\n[yellow]Note: Showing {limit} issues by default. You can view more issues by using the --limit argument.[/yellow]")

@cli.command()
@click.option('--repo', required=True, help='Repository in format owner/repo')
@click.option('--issue-number', type=int, help='Issue number to scope (optional - will prompt if not provided)')
@click.option('--limit', default=10, help='Maximum number of issues to display for selection')
@click.option('--label', help='Filter by label names (comma-separated for multiple)')
@click.option('--milestone', help='Filter by milestone (number, "*" for any, "none" for none)')
@click.option('--assignee', help='Filter by assignee (username, "*" for any, "none" for unassigned)')
def scope_issue(repo, issue_number, limit, label, milestone, assignee):
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
            issue_number = select_issue_interactively(github_client, repo, limit=limit, labels=label, milestone=milestone, assignee=assignee)
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

        devin_client = DevinClient()
        
        confidence_level, brief_analysis, session_id = devin_client.calculate_confidence_score_with_ai(issue)
        
        if confidence_level is None:
            console.print(f"[red]Failed to analyze issue with AI. Unable to extract confidence assessment from Devin session.[/red]")
            console.print(f"[yellow]Please try again or check the issue description for clarity.[/yellow]")
            return

        if confidence_level.lower() == 'high':
            color = "green"
        elif confidence_level.lower() == 'medium':
            color = "yellow"
        else:  # low
            color = "red"

        analysis_panel = Panel(
            f"[bold {color}]{confidence_level} Confidence[/bold {color}]\n\n"
            f"[dim]AI Analysis:[/dim]\n{brief_analysis}\n\n" +
            (f"[dim]Scoping session: {session_id}[/dim]" if session_id else ""),
            title="🎯 AI-Powered Issue Scoping",
            border_style=color
        )
        console.print(analysis_panel)

        console.print(f"\n[yellow]What would you like to do next?[/yellow]")
        
        try:
            questions = [
                inquirer.List('action',
                             message="Select an action",
                             choices=[
                                 ('📋 See detailed scope analysis', 'detailed_scope'),
                                 ('🚀 Open PR session (create implementation)', 'pr_session'),
                                 ('❌ Cancel', 'cancel')
                             ],
                             carousel=True)
            ]
            
            answers = inquirer.prompt(questions)
            if answers is None or answers['action'] == 'cancel':
                console.print("[dim]Operation cancelled.[/dim]")
                return
            
            action = answers['action']
            
        except KeyboardInterrupt:
            console.print("\n[dim]Operation cancelled.[/dim]")
            return

        if action == 'detailed_scope':
            console.print(f"\n[blue]Retrieving detailed scope analysis...[/blue]")
            
            try:
                detailed_scope, full_message = devin_client.wait_for_detailed_scope(session_id)
                
                if detailed_scope:
                    detailed_panel = Panel(
                        detailed_scope,
                        title="📊 Detailed Scope Analysis",
                        border_style="blue"
                    )
                    console.print(detailed_panel)
                    
                    if full_message and full_message != detailed_scope:
                        full_message_panel = Panel(
                            full_message,
                            title="💬 Full Devin Analysis Message",
                            border_style="dim"
                        )
                        console.print(full_message_panel)
                    
                    console.print(f"\n[dim]Full scoping session: {session_id}[/dim]")
                    
                    console.print(f"\n[yellow]Would you like to open a PR session to implement this issue?[/yellow]")
                    
                    try:
                        pr_questions = [
                            inquirer.List('pr_action',
                                         message="Select an action",
                                         choices=[
                                             ('🚀 Open PR session (create implementation)', 'create_pr'),
                                             ('❌ No, finish here', 'finish')
                                         ],
                                         carousel=True)
                        ]
                        
                        pr_answers = inquirer.prompt(pr_questions)
                        if pr_answers and pr_answers['pr_action'] == 'create_pr':
                            console.print(f"\n[blue]Creating implementation session for issue #{issue_number}...[/blue]")

                            _process_issue_with_devin(
                                repo,
                                issue_number,
                                IMPLEMENTATION_PROMPT,
                                confidence_level=confidence_level,
                                ai_analysis=brief_analysis
                            )
                        else:
                            console.print("[dim]Analysis complete.[/dim]")
                            
                    except KeyboardInterrupt:
                        console.print("\n[dim]Operation cancelled.[/dim]")
                        
                else:
                    console.print(f"[yellow]Detailed scope not yet available. Check the session later.[/yellow]")
                    console.print(f"[dim]Session ID: {session_id}[/dim]")
            
            except TimeoutError as e:
                console.print(f"[yellow]{e}[/yellow]")
                console.print(f"[dim]You can check the session later. Session ID: {session_id}[/dim]")
            except Exception as e:
                console.print(f"[red]Error retrieving detailed scope: {e}[/red]")
        
        elif action == 'pr_session':
            console.print(f"\n[blue]Creating implementation session for issue #{issue_number}...[/blue]")

            _process_issue_with_devin(
                repo,
                issue_number,
                IMPLEMENTATION_PROMPT,
                confidence_level=confidence_level,
                ai_analysis=brief_analysis
            )

    except requests.exceptions.HTTPError as e:
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
@click.option('--limit', default=10, help='Maximum number of issues to display for selection')
@click.option('--label', help='Filter by label names (comma-separated for multiple)')
@click.option('--milestone', help='Filter by milestone (number, "*" for any, "none" for none)')
@click.option('--assignee', help='Filter by assignee (username, "*" for any, "none" for unassigned)')
def complete_issue(repo, issue_number, limit, label, milestone, assignee):
    """Complete an issue using Devin AI"""
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
            issue_number = select_issue_interactively(github_client, repo, limit=limit, labels=label, milestone=milestone, assignee=assignee)
        except click.ClickException as e:
            console.print(f"[red]Error: {e}[/red]")
            return
    else:
        if not validate_issue_number(issue_number):
            console.print(f"[red]Error: Invalid issue number '{issue_number}'[/red]")
            console.print(f"[yellow]Issue numbers must be positive integers[/yellow]")
            return

    _process_issue_with_devin(repo, issue_number, COMPLETE_ISSUE_PROMPT)
