import requests
import re
from bs4 import BeautifulSoup
from rich.console import Console
from rich.prompt import Prompt
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn
from concurrent.futures import ThreadPoolExecutor
import os
import sys

class FacebookIdChecker:
    """
    A class to check for valid Facebook profile IDs concurrently.

    This script attempts to determine if a Facebook profile ID corresponds to a
    real user account by checking the title of the resulting page.

    Disclaimer: Scraping websites like Facebook can be against their Terms of
    Service. This script is for educational purposes only. The user is
    responsible for any misuse. The script may stop working if Facebook
    changes its page structure or implements stricter anti-scraping measures.
    """

    def __init__(self, max_threads=10):
        self.base_url = "https://www.facebook.com/profile.php?id={}"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.console = Console()
        self.max_threads = max_threads
        self.output_file_path = "valid_profiles.txt"
        self.start_id = 0
        self.end_id = 0

    def _fetch_url(self, url):
        """
        Fetches a URL with a timeout and returns the response object or None.
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            return response
        except requests.RequestException as e:
            self.console.log(f"[bright_red]Request failed for {url}: {e}[/bright_red]", style="dim")
            return None

    def _get_processed_ids(self):
        """
        Reads the output file to find IDs that have already been processed
        to allow for resuming a previous session.
        """
        processed_ids = set()
        if not os.path.exists(self.output_file_path):
            return processed_ids
        
        try:
            with open(self.output_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    # Regex to find the ID in a line like: "ID: 12345 | Name: John Doe | URL: ..."
                    match = re.search(r"ID: (\d+)", line)
                    if match:
                        processed_ids.add(int(match.group(1)))
        except (IOError, ValueError) as e:
            self.console.print(f"[bold red]Error reading processed IDs from {self.output_file_path}: {e}[/bold red]")

        return processed_ids

    def _process_id(self, user_id, output_file):
        """
        Processes a single user ID to check for a valid profile.
        Writes valid profiles to the output file.
        """
        url = self.base_url.format(user_id)
        response = self._fetch_url(url)

        if response:
            try:
                soup = BeautifulSoup(response.text, "html.parser")
                title_tag = soup.find("title")
                
                if title_tag and title_tag.text:
                    title_text = title_tag.text.strip()
                    # A more robust check against common non-profile page titles.
                    if "facebook" not in title_text.lower() and "log in" not in title_text.lower() and len(title_text) > 0:
                        full_name = title_text
                        output_line = f"ID: {user_id} | Name: {full_name} | URL: {url}\n"
                        output_file.write(output_line)
                        output_file.flush() # Ensure it's written immediately
                        return f"[bold green]Found: {full_name}[/bold green] (ID: {user_id})"
            except Exception as e:
                return f"[red]Parsing error for ID {user_id}: {e}[/red]"
        return None

    def get_user_input(self):
        """
        Greets the user and prompts for all necessary inputs.
        Handles input validation.
        """
        self.console.print("[bold magenta]Welcome to the Improved FB ID Checker![/bold magenta]", justify="center")
        self.console.print("[yellow]Disclaimer: Use responsibly and at your own risk.[/yellow]", justify="center")
        
        try:
            search_type = Prompt.ask(
                "[bold cyan]Select search type[/bold cyan]",
                choices=["1", "2"],
                default="2",
                show_choices=True,
                description="1: Single ID + range, 2: ID Range"
            )

            if search_type == "1":
                single_id = int(Prompt.ask("[bold cyan]Enter the starting ID[/bold cyan]"))
                num_check = int(Prompt.ask("[bold cyan]How many IDs to check from start?[/bold cyan]"))
                self.start_id = single_id
                self.end_id = single_id + num_check - 1
            else:
                self.start_id = int(Prompt.ask("[bold cyan]Enter the start of the ID range[/bold cyan]", default="1"))
                self.end_id = int(Prompt.ask("[bold cyan]Enter the end of the ID range[/bold cyan]"))

            if self.start_id >= self.end_id:
                self.console.print("[bold red]Start ID must be less than the end ID.[/bold red]")
                return False

            self.output_file_path = Prompt.ask("[bold cyan]Enter the output file path[/bold cyan]", default="valid_profiles.txt")
            self.max_threads = int(Prompt.ask("[bold cyan]Enter the number of threads[/bold cyan]", default="10"))

        except (ValueError, TypeError):
            self.console.print("[bold red]Invalid input. Please enter a valid number.[/bold red]")
            return False
        except KeyboardInterrupt:
            self.console.print("\n[bold yellow]Operation cancelled by user.[/bold yellow]")
            return False
            
        return True

    def run(self):
        """
        Main method to run the checker.
        """
        if not self.get_user_input():
            return

        processed_ids = self._get_processed_ids()
        if processed_ids:
            self.console.print(f"[bold yellow]Found {len(processed_ids)} previously checked IDs. Resuming session.[/bold yellow]")

        ids_to_check = [i for i in range(self.start_id, self.end_id + 1) if i not in processed_ids]
        
        if not ids_to_check:
            self.console.print("[bold green]All IDs in the specified range have already been checked.[/bold green]")
            return

        self.console.print(f"[cyan]Checking {len(ids_to_check)} IDs from {self.start_id} to {self.end_id} using {self.max_threads} threads...[/cyan]")

        progress_columns = [
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TextColumn("•"),
            TimeRemainingColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
        ]
        
        try:
            with Progress(*progress_columns, console=self.console) as progress:
                task = progress.add_task("[yellow]Scanning...", total=len(ids_to_check))
                
                with open(self.output_file_path, "a", encoding="utf-8") as output_file:
                    with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                        futures = {executor.submit(self._process_id, user_id, output_file): user_id for user_id in ids_to_check}
                        
                        for future in futures:
                            result = future.result()
                            if result:
                                self.console.print(result)
                            progress.update(task, advance=1)

        except KeyboardInterrupt:
            self.console.print("\n[bold red]Process interrupted by user. Exiting.[/bold red]")
        except Exception as e:
            self.console.print(f"\n[bold red]An unexpected error occurred: {e}[/bold red]")
        finally:
            self.console.print(f"\n[bold magenta]Scan complete. Valid profiles saved to '{self.output_file_path}'[/bold magenta]")


if __name__ == "__main__":
    checker = FacebookIdChecker()
    checker.run()

