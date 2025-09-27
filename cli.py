#!/usr/bin/env python3
"""
GitHub Issues Devin Automation CLI

A command-line tool for integrating GitHub Issues with Devin AI.

This is a backward compatibility wrapper. The main implementation
has been moved to the github_issues_devin_automation package.
"""

from github_issues_devin_automation.cli.commands import cli

if __name__ == '__main__':
    cli()
