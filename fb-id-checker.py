import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.prompt import Prompt
from concurrent.futures import ThreadPoolExecutor


def fetch_url(url, headers):
    """Fetch a URL and return the response or an exception."""
    try:
        response = requests.get(url, headers=headers, timeout=5)
        return response
    except requests.RequestException as e:
        return str(e)


def process_url(base_url, user_id, headers, output_file, console):
    """Process a single URL and validate its content."""
    url = base_url.format(user_id)
    response = fetch_url(url, headers)
    
    if isinstance(response, requests.Response):
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            title_tag = soup.find("title")
            if title_tag and "Log into Facebook" not in title_tag.text and "Facebook" not in title_tag.text:
                full_name = title_tag.text.strip()
                output_file.write(f"Valid URL found: {url} with name: {full_name}\n")
                console.print(f"[bold green]Valid URL found:[/bold green] {url} with name: {full_name}")
            else:
                output_file.write(f"Invalid profile or no name for: {url}\n")
        else:
            output_file.write(f"Error {response.status_code} for: {url}\n")
    else:
        # Log the exception
        output_file.write(f"Request failed for: {url}, with exception: {response}\n")


def check_urls(base_url, start_id, end_id, output_file_path, console, max_threads=5):
    """Check Facebook profile URLs in a given range."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    with open(output_file_path, "a") as output_file:
        with ThreadPoolExecutor(max_threads) as executor:
            for user_id in range(start_id, end_id + 1):
                executor.submit(process_url, base_url, user_id, headers, output_file, console)


if __name__ == "__main__":
    console = Console()
    console.print("[bold magenta]Welcome to the FB ID Checker![/bold magenta]", justify="center")

    base_url = "https://www.facebook.com/profile.php?id={}"

    search_type = Prompt.ask(
        "[bold cyan]Start search from (1) a single ID or (2) a range of IDs?[/bold cyan]",
        choices=["1", "2"]
    )

    if search_type == "1":
        single_id = int(Prompt.ask("[bold cyan]Enter the starting ID[/bold cyan]"))
        num_check = int(Prompt.ask("[bold cyan]How many IDs do you want to check starting from this ID?[/bold cyan]"))
        start_id = single_id
        end_id = single_id + num_check - 1
    else:
        start_id = int(Prompt.ask("[bold cyan]Enter the start of the range[/bold cyan]", default="1"))
        end_id = int(Prompt.ask("[bold cyan]Enter the end of the range[/bold cyan]"))
        if start_id >= end_id:
            console.print("[bold red]Start of range must be less than the end of range.[/bold red]")
            exit()

    output_file_path = Prompt.ask("[bold cyan]Enter the output file path[/bold cyan]", default="combined_output.txt")
    max_threads = int(Prompt.ask("[bold cyan]Enter the number of threads for parallel processing[/bold cyan]", default="5"))

    check_urls(base_url, start_id, end_id, output_file_path, console, max_threads)