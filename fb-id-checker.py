import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.prompt import Prompt


def check_url(base_url, start, end, output_file_path, console):
    """
    Checks and validates Facebook profile URLs in a given range.

    :param base_url: String format of the base URL to check.
    :param start: Start of the range.
    :param end: End of the range.
    :param output_file_path: Path to the output file.
    """
    headers = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    with open(output_file_path, "w") as output_file:
        for i in range(start, end + 1):
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
                        pass
                        # output_file.write(f"URL does not meet criteria: {url}\n")
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

    while True:
        start_range = int(
            Prompt.ask("[bold cyan]Enter the start of the range[/bold cyan]",
                       default="1"))
        end_range = int(
            Prompt.ask("[bold cyan]Enter the end of the range[/bold cyan]"))
        if start_range < end_range:
            break
        console.print(
            "[bold red]Start of range must be less than end of range.[/bold red]"
        )

    output_file_path = "combined_output.txt"

    check_url(base_url, start_range, end_range, output_file_path, console)
