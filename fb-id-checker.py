import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.prompt import Prompt


def check_url(base_url, start_id, end_id, output_file_path, console):
    """
    Checks and validates Facebook profile URLs from a start ID to an end ID.

    :param base_url: String format of the base URL to check.
    :param start_id: ID to start search.
    :param end_id: ID to end search.
    :param output_file_path: Path to the output file.
    """
    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    with open(output_file_path, "a") as output_file:
        for i in range(start_id, end_id + 1):
            url = base_url.format(i)
            try:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    full_name_tags = soup.find_all("title")

                    if full_name_tags and not any(
                            excluded in full_name_tags[0].text
                            for excluded in ["Log into Facebook", "Facebook"]):
                        full_name = full_name_tags[0].text.strip()
                        output_file.write(
                            f"Valid URL found: {url} with name: {full_name}\n")
                        console.print(
                            f"[bold green]Valid URL found:[/bold green] {url} with name: {full_name}"
                        )
                    else:
                        # Optionally log URLs not meeting criteria.
                        pass
                else:
                    output_file.write(f"Page not found or error for: {url}\n")
            except requests.RequestException as e:
                output_file.write(
                    f"Request failed for: {url}, with exception: {str(e)}\n")


if __name__ == "__main__":
    console = Console()
    console.print("[bold magenta]Welcome to the FB ID Checker![/bold magenta]",
                  justify="center")

    base_url = "https://www.facebook.com/profile.php?id={}"

    search_type = Prompt.ask(
        "[bold cyan]Start search from (1) a single ID or (2) a range of IDs?[/bold cyan]",
        choices=["1", "2"])

    if search_type == "1":
        single_id = int(
            Prompt.ask("[bold cyan]Enter the starting ID[/bold cyan]"))
        num_check = int(
            Prompt.ask(
                "[bold cyan]How many IDs do you want to check starting from this ID?[/bold cyan]"
            ))
        start_id = single_id
        end_id = single_id + num_check - 1  # To ensure we check 'num_check' number of IDs including the start ID.
    else:
        start_id = int(
            Prompt.ask("[bold cyan]Enter the start of the range[/bold cyan]",
                       default="1"))
        end_id = int(
            Prompt.ask("[bold cyan]Enter the end of the range[/bold cyan]"))
        if start_id >= end_id:
            console.print(
                "[bold red]Start of range must be less than the end of range.[/bold red]"
            )
            exit()

    output_file_path = "combined_output.txt"

    check_url(base_url, start_id, end_id, output_file_path, console)
