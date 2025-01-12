# Rev-Tun: SSH Reverse Tunnel Management Tool

A flexible SSH reverse tunnel management tool that allows you to manage multiple reverse tunnels through configuration files. The tool can convert configurations into supervisor or systemd services, or run them directly in console mode.

Key features:

- Manage multiple tunnels pointing to different servers using configuration files
- Support port range mapping for reverse tunnels
- Fine-grained control at service level
- Multiple deployment options: supervisor, systemd, or direct console mode
- Automatic reconnection and tunnel health monitoring

# Installation

Using `pip` (or `pipx`) to install as a command line tool:

```bash
pip install rev-tun
```

# Usage

## Basic Usage

```bash
rev-tun [config-name] [options]
```

When using `supervisor` or `systemd` registrar, you need to run the command with `sudo`:

```bash
sudo rev-tun [config-name] --register [supervisor|systemd] [options]
```

## Command Line Options

- `config-name`: Optional parameter, specifies the configuration file name (without .toml extension)
  - If not specified, loads all .toml files in the configuration directory
  - If specified, loads only the corresponding configuration file

- `-r, --register`: Specify the registrar type (default: supervisor)
  - `supervisor`: Use Supervisor to manage services (by generating a supervisor configuration file)
  - `systemd`: Use Systemd to manage services
  - `console`: Run directly in console

- `--conf-dir`: Specify configuration file directory (default: `/etc/rev-tun`)
- `--log-dir`: Specify log file directory (default: `/var/log/rev-tun`)

## Examples

```bash
# Load all configurations
rev-tun

# Load specific configuration
rev-tun my-tunnel

# Use systemd registrar
rev-tun --register systemd

# Specify configuration directory
rev-tun --conf-dir /etc/rev-tun
```

# Configuration File

You can use configuration files to manage multiple reverse tunnels. 

The default configuration directory is `/etc/rev-tun`, and the configuration files should have the `.toml` extension.

## Example

A simple configuration file example (`/etc/rev-tun/my-tunnel.toml`):

```toml
[server]
user = "user"
address = "192.168.114.114"
port = 1000
identity-file = "/home/user/.ssh/id_ed25519"

[services.ssh]
remote-ports = "1300"
local-ports = "22"
forwarding-mode = "local"

[services.eda_vnc]
local-ports = "15900-15999"
remote-ports = "5900-5999"
```

In the above example:

- We want to connect to the server with the IP address `192.168.144.144` with port `1000` using the SSH user `user` and the identity file `/home/user/.ssh/id_ed25519`.
- We have two services: `ssh` and `eda_vnc`.
  - The `ssh` service forwards the local port `22` to the remote port `1300` in local forwarding mode, meaning that the remote port `1300` is accessible from the server.
  - The `eda_vnc` service forwards the local ports `15900-15999` to the remote ports `5900-5999`.

## Default Configuration

Default configuration are as follows:

```toml
[server]
user = "root" # SSH user
no-remote-command = true # ssh -N option
disable-tty = true # ssh -T option

[connection]
retry = 3 # retry 3 times

[ssh-config]
server-alive-interval = 60 # alive signal every 60 seconds
server-alive-count-max = 3 # 3 times of no response

[services]
forwarding-mode = "remote" # remote forwarding mode
```

You can override the default configuration by adding the corresponding fields in the configuration file.