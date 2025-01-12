from collections.abc import Iterable
from enum import Enum
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any, Self

import tomli
from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator
from pydantic.networks import IPvAnyAddress

from rev_tun.const import options
from rev_tun.utils import convert_to


class ConfigModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def _transform(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        return {
            convert_to(key, "snake"): value  #
            for key, value in data.items()
        }


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


class ServiceConfig(ConfigModel):
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
    forwarding_mode: ForwardingMode = Field(
        default=ForwardingMode.remote,
        description="forwarding mode",
    )

    def __str__(self) -> str:
        def transform(mode: ForwardingMode, local: int, remote: int) -> str:
            match mode:
                case ForwardingMode.local:
                    return f"-L {self.local_addr}:{local}:{self.remote_addr}:{remote}"
                case ForwardingMode.remote:
                    return f"-R {self.remote_addr}:{remote}:{self.local_addr}:{local}"

        return " ".join(
            transform(self.forwarding_mode, local, remote)
            for local, remote in self.local_ports.match(self.remote_ports)
        )


class SSHConfig(ConfigModel):
    model_config = ConfigDict(extra="allow")

    server_alive_interval: int = Field(default=60)
    server_alive_count_max: int = Field(default=3)

    @model_validator(mode="before")
    def _transform(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        return {
            convert_to(key, "snake"): value  #
            for key, value in data.items()
        }

    def __str__(self) -> str:
        return " ".join(
            f"-o {convert_to(key, 'camel')}={value}"  #
            for key, value in self
        )


class ConnectionConfig(ConfigModel):
    retry: int = Field(default=3, description="retry times")


class ServerConfig(ConfigModel):
    model_config = ConfigDict(extra="allow")

    user: str = Field(default="root", description="login name")
    addr: IPvAnyAddress = Field(description="remote address")

    no_remote_command: bool = Field(default=True)
    disable_pty: bool = Field(default=True)

    def __str__(self) -> str:
        def transform(key: str, value: Any) -> str | None:
            if key in ("user", "addr"):
                return None

            if not (option := options.get(key)):
                return None

            match value:
                case False:
                    return None
                case True:
                    return option
                case _:
                    return f"{option} {value}"

        return f"{self.user}@{self.addr} " + " ".join(
            option  #
            for key, value in self
            if (option := transform(key, value))
        )


class Config(ConfigModel):
    name: str = Field(description="config name from file")
    server: ServerConfig
    connection: ConnectionConfig = ConnectionConfig()
    ssh: SSHConfig = SSHConfig()
    services: dict[str, ServiceConfig] = Field(default_factory=dict)

    @classmethod
    def load(cls, config_path: Path) -> Self:
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with config_path.open("rb") as f:
            try:
                raw_config = tomli.load(f)
                raw_config["name"] = config_path.stem

                return cls.model_validate(raw_config)
            except Exception as e:
                raise ValueError(f"Failed to parse config file: {e}")

    def __str__(self) -> str:
        services = " ".join(
            str(service)  #
            for service in self.services.values()
        )

        return f"ssh {self.server} {self.ssh} {services}"
