# SSH Reverse Tunnel Management

Usage:

```bash
rev-tun
```

# Example

A simple example of conf file:

```toml
[server]
address = "192.168.114.114"
port = 1000
identity-file = "/home/user/.ssh/id_ed25519"

[connection]
retry = 3

[ssh-config]
server-alive-interval = 60
server-alive-count-max = 10

[services.ssh]
remote-ports = "1300"
local-ports = "22"

[services.eda_vnc]
local-ports = "15900-15999"
remote-ports = "5900-5999"
```