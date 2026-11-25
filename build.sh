#!/usr/bin/env bash
# Prepare the ASE tools and check the existing Blender installation.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
skill="$root/skills/materials-schematic"
lock="$skill/environment/linux-64.lock"
prefix="$root/.figure-env"
unset PYTHONHOME PYTHONPATH

if [[ $(uname -sm) != "Linux x86_64" ]]; then
    echo "The environment lock requires x86-64 Linux or WSL2." >&2
    exit 1
fi

# Serialize builds from different shells using the same checkout.
exec 9>>"$root/.figure-build.lock"
flock -x 9

matches_lock() {
    [[ -x "$prefix/bin/python" && -f "$prefix/conda-meta/history" ]] || return 1
    "$prefix/bin/python" -I - "$lock" <<'PY'
import json
from pathlib import Path
import sys

from ase.io import read
from ase.neighborlist import neighbor_list

expected = {line for line in Path(sys.argv[1]).read_text().splitlines() if line.startswith("https://")}
installed = set()
for path in (Path(sys.prefix) / "conda-meta").glob("*.json"):
    record = json.loads(path.read_text())
    installed.add(f"{record.get('url')}#{record.get('md5')}")
sys.exit(0 if expected and expected <= installed else 1)
PY
}

if matches_lock; then
    echo "Reusing the verified environment at $prefix"
else
    action=create
    if [[ -f "$prefix/conda-meta/history" ]]; then
        action=install
    elif [[ -e "$prefix" || -L "$prefix" ]]; then
        echo "Existing path is not a conda environment: $prefix" >&2
        exit 1
    fi

    scratch=$(mktemp -d)
    cleanup() {
        status=$?
        # Only a new prefix created by this invocation may be incomplete.
        if [[ "$status" != 0 && "$action" == create && -d "$prefix" ]]; then
            rm -rf -- "$prefix"
        fi
        rm -rf -- "$scratch"
    }
    trap cleanup EXIT

    if command -v conda >/dev/null; then
        manager=conda
    elif command -v mamba >/dev/null; then
        manager=mamba
    else
        version=26.9.4-2
        asset="Miniforge3-$version-Linux-x86_64.sh"
        url="https://github.com/conda-forge/miniforge/releases/download/$version/$asset"
        echo "Bootstrapping Miniforge $version"
        curl --fail --location --retry 3 --output "$scratch/$asset" "$url"
        (cd "$scratch" && sha256sum --check <<<"bbaf16b3897da24c4be50315934ba74848f617b4495982841d6a0a60e0edbbdf  $asset")
        bash "$scratch/$asset" -b -p "$scratch/miniforge"
        export MAMBA_ROOT_PREFIX="$scratch/miniforge"
        manager="$MAMBA_ROOT_PREFIX/bin/mamba"
    fi

    "$manager" "$action" --yes --prefix "$prefix" --file "$lock"
    matches_lock || { echo "ASE environment verification failed." >&2; exit 1; }
    rm -rf -- "$scratch"
    trap - EXIT
fi

(
    cd "$skill/scripts"
    "$prefix/bin/python" -s - <<'PY'
import subprocess
import sys
import ase
from host import executable

print(f"Python {sys.version.split()[0]} · ASE {ase.__version__}")
blender = executable()
try:
    version = subprocess.check_output([str(blender), "--version"], text=True).splitlines()[0]
except OSError as error:
    sys.exit(f"Cannot start {blender}: {error}. Load Blender or set BLENDER_EXE.")
print(f"{version} · {blender}")
PY
)
echo "Ready. Run the skill scripts with $prefix/bin/python"
