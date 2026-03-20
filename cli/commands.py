"""CLI commands for leox: start, stop, restart, status, logs."""

import subprocess
import sys

import click

from cli.display import print_status, print_banner, print_error, print_ok

COMPOSE_FILE = "docker-compose.yml"


def _run_compose(*args: str, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a docker compose command."""
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, *args]
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
    )


@click.group()
def cli():
    """LeoX — Tu ente digital personal."""
    pass


@cli.command()
def start():
    """Levanta todos los servicios."""
    print_banner("Iniciando LeoX...")
    result = _run_compose("up", "-d", "--build")
    if result.returncode == 0:
        print_ok("LeoX está corriendo.")
        print_ok("Revisa los logs con: leox logs")
    else:
        print_error("Error al iniciar. Revisa docker compose logs.")
        sys.exit(1)


@cli.command()
def stop():
    """Detiene todos los servicios."""
    print_banner("Deteniendo LeoX...")
    result = _run_compose("down")
    if result.returncode == 0:
        print_ok("LeoX detenido.")
    else:
        print_error("Error al detener.")
        sys.exit(1)


@cli.command()
def restart():
    """Reinicia todos los servicios."""
    print_banner("Reiniciando LeoX...")
    _run_compose("down")
    result = _run_compose("up", "-d", "--build")
    if result.returncode == 0:
        print_ok("LeoX reiniciado.")
    else:
        print_error("Error al reiniciar.")
        sys.exit(1)


@cli.command()
def status():
    """Muestra el estado de cada servicio."""
    # Get docker compose status
    result = _run_compose("ps", "--format", "json", capture=True)

    # Get WhatsApp connection status
    import httpx

    wa_status = None
    brain_status = None

    try:
        r = httpx.get("http://localhost:3000/status", timeout=3)
        wa_status = r.json()
    except Exception:
        pass

    try:
        r = httpx.get("http://localhost:8000/health", timeout=3)
        brain_status = r.json()
    except Exception:
        pass

    print_status(
        compose_output=result.stdout if result.returncode == 0 else None,
        wa_status=wa_status,
        brain_status=brain_status,
    )


@cli.command()
@click.option("-f", "--follow", is_flag=True, help="Seguir logs en tiempo real")
@click.argument("service", required=False)
def logs(follow: bool, service: str | None):
    """Muestra logs de los servicios."""
    args = ["logs", "--tail", "100"]
    if follow:
        args.append("-f")
    if service:
        args.append(service)
    _run_compose(*args)
