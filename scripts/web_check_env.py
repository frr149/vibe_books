from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

MIN_NODE_MAJOR = 22
RECOMMENDED_NODE_MAJOR = 22


@dataclass(frozen=True)
class ToolStatus:
    name: str
    level: str
    detail: str


def _run_version_command(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    output = completed.stdout.strip() or completed.stderr.strip()
    if output == "":
        return None
    return output.splitlines()[0].strip()


def _parse_major(version: str) -> int | None:
    match = re.search(r"(\d+)", version)
    if match is None:
        return None
    return int(match.group(1))


def check_node() -> ToolStatus:
    version = _run_version_command(["node", "-v"])
    if version is None:
        return ToolStatus(
            name="node",
            level="fail",
            detail="No encontrado. Instala Node 22 LTS o superior.",
        )

    major = _parse_major(version)
    if major is None:
        return ToolStatus(
            name="node",
            level="fail",
            detail=f"No se pudo parsear la version: {version}",
        )

    if major < MIN_NODE_MAJOR:
        return ToolStatus(
            name="node",
            level="fail",
            detail=(
                f"Version {version} no compatible. "
                f"Se requiere Node >= {MIN_NODE_MAJOR}."
            ),
        )

    if major != RECOMMENDED_NODE_MAJOR:
        return ToolStatus(
            name="node",
            level="warn",
            detail=(
                f"Version detectada: {version}. "
                f"Recomendado para este proyecto: Node {RECOMMENDED_NODE_MAJOR} LTS."
            ),
        )

    return ToolStatus(name="node", level="ok", detail=f"Version detectada: {version}.")


def check_pnpm() -> ToolStatus:
    version = _run_version_command(["pnpm", "-v"])
    if version is None:
        return ToolStatus(
            name="pnpm",
            level="fail",
            detail="No encontrado. Instala pnpm para ejecutar el frontend.",
        )

    return ToolStatus(name="pnpm", level="ok", detail=f"Version detectada: {version}.")


def main() -> int:
    statuses = [check_node(), check_pnpm()]
    has_failures = False

    for status in statuses:
        if status.level == "ok":
            label = "OK"
        elif status.level == "warn":
            label = "WARN"
        else:
            label = "FAIL"
            has_failures = True
        print(f"[{label}] {status.name}: {status.detail}")

    if has_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
