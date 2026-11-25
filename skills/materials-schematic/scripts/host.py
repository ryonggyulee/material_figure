"""Build, revise and render with the installed Blender in background mode."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess


def executable():
    explicit = os.environ.get("BLENDER_EXE")
    if explicit:
        return Path(shutil.which(explicit) or explicit)
    native = shutil.which("blender")
    if native:
        return Path(native)
    base = Path("/mnt/c/Program Files/Blender Foundation")
    choices = list(base.glob("Blender */blender.exe"))
    if not choices:
        raise SystemExit("Load Blender on PATH or set BLENDER_EXE to its executable path.")
    return max(choices, key=lambda p: tuple(map(int, re.findall(r"\d+", p.parent.name))))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--input", type=Path, help="Open this existing .blend before applying edits")
    cli.add_argument("--output", required=True, type=Path, help="Destination .blend")
    cli.add_argument("--geometry", type=Path, help="Add the prepared .npz structure")
    cli.add_argument("--replace", metavar="TARGET", help="Replace one existing atomic object's geometry by name or figure_id")
    cli.add_argument("--script", type=Path, help="Run a local Blender composition or revision script")
    cli.add_argument("--style", choices=["studio", "cartoon"])
    cli.add_argument("--render", type=Path, help="Also render the active camera to a PNG")
    cli.add_argument("--transparent", action=argparse.BooleanOptionalAction,
                     help="Override the PNG background preset (default: transparent)")
    cli.add_argument("--threads", type=int, default=os.getenv("SLURM_CPUS_PER_TASK"),
                     help="Blender thread count (defaults to the Slurm task allocation if set)")
    cli.add_argument("--preview", action="store_true", help="Render a half-size, low-sample proof PNG")
    cli.add_argument("--open", action="store_true", help="Open the saved file in an interactive window")
    args = cli.parse_args()
    if args.replace and not (args.input and args.geometry):
        cli.error("--replace requires --input and --geometry")
    if args.threads is not None and args.threads < 1:
        cli.error("--threads must be positive")
    if args.preview and not args.render:
        cli.error("--preview needs a --render PNG path")
    if args.output.suffix.lower() != ".blend" or (args.render and args.render.suffix.lower() != ".png"):
        cli.error("use .blend for --output and .png for --render")
    if not any((args.input, args.geometry, args.script)):
        cli.error("supply --input, --geometry or --script")
    exe = executable()
    if not exe.is_file():
        cli.error(f"Blender executable missing: {exe}")
    windows = exe.suffix.lower() == ".exe" and os.name != "nt"

    def host_path(path):
        path = str(path.resolve())
        if windows:
            return subprocess.check_output(["wslpath", "-w", path], text=True).strip()
        return path

    for path in (args.input, args.geometry, args.script):
        if path and not path.is_file():
            cli.error(f"missing input file: {path}")
    for path in (args.output, args.render):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
    command = [str(exe), "--background", "--factory-startup"]
    if args.input:
        command.append(host_path(args.input))
    if args.threads:
        command += ["--threads", str(args.threads)]
    command += ["--python-exit-code", "1", "--python", host_path(Path(__file__).with_name("driver.py")), "--"]
    for key in ("input", "output", "geometry", "script", "render"):
        value = getattr(args, key)
        if value:
            command += ["--" + key, host_path(value)]
    if args.replace:
        command += ["--replace", args.replace]
    if args.style:
        command += ["--style", args.style]
    if args.preview:
        command.append("--preview")
    if args.transparent is not None:
        command.append("--transparent" if args.transparent else "--no-transparent")
    subprocess.run(command, check=True)
    if args.open:
        subprocess.Popen([str(exe), host_path(args.output)])


if __name__ == "__main__":
    main()
