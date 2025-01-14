from pathlib import Path
from typing import Annotated

import typer
from register import register_lookup
from rich.console import Console
from typer import Typer

from rev_tun.config import init_conf_dir, load_configs
from rev_tun.register import RegisterType

app = Typer()
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
    ] = init_conf_dir(),
    log_dir_path: Annotated[
        Path,
        typer.Option(
            "--log-dir",
            help="log directory path",
        ),
    ] = Path("/var/log/rev-tun"),
):
    register = register_lookup[register_type]
    for config in load_configs(conf_dir_path):
        if config_name and config_name != config.name:
            continue

        try:
            register.register(
                config,
                log_dir_path=log_dir_path,
            )
            console.print(f"{config.name} registered")
        except Exception as e:
            err_console.print(f"config {config.name} failed to register: {e}")
