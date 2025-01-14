import shutil
from abc import ABC
from collections.abc import Iterable
from enum import Enum
from importlib import resources as res
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any, Self

import tomli
from const import options, ssh_options
from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator
from pydantic.networks import IPvAnyAddress

import rev_tun
import rev_tun.templates
from rev_tun.utils import check_root, convert_to, merge


class ConfigModel(BaseModel, ABC):
    @model_validator(mode="before")
    @classmethod
    def _transform(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        return {
            convert_to(key, "snake"): value  #
            for key, value in data.items()
        }

    @property
    def command(self) -> list[str]:
        return []

    def __str__(self) -> str:
        return " ".join(self.command)


class ForwardingMode(str, Enum):
    remote = "remote"
    local = "local"


class Ports(RootModel):
    root: list[int]

    @model_validator(mode="before")
    @classmethod
    def _parse(cls, data: Any) -> Any:
        if not isinstance(data, str):
            return data

        ports: list[int] = []
        for part in data.split(","):
            if "-" in part:
                start, end = map(int, part.split("-"))
                ports.extend(range(start, end + 1))
            else:
                ports.append(int(part))

        if not len(set(ports)) == len(ports):
            raise ValueError("Duplicate port number")

        return ports

    def match(self, remote_ports: "Ports") -> Iterable[tuple[int, int]]:
        if not self.is_match(remote_ports):
            raise ValueError(
                "The number of local ports does not match the number of remote ports"
            )

        yield from zip(self.root, remote_ports.root)

    def is_match(self, remote_ports: "Ports") -> bool:
        return len(self.root) == len(remote_ports.root)


class ServiceConfigOptions(ConfigModel):
    forwarding_mode: ForwardingMode = Field(
        default=ForwardingMode.remote,
        description="forwarding mode",
    )


class ServiceConfig(ServiceConfigOptions):
    enable: bool = Field(default=True, description="enable service")

    local_ports: Ports = Field(description="local ports")
    local_addr: IPvAnyAddress = Field(
        default=IPv4Address("127.0.0.1"),
        description="local address",
    )
    remote_ports: Ports = Field(description="remote ports")
    remote_addr: IPvAnyAddress = Field(
        default=IPv4Address("127.0.0.1"),
        description="remote address",
    )

    @property
    def command(self) -> list[str]:
        def transform(mode: ForwardingMode, local: int, remote: int) -> str:
            match mode:
                case ForwardingMode.local:
                    return f"-L {self.local_addr}:{local}:{self.remote_addr}:{remote}"
                case ForwardingMode.remote:
                    return f"-R {self.remote_addr}:{remote}:{self.local_addr}:{local}"

        return [
            transform(self.forwarding_mode, local, remote)
            for local, remote in self.local_ports.match(self.remote_ports)
        ]


class ServicesConfig(ServiceConfigOptions):
    services: dict[str, ServiceConfig] = {}  # TODO: add service default values

    @property
    def command(self) -> list[str]:
        return [
            str(service)  #
            for service in self.services.values()
            if service.enable
        ]


class SSHConfig(ConfigModel):
    model_config = ConfigDict(extra="allow")

    server_alive_interval: int = Field(default=60)
    server_alive_count_max: int = Field(default=3)

    @property
    def command(self) -> list[str]:
        return [
            f"-o {camel_key}={value}"
            for key, value in self
            if (camel_key := convert_to(key, "camel")) in ssh_options
        ]


class ConnectionConfig(ConfigModel):
    retry: int = Field(default=3, description="retry times")


class ServerConfig(ConfigModel):
    model_config = ConfigDict(extra="allow")

    user: str = Field(default="root", description="login name")
    addr: IPvAnyAddress = Field(description="remote address")

    no_remote_command: bool = Field(default=True)
    disable_pty: bool = Field(default=True)

    @property
    def command(self) -> list[str]:
        def transform(key: str, value: Any) -> str | None:
            if not (option := options.get(key)):
                return None

            match value:
                case False:
                    return None
                case True:
                    return option
                case _:
                    return f"{option} {value}"

        return [
            f"{self.user}@{self.addr}",
            *(
                option
                for key, value in self
                if (option := transform(key, value))  #
                and key not in ("user", "addr")
            ),
        ]


class Config(ConfigModel):
    name: str = Field(description="config name from file")

    server: ServerConfig
    connection: ConnectionConfig = ConnectionConfig()
    ssh_config: SSHConfig = SSHConfig()
    services: ServicesConfig = ServicesConfig()

    @classmethod
    def load(cls, config_path: Path, default: dict | None = None) -> Self:
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with config_path.open("rb") as f:
            try:
                raw_config: dict[str, Any] = tomli.load(f)
                if default:
                    raw_config = merge(default, raw_config)
                raw_config["name"] = config_path.stem

                return cls.model_validate(raw_config)
            except Exception as e:
                raise ValueError(f"Failed to parse config file: {e}")

    @property
    def command(self) -> list[str]:
        return [
            command
            for _, sub_config in self
            if isinstance(sub_config, ConfigModel)
            for command in sub_config.command
        ]


def load_configs(conf_dir_path: Path) -> Iterable[Config]:
    default_config_path = conf_dir_path / "default.toml"
    default_config = (
        tomli.loads(default_config_path.read_text())
        if default_config_path.exists()
        else None
    )

    config_paths = (
        path  #
        for path in (conf_dir_path / "conf.d").iterdir()
        if path.suffix == ".toml"
    )

    return (Config.load(config_path, default_config) for config_path in config_paths)


def init_conf_dir() -> Path:
    conf_dir_path = (
        Path("/etc/rev-tun")  #
        if check_root(raise_exception=False)
        else Path.home() / ".rev-tun"
    )

    conf_dir_path.mkdir(parents=True, exist_ok=True)
    (conf_dir_path / "conf.d").mkdir(exist_ok=True)

    # Copy default config if not exists
    default_config_path = conf_dir_path / "default.toml"

    if not default_config_path.exists():
        with res.as_file(res.files(rev_tun.templates)) as template_path:
            shutil.copy2(template_path, default_config_path)

    return conf_dir_path
