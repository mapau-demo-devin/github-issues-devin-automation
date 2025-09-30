"""
Devin API client for creating and managing Devin sessions.
"""

import requests
import time
import re
from typing import Dict, Any, Tuple, Optional
from ..config.settings import get_devin_api_key, get_devin_api_base_url, get_devin_api_timeout, get_devin_api_max_retries

class DevinClient:
    def __init__(self):
        self.api_key = get_devin_api_key()
        self.base_url = get_devin_api_base_url()
        self.timeout = get_devin_api_timeout()
        self.max_retries = get_devin_api_max_retries()
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def create_session(self, prompt: str, **kwargs) -> Dict[Any, Any]:
        """
        Create a new Devin session.

        Args:
            prompt: Task description for Devin
            **kwargs: Additional session parameters (snapshot_id, unlisted, etc.)

        Returns:
            Session creation response with session_id and url
        """
        url = f"{self.base_url}/sessions"

        data = {
            'prompt': prompt,
            **kwargs
        }

        return self._make_request_with_retry('POST', url, json=data)

    def send_message(self, session_id: str, message: str) -> None:
        """
        Send a message to an existing Devin session.

        Args:
            session_id: ID of the session to send message to
            message: Message to send to Devin
        """
        url = f"{self.base_url}/sessions/{session_id}/message"

        data = {
            'message': message
        }

        self._make_request_with_retry('POST', url, json=data)

    def get_session(self, session_id: str) -> Dict[Any, Any]:
        """
        Get details about an existing session.

        Args:
            session_id: ID of the session to retrieve

        Returns:
            Session details dictionary
        """
        url = f"{self.base_url}/sessions/{session_id}"

        return self._make_request_with_retry('GET', url)

    def list_sessions(self, limit: int = 10) -> Dict[Any, Any]:
        """
        List recent Devin sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            Sessions list response
        """
        url = f"{self.base_url}/sessions"
        params = {'limit': limit}

        return self._make_request_with_retry('GET', url, params=params)

    def _make_request_with_retry(self, method: str, url: str, **kwargs) -> Dict[Any, Any]:
        """
        Make HTTP request with retry logic and proper timeout handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response JSON data

        Raises:
            requests.exceptions.RequestException: If all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()

                if method == 'POST' and 'message' in url:
                    return None

                return response.json()

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Request failed (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise requests.exceptions.RequestException(
                        f"Request failed after {self.max_retries} attempts. Last error: {str(e)}"
                    ) from e
            except requests.exceptions.HTTPError as e:
                raise e

        if last_exception:
            raise last_exception

    def wait_for_session_completion(self, session_id: str, timeout: int = 600, poll_interval: int = 5) -> Dict[Any, Any]:
        """
        Poll a session until it completes or times out.

        Args:
            session_id: ID of the session to monitor
            timeout: Maximum time to wait in seconds (default: 5 minutes)
            poll_interval: Time between polls in seconds (default: 5 seconds)

        Returns:
            Final session details dictionary

        Raises:
            TimeoutError: If session doesn't complete within timeout
            requests.exceptions.RequestException: If API calls fail
        """
        from rich.console import Console
        from rich.live import Live
        from rich.spinner import Spinner

        console = Console()
        start_time = time.time()

        with Live(Spinner("dots", text="Waiting for Devin to complete analysis..."), console=console, refresh_per_second=4) as live:
            while time.time() - start_time < timeout:
                try:
                    session = self.get_session(session_id)
                    status = session.get('status_enum', session.get('status', 'unknown'))

                    if status in ['finished', 'blocked', 'expired']:
                        live.stop()
                        return session
                    elif status in ['working']:
                        live.update(Spinner("dots", text=f"Devin is {status}..."))

                    time.sleep(poll_interval)

                except Exception as e:
                    live.stop()
                    raise e

            live.stop()
            raise TimeoutError(f"Session {session_id} did not complete within {timeout} seconds")

    def calculate_confidence_score_with_ai(self, issue: Dict[Any, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Scope GitHub issue using Devin AI and extract confidence level.
        
        Args:
            issue: GitHub issue dictionary
            
        Returns:
            Tuple of (confidence_level, brief_analysis, session_id) or (None, None, None) if failed
        """
        from rich.console import Console
        
        console = Console()
        console.print(f"[blue]Creating Devin session to scope issue...[/blue]")

        initial_prompt = f"""Analyze this GitHub issue and provide a quick initial confidence assessment. Please update the structured output immediately when you assign a confidence score and brief_analysis. Use the following format for the structured_output:.
{{
  "confidence_level": "High|Medium|Low",
  "brief_analysis": "2-3 sentence analysis of scope and complexity"
}}

Issue Title: {issue.get('title', '')}
Issue Body: {issue.get('body', '') or 'No description provided'}
Labels: {', '.join([label.get('name', '') for label in issue.get('labels', [])])}

**INSTRUCTIONS:**
1. Read the issue carefully
2. **AS SOON AS you determine your confidence level and scope, IMMEDIATELY update the structured output** with your confidence assessment and brief_analysis
3. Keep your analysis concise (2-3 sentences maximum)
4. Do NOT provide detailed analysis yet - just initial assessment
5. Do NOT create pull requests or implement solutions

**CRITICAL: Update the structured output immediately as soon as you have determined the confidence level and brief scope. Respond as fast as possible.**"""

        try:
            session = self.create_session(initial_prompt)
            session_id = session['session_id']

            console.print(f"[green]Created scoping session: {session_id}[/green]")
            console.print(f"[dim]Session URL: {session['url']}[/dim]")

            console.print(f"[blue]Waiting for Devin to assign a confidence score...[/blue]")
            confidence_level, brief_analysis = self._extract_initial_confidence(session_id)
            
            if not confidence_level or not brief_analysis:
                console.print(f"[red]Failed to extract initial assessment[/red]")
                return None, None, None

            detailed_analysis_prompt = f"""Now that you've provided the initial assessment, please provide a comprehensive detailed scope analysis using the following structured_output schema:
{{
  "detailed_analysis": "Comprehensive detailed scope analysis"
   "implementation_approach": "Detailed implementation approach"
  "testing_considerations": "Testing considerations"
}}

**INSTRUCTIONS FOR DETAILED ANALYSIS:**
1. Provide a comprehensive detailed scope assessment including:
   - Detailed implementation approach
   - Potential challenges and edge cases
   - Testing considerations
   - Files/components that need to be modified
   - Time breakdown by component
2. **UPDATE the structured output's detailed_scope_analysis field** when you complete the analysis
3. Do NOT create pull requests or implement solutions

**Take your time to be thorough and comprehensive.**"""
            
            self.send_message(session_id, detailed_analysis_prompt)

            return confidence_level, brief_analysis, session_id

        except Exception as e:
            console.print(f"[red]Error during AI analysis: {e}[/red]")
            return None, None, None

    def _extract_initial_confidence(self, session_id: str, timeout: int = 300, poll_interval: int = 10) -> Tuple[Optional[str], Optional[str]]:
        """Extract confidence level and brief analysis from structured output.
        
        Args:
            session_id: ID of the session to monitor
            timeout: Maximum time to wait in seconds (default: 5 minutes)
            poll_interval: Time between polls in seconds (default: 10 seconds)
            
        Returns:
            Tuple of (confidence_level, brief_analysis) or (None, None) if failed
        """
        from rich.console import Console
        from rich.live import Live
        from rich.spinner import Spinner

        console = Console()
        start_time = time.time()

        with Live(Spinner("dots", text="Waiting for Devin to assign a confidence score..."), console=console, refresh_per_second=4) as live:
            while time.time() - start_time < timeout:
                try:
                    session = self.get_session(session_id)
                    status = session.get('status_enum', session.get('status', 'unknown'))
                    
                    structured_output = session.get('structured_output', {})
                    if structured_output and 'confidence_level' in structured_output and 'brief_analysis' in structured_output:
                        confidence = structured_output['confidence_level']
                        brief_analysis = structured_output['brief_analysis']
                        if confidence in ['High', 'Medium', 'Low'] and brief_analysis and brief_analysis.strip():
                            live.stop()
                            return confidence, brief_analysis
                    
                    if status in ['finished', 'blocked', 'expired']:
                        live.stop()
                        break

                    time.sleep(poll_interval)

                except Exception as e:
                    live.stop()
                    raise e

            live.stop()
            return None, None


    def wait_for_detailed_scope(self, session_id: str, timeout: int = 600, poll_interval: int = 10) -> Tuple[Optional[str], Optional[str]]:
        """
        Poll a scoping session until detailed scope analysis is available in structured output.

        Args:
            session_id: ID of the session to monitor
            timeout: Maximum time to wait in seconds (default: 10 minutes)
            poll_interval: Time between polls in seconds (default: 10 seconds)

        Returns:
            Tuple of (detailed_scope_analysis, full_message) or (None, None) if not available

        Raises:
            TimeoutError: If detailed scope analysis doesn't become available within timeout
        """
        from rich.console import Console
        from rich.live import Live
        from rich.spinner import Spinner

        console = Console()
        start_time = time.time()
        
        initial_session = self.get_session(session_id)
        initial_structured_output = initial_session.get('structured_output', {})
        initial_brief = initial_structured_output.get('brief_analysis', '')

        with Live(Spinner("dots", text="Waiting for detailed scope analysis from Devin..."), console=console, refresh_per_second=4) as live:
            while time.time() - start_time < timeout:
                try:
                    session = self.get_session(session_id)
                    structured_output = session.get('structured_output', {})
                    
                    if structured_output and 'detailed_scope_analysis' in structured_output:
                        detailed_scope_analysis = structured_output['detailed_scope_analysis']
                        if (detailed_scope_analysis and 
                            detailed_scope_analysis.strip() and 
                            detailed_scope_analysis != initial_brief):
                            live.stop()
                            full_message = self._extract_detailed_from_messages(session)
                            return detailed_scope_analysis, full_message
                    
                    status = session.get('status_enum', session.get('status', 'unknown'))
                    if status in ['finished', 'blocked', 'expired']:
                        live.stop()
                        full_message = self._extract_detailed_from_messages(session)
                        return full_message, full_message  # Return same content as both structured and message

                    time.sleep(poll_interval)

                except Exception as e:
                    live.stop()
                    raise e

            live.stop()
            raise TimeoutError(f"Detailed scope analysis did not become available within {timeout} seconds")
    
    def _extract_detailed_from_messages(self, session: Dict[Any, Any]) -> str:
        """Extract detailed scope from session messages if not in structured output."""
        messages = session.get('messages', [])
        for message in reversed(messages):
            if message.get('type') == 'devin_message':
                content = message.get('message', '')
                if content.strip() and len(content.strip()) > 200:
                    return content
        
        return "Detailed scope analysis not yet available. The scoping session may still be in progress."
