from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from typer import Typer

from rev_tun.config import Config

app = Typer()
console = Console()
err_console = Console(stderr=True)


@app.command()
def main(
    conf_dir_path: Annotated[
        Path,
        typer.Option(
            "--conf-dir",
            help="configuration directory path",
        ),
    ] = Path("/etc/supervisor/rev-tun"),
    log_dir_path: Annotated[
        Path,
        typer.Option(
            "--log-dir",
            help="log directory path",
        ),
    ] = Path("/var/log/rev-tun"),
):
    config_paths = (
        path
        for path in conf_dir_path.iterdir()  #
        if path.suffix == ".toml"
    )
    try:
        for config_path in config_paths:
            config = Config.load(config_path)
            config.register(
                log_dir_path=log_dir_path,
            )
            console.print(f"{config.name} registered")
    except Exception as e:
        err_console.print(e)
