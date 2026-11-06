import re, subprocess

try:
    from mcp.server.mcpserver import MCPServer as Server  # mcp 2.x
except ImportError:
    from mcp.server.fastmcp import FastMCP as Server      # mcp 1.x

mcp = Server("devstack")

OPENRC = "source /opt/stack/devstack/openrc admin admin >/dev/null 2>&1"
#mcp = FastMCP("devstack")


def sh(cmd: str) -> str:
    p = subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True, timeout=60)
    return (p.stdout + p.stderr)[-6000:]


@mcp.tool()
def devstack_services() -> str:
    """Report which DevStack services (systemd units named devstack@*) are
    running, failed, or inactive on this host. Use for 'what services are running?'"""
    out = sh("systemctl list-units 'devstack@*' --all --no-legend --plain --no-pager")
    groups = {"running": [], "failed": [], "other": []}
    for line in out.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue
        name = re.sub(r"^devstack@|\.service$", "", parts[0])
        active, sub = parts[2], parts[3]
        if active == "active" and sub == "running":
            groups["running"].append(name)
        elif active == "failed":
            groups["failed"].append(name)
        else:
            groups["other"].append(f"{name} ({active}/{sub})")
    return "\n".join(f"{k}: {', '.join(v) or 'none'}" for k, v in groups.items())


@mcp.tool()
def openstack_catalog() -> str:
    """List services registered in the OpenStack catalog (keystone, nova, glance...)."""
    return sh(f"{OPENRC} && openstack service list")


@mcp.tool()
def compute_services() -> str:
    """Nova compute services and whether they are up or down."""
    return sh(f"{OPENRC} && openstack compute service list")


@mcp.tool()
def network_agents() -> str:
    """Neutron agents and whether they are alive."""
    return sh(f"{OPENRC} && openstack network agent list")


@mcp.tool()
def supporting_services() -> str:
    """Status of non-OpenStack services DevStack depends on: MySQL/MariaDB,
    RabbitMQ, Apache (Horizon/WSGI), Open vSwitch, libvirt."""
    units = "mysql mariadb rabbitmq-server apache2 openvswitch-switch libvirtd"
    return sh(f"systemctl is-active {units} 2>&1 | paste -d' ' <(echo {units} | tr ' ' '\\n') -")


@mcp.tool()
def recent_errors(service: str = "") -> str:
    """Last 40 log lines at warning level or worse. Pass a unit name like
    'n-api' to filter to one DevStack service."""
    if service and not re.fullmatch(r"[a-z0-9-]+", service):
        return "Invalid service name."
    unit = f"-u devstack@{service}" if service else "-u 'devstack@*'"
    return sh(f"journalctl {unit} -p warning -n 40 --no-pager")


if __name__ == "__main__":
    mcp.run()
