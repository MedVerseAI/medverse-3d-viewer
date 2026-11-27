#!/usr/bin/env python3
"""
convert_blend.py  --  .blend  ->  web/model.glb   (run from VS Code / the terminal, not from inside Blender)

Overview:
  1) Reads config.json
  2) finds the .blend file (a direct file path or a folder containing .blend files)
  3) runs Blender in the background (without a UI) and exports to GLB
  4) Places the output in web/model.glb  <-- the file loaded by index.html (MODEL_URL='./model.glb')
  5) (optional) runs docker compose up -d --build

Usage:
  python convert_blend.py
  python convert_blend.py --config config.json
  python convert_blend.py --blend "D:/models/brain.blend"      # overrides blend_path in config
  python convert_blend.py --docker                             # rebuilds Docker after conversion

No external libraries required -- just standard Python + Blender installed on the machine.
"""

import argparse
import glob
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


# ----------------------------------------------------------------------------
# Code to be executed inside Blender (written to a temporary file and passed to blender --python)
# ----------------------------------------------------------------------------
BLENDER_SIDE_SCRIPT = r'''
import sys, json
import bpy

args = json.loads(sys.argv[sys.argv.index("--") + 1])
opts = args["export"]

# Ensure the glTF add-on is enabled (usually enabled by default)
if not hasattr(bpy.ops.export_scene, "gltf"):
    try:
        bpy.ops.preferences.addon_enable(module="io_scene_gltf2")
    except Exception as exc:
        print("WARN: could not enable glTF addon:", exc)

op = bpy.ops.export_scene.gltf
supported = set(op.get_rna_type().properties.keys())

wanted = {
    "filepath": args["out"],
    "export_format": "GLB",
    "export_apply": opts["apply_modifiers"],
    "export_extras": opts["export_extras"],          # required to preserve bp3d_group / hemisphere ...
    "export_yup": opts["y_up"],
    "use_visible": opts["only_visible"],
    "use_selection": opts["only_selected"],
    "export_cameras": opts["cameras"],
    "export_lights": opts["lights"],
    "export_animations": opts["animations"],
    "export_draco_mesh_compression_enable": opts["draco"],
    "export_draco_mesh_compression_level": opts["draco_level"],
}

kwargs = {k: v for k, v in wanted.items() if k in supported}
skipped = sorted(set(wanted) - set(kwargs))
if skipped:
    print("NOTE: this Blender version does not have these export options, skipped:", skipped)

result = op(**kwargs)
print("EXPORT_RESULT:", result)
if "FINISHED" not in result:
    raise SystemExit(1)
'''


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "blend_path": "",
    "blender_exe": "",
    "output_glb": "web/model.glb",
    "backup_existing": True,
    "docker_rebuild": False,
    "export": {
        "draco": True,
        "draco_level": 6,
        "apply_modifiers": True,
        "export_extras": True,
        "y_up": True,
        "only_visible": False,
        "only_selected": False,
        "cameras": False,
        "lights": False,
        "animations": False,
    },
}


def die(msg: str, code: int = 1):
    print(f"\n[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


def clean_path(p: str) -> Path:
    """Removes quotes and extra whitespace, and expands ~ and %VAR%."""
    p = p.strip().strip('"').strip("'")
    return Path(os.path.expandvars(os.path.expanduser(p)))


def load_config(path: Path) -> dict:
    if not path.is_file():
        die(f"Config file not found: {path}")
    try:
        user_cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(
            f"Invalid JSON in config.json: {exc}\n"
            "  Tip: on Windows, use / in paths (D:/folder/file.blend) "
            "or \\\\ twice, not a single \\."
        )
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    for k, v in user_cfg.items():
        if k == "export" and isinstance(v, dict):
            cfg["export"].update(v)
        else:
            cfg[k] = v
    return cfg


def resolve_blend(blend_path: str) -> Path:
    """Accepts a .blend file directly, or a folder containing .blend files (chooses the newest)."""
    if not blend_path:
        die("blend_path is empty in config.json")
    p = clean_path(blend_path)
    if not p.is_absolute():
        p = (SCRIPT_DIR / p).resolve()

    if p.is_file():
        if p.suffix.lower() != ".blend":
            die(f"This file is not a .blend file: {p}")
        return p

    if p.is_dir():
        found = sorted(
            (f for f in p.glob("*.blend") if f.is_file()),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if not found:
            die(f"No .blend files found in folder: {p}")
        if len(found) > 1:
            print(f"[INFO] Found {len(found)} .blend files in the folder; using the newest:")
            for f in found:
                print(f"         - {f.name}")
        return found[0]

    die(f"Path does not exist: {p}")


def find_blender(configured: str) -> Path:
    """Searches for Blender: config -> BLENDER_PATH -> PATH -> known locations."""
    candidates = []
    if configured.strip():
        candidates.append(clean_path(configured))
    if os.environ.get("BLENDER_PATH"):
        candidates.append(clean_path(os.environ["BLENDER_PATH"]))
    on_path = shutil.which("blender")
    if on_path:
        candidates.append(Path(on_path))

    system = platform.system()
    if system == "Windows":
        for base in filter(None, [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")]):
            hits = glob.glob(os.path.join(base, "Blender Foundation", "Blender *", "blender.exe"))
            # Highest version first
            candidates += [Path(h) for h in sorted(hits, reverse=True)]
        hits = glob.glob(os.path.join(os.environ.get("ProgramFiles", ""), "Blender Foundation", "blender.exe"))
        candidates += [Path(h) for h in hits]
    elif system == "Darwin":
        candidates.append(Path("/Applications/Blender.app/Contents/MacOS/Blender"))
    else:
        candidates += [Path("/usr/bin/blender"), Path("/snap/bin/blender"), Path("/usr/local/bin/blender")]

    for c in candidates:
        # If the user entered the installation folder instead of the executable
        if c.is_dir():
            for name in ("blender.exe", "blender", "Blender"):
                if (c / name).is_file():
                    return c / name
        elif c.is_file():
            return c

    die(
        "Blender not found.\n"
        "  Set its path in config.json:  \"blender_exe\": \"C:/Program Files/Blender Foundation/Blender 4.2/blender.exe\"\n"
        "  Or add it to PATH, or set the BLENDER_PATH environment variable."
    )


def run_blender(blender: Path, blend: Path, out_glb: Path, export_opts: dict):
    payload = json.dumps({"out": str(out_glb), "export": export_opts})
    with tempfile.NamedTemporaryFile("w", suffix="_export.py", delete=False, encoding="utf-8") as tmp:
        tmp.write(BLENDER_SIDE_SCRIPT)
        script_path = tmp.name

    cmd = [
        str(blender),
        "--background",
        "--factory-startup",              # ignores user add-ons/settings to keep the result consistent
        "--python-exit-code", "1",        # returns a real error if an exception occurs inside Blender
        str(blend),
        "--python", script_path,
        "--", payload,
    ]
    print(f"[INFO] Blender : {blender}")
    print(f"[INFO] Source  : {blend}")
    print("[INFO] Converting... (may take some time depending on scene size)\n")
    try:
        proc = subprocess.run(cmd)
    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass
    if proc.returncode != 0:
        die(f"Blender returned an error (code {proc.returncode}). Check the messages above.")


def validate_glb(path: Path):
    if not path.is_file() or path.stat().st_size < 20:
        die("Export finished, but the GLB file was not created.")
    with open(path, "rb") as f:
        if f.read(4) != b"glTF":
            die("The output file is not a valid GLB (incorrect header).")


def docker_rebuild(project_dir: Path):
    docker = shutil.which("docker")
    if not docker:
        print("[WARN] Docker is not in PATH -- skipping rebuild.")
        return
    print("\n[INFO] docker compose up -d --build ...")
    r = subprocess.run([docker, "compose", "up", "-d", "--build"], cwd=project_dir)
    if r.returncode != 0:
        print("[WARN] docker compose failed -- check the messages above.")
    else:
        print("[OK] Container updated -- open http://localhost:8080")


# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Convert .blend to GLB and install it into the AtlasView web folder.")
    ap.add_argument("--config", default=str(SCRIPT_DIR / "config.json"), help="path to config.json")
    ap.add_argument("--blend", help="override blend_path from config (file or folder)")
    ap.add_argument("--docker", action="store_true", help="rebuild docker after converting")
    args = ap.parse_args()

    cfg_path = clean_path(args.config)
    cfg = load_config(cfg_path)
    project_dir = cfg_path.parent

    blend = resolve_blend(args.blend or cfg["blend_path"])
    blender = find_blender(cfg["blender_exe"])

    out_glb = clean_path(cfg["output_glb"])
    if not out_glb.is_absolute():
        out_glb = (project_dir / out_glb).resolve()
    out_glb.parent.mkdir(parents=True, exist_ok=True)

    # Export to a temporary file first; if successful, move it to model.glb (so a failure does not damage the old model)
    tmp_dir = Path(tempfile.mkdtemp(prefix="atlas_glb_"))
    tmp_glb = tmp_dir / "model.glb"
    try:
        run_blender(blender, blend, tmp_glb, cfg["export"])
        validate_glb(tmp_glb)

        if cfg["backup_existing"] and out_glb.exists():
            bak = project_dir / (out_glb.name + ".bak")   # outside web/ so it is not included in the Docker image
            shutil.copy2(out_glb, bak)
            print(f"[INFO] Backup  : {bak}")
        shutil.move(str(tmp_glb), str(out_glb))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    size_mb = out_glb.stat().st_size / 1_000_000
    print(f"\n[OK] Done: {out_glb}  ({size_mb:.2f} MB)")

    if args.docker or cfg["docker_rebuild"]:
        docker_rebuild(project_dir)
    else:
        print("To update Docker:  docker compose up -d --build   (or run the script with --docker)")


if __name__ == "__main__":
    main()