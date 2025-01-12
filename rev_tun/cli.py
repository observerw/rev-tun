from pathlib import Path
from typing import Annotated, Iterable

import typer
from register import register_lookup
from rich.console import Console
from typer import Typer

from rev_tun.config import Config
from rev_tun.register import RegisterType

app = Typer()
console = Console()
err_console = Console(stderr=True)


@app.command()
def main(
    config_name: Annotated[
        str | None,
        typer.Argument(
            help="config name",
        ),
    ] = None,
    register_type: Annotated[
        RegisterType,
        typer.Option(
            "-r",
            "--register",
            help="register type",
            case_sensitive=False,
            show_default=True,
        ),
    ] = RegisterType.supervisor,
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
    config_paths: Iterable[Path] = (
        (conf_dir_path / f"{config_name}.toml",)
        if config_name
        else (path for path in conf_dir_path.iterdir() if path.suffix == ".toml")
    )

    register = register_lookup[register_type]
    for config_path in config_paths:
        try:
            config = Config.load(config_path)
            register.register(
                config,
                log_dir_path=log_dir_path,
            )
            console.print(f"{config.name} registered")
        except Exception as e:
            err_console.print(f"{config_path}: {e}")
