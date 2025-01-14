import subprocess
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

from utils import template_env

from rev_tun.config import Config
from rev_tun.utils import check_root


class Registrar(ABC):
    @abstractmethod
    def register(self, config: Config, *, log_dir_path: Path): ...


class SupervisorRegistrar(Registrar):
    def register(self, config: Config, *, log_dir_path: Path) -> None:
        """Register the SSH tunnel as a supervisor program"""

        check_root()

        if not (sv_conf_dir_path := Path("/etc/supervisor/conf.d")).exists():
            raise FileNotFoundError("Supervisor config directory not found")

        name = f"rev-tun-{config.name}"

        # 加载模板

        template = template_env.get_template("supervisor.conf.j2")

        # 渲染模板
        config_content = template.render(
            name=name,
            command=f"ssh {config}",
            retry=config.connection.retry,
            log_dir=log_dir_path,
        )

        conf_file = sv_conf_dir_path / f"{name}.conf"
        conf_file.write_text(config_content)

        try:
            for cmd in [
                ["supervisorctl", "update"],
                ["supervisorctl", "restart", name],
            ]:
                subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            raise RuntimeError("Failed to update supervisor")


class SystemdRegistrar(Registrar):
    def register(self, config: Config, *, log_dir_path: Path) -> None:
        """Register the SSH tunnel as a systemd service"""

        check_root()

        systemd_dir_path = Path("/etc/systemd/system")
        if not systemd_dir_path.exists():
            raise FileNotFoundError("Systemd directory not found")

        name = f"rev-tun-{config.name}"

        template = template_env.get_template("systemd.service.j2")

        service_content = template.render(
            name=config.name,
            command=f"ssh {config}",
            retry=config.connection.retry,
            log_dir=log_dir_path,
        )

        service_file = systemd_dir_path / f"{name}.service"
        service_file.write_text(service_content)

        try:
            for cmd in [
                ["systemctl", "daemon-reload"],
                ["systemctl", "enable", name],
                ["systemctl", "restart", name],
            ]:
                subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            raise RuntimeError("Failed to update systemd service")


class ConsoleRegistrar(Registrar):
    def register(self, config: Config, *, log_dir_path: Path) -> None:
        """Run the SSH tunnel command directly with retry logic"""
        cmd = config.command

        log_dir_path.mkdir(parents=True, exist_ok=True)

        for attempt in range(config.connection.retry):
            try:
                if attempt > 0:
                    print(f"Retrying ({attempt}/{config.connection.retry})...")

                process = subprocess.run(
                    ["ssh", *cmd],
                    check=True,
                    text=True,
                    capture_output=True,
                )

                with open(log_dir_path / f"{config.name}.out.log", "a") as out_log:
                    out_log.write(process.stdout)

            except subprocess.CalledProcessError as e:
                with open(log_dir_path / f"{config.name}.err.log", "a") as err_log:
                    err_log.write(e.stderr)

                if attempt == config.connection.retry - 1:
                    raise RuntimeError(
                        f"Failed to establish SSH tunnel after {config.connection.retry} attempts"
                    )

            except KeyboardInterrupt:
                print("\nReceived keyboard interrupt, stopping...")
                return


class RegisterType(str, Enum):
    supervisor = "supervisor"
    systemd = "systemd"
    console = "console"


register_lookup: dict[RegisterType, Registrar] = {
    RegisterType.supervisor: SupervisorRegistrar(),
    RegisterType.systemd: SystemdRegistrar(),
    RegisterType.console: ConsoleRegistrar(),
}
