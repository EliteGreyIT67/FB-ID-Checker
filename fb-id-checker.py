import asyncio
import os
import re
from dataclasses import dataclass

import aiohttp
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import (BarColumn, Progress, TextColumn,
                            TimeElapsedColumn, TimeRemainingColumn)
from rich.prompt import Prompt

@dataclass
class Config:
    """Holds configuration for the Facebook ID checker."""
    BASE_URL: str = "https://www.facebook.com/profile.php?id={}"
    HEADERS: dict = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    REQUEST_TIMEOUT: int = 10

class FacebookIdChecker:
    """
    Asynchronously checks for valid Facebook profile IDs using asyncio and aiohttp.

    Disclaimer: This script is for educational purposes only. Scraping websites
    like Facebook might be against their Terms of Service. The user is responsible
    for any misuse.
    """

    def __init__(self, max_concurrency: int = 100):
        self.config = Config()
        self.console = Console()
        self.max_concurrency = max_concurrency
        self.output_file_path = "valid_profiles.txt"
        self.start_id = 0
        self.end_id = 0

    async def _fetch_url(self, session: aiohttp.ClientSession, url: str) -> str | None:
        """Asynchronously fetches a URL and returns the response text."""
        try:
            async with session.get(url, timeout=self.config.REQUEST_TIMEOUT) as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientResponseError as e:
            self.console.log(f"[yellow]HTTP error for {url}: {e.status} {e.message}[/yellow]", style="dim")
        except asyncio.TimeoutError:
            self.console.log(f"[yellow]Timeout for URL: {url}[/yellow]", style="dim")
        except aiohttp.ClientError as e:
            self.console.log(f"[bright_red]Request failed for {url}: {e}[/bright_red]", style="dim")
        return None

    def _get_processed_ids(self) -> set[int]:
        """Reads the output file to find IDs that have already been processed."""
        processed_ids = set()
        if not os.path.exists(self.output_file_path):
            return processed_ids
        
        try:
            with open(self.output_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if match := re.search(r"ID: (\d+)", line):
                        processed_ids.add(int(match.group(1)))
        except (IOError, ValueError) as e:
            self.console.print(f"[bold red]Error reading processed IDs from {self.output_file_path}: {e}[/bold red]")
        return processed_ids

    async def _process_id(self, session: aiohttp.ClientSession, user_id: int, output_file) -> str | None:
        """Processes a single user ID to check for a valid profile."""
        url = self.config.BASE_URL.format(user_id)
        html_content = await self._fetch_url(session, url)

        if not html_content:
            return None

        try:
            soup = BeautifulSoup(html_content, "html.parser")
            title_tag = soup.find("title")
            
            if title_tag and title_tag.text:
                title_text = title_tag.text.strip()
                # Check for titles that indicate a valid user profile page.
                if "facebook" not in title_text.lower() and "log in" not in title_text.lower() and title_text:
                    full_name = title_text
                    output_line = f"ID: {user_id} | Name: {full_name} | URL: {url}\n"
                    # Note: File I/O is blocking. For extreme performance, a library like aiofiles
                    # could be used, but for this use case, standard I/O is acceptable.
                    output_file.write(output_line)
                    output_file.flush()
                    return f"[bold green]Found: {full_name}[/bold green] (ID: {user_id})"
        except Exception as e:
            return f"[red]Parsing error for ID {user_id}: {e}[/red]"
        return None

    def get_user_input(self) -> bool:
        """Greets the user and prompts for necessary inputs."""
        self.console.print("[bold magenta]Welcome to the Optimized FB ID Checker![/bold magenta]", justify="center")
        self.console.print("[cyan]Using asyncio for improved performance.[/cyan]", justify="center")
        self.console.print("[yellow]Disclaimer: Use responsibly and at your own risk.[/yellow]", justify="center")
        
        try:
            search_type = Prompt.ask(
                "[bold cyan]Select search type[/bold cyan]",
                choices=["1", "2"], default="2", show_choices=True,
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
            self.max_concurrency = int(Prompt.ask("[bold cyan]Enter max concurrent requests[/bold cyan]", default="100"))

        except (ValueError, TypeError):
            self.console.print("[bold red]Invalid input. Please enter a valid number.[/bold red]")
            return False
        except KeyboardInterrupt:
            self.console.print("\n[bold yellow]Operation cancelled by user.[/bold yellow]")
            return False
        return True

    async def run(self):
        """Main method to run the checker."""
        if not self.get_user_input():
            return

        processed_ids = self._get_processed_ids()
        if processed_ids:
            self.console.print(f"[bold yellow]Found {len(processed_ids)} previously checked IDs. Resuming session.[/bold yellow]")

        ids_to_check = [i for i in range(self.start_id, self.end_id + 1) if i not in processed_ids]
        
        if not ids_to_check:
            self.console.print("[bold green]All IDs in the specified range have already been checked.[/bold green]")
            return

        self.console.print(f"[cyan]Checking {len(ids_to_check)} IDs from {self.start_id} to {self.end_id} using {self.max_concurrency} concurrent tasks...[/cyan]")

        progress_columns = [
            TextColumn("[progress.description]{task.description}"), BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%", TextColumn("•"),
            TimeRemainingColumn(), TextColumn("•"), TimeElapsedColumn(),
        ]
        
        semaphore = asyncio.Semaphore(self.max_concurrency)
        
        async def process_with_semaphore(session, user_id, output_file):
            async with semaphore:
                return await self._process_id(session, user_id, output_file)

        try:
            with Progress(*progress_columns, console=self.console) as progress:
                task = progress.add_task("[yellow]Scanning...", total=len(ids_to_check))
                
                with open(self.output_file_path, "a", encoding="utf-8") as output_file:
                    async with aiohttp.ClientSession(headers=self.config.HEADERS) as session:
                        tasks = [
                            process_with_semaphore(session, user_id, output_file)
                            for user_id in ids_to_check
                        ]
                        
                        for future in asyncio.as_completed(tasks):
                            result = await future
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
    try:
        asyncio.run(FacebookIdChecker().run())
    except KeyboardInterrupt:
        pass
