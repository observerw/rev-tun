from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from typer import Typer

from rev_tun import utils
from rev_tun.config import init_conf_dir, load_configs
from rev_tun.register import RegisterType, register_lookup

app = Typer(add_completion=False)
console = Console()
err_console = Console(stderr=True)


@app.command()
def register(
    config_name: Annotated[
        str | None,
        typer.Argument(
            help="config name",
        ),
    ] = None,
    registrar_type: Annotated[
        RegisterType,
        typer.Option(
            "-r",
            "--registrar",
            help="register type",
            case_sensitive=False,
            show_default=True,
        ),
    ] = RegisterType.supervisor,
    conf_dir_path: Annotated[
        Path | None,
        typer.Option(
            "--conf-dir",
            help="configuration directory path",
        ),
    ] = None,
    conf_file_path: Annotated[
        Path | None,
        typer.Option(
            "--conf-file",
            help="single configuration file path",
        ),
    ] = None,
    log_dir_path: Annotated[
        Path,
        typer.Option(
            "--log-dir",
            help="log directory path",
        ),
    ] = Path("/var/log/rev-tun"),
):
    """
    Register configuration to supervisor, systemd, or others.
    """

    if not (path := utils.mutually_exclusive(conf_dir_path, log_dir_path)):
        raise ValueError("One of --conf-dir or --log-dir is required")

    if not path.exists():
        if path.is_file():
            raise ValueError(f"{path} not exists")
        if path.is_dir():
            raise FileNotFoundError(f"{path} not exists, consider running `init` first")

    registrar = register_lookup[registrar_type]

    for config in load_configs(path):
        if config_name and config_name != config.name:
            continue

        try:
            registrar.register(config, log_dir_path=log_dir_path)
            console.print(f"{config.name} registered")
        except Exception as e:
            err_console.print(f"config {config.name} failed to register: {e}")


@app.command()
def init(
    base_path: Annotated[
        Path | None,
        typer.Option(
            "--base-path",
            help="base path",
        ),
    ] = None,
):
    """
    Initialize configuration directory.
    """

    path = init_conf_dir(base_path)
    console.print(f"Configuration directory initialized at {path}")
