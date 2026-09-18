from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import stat
import subprocess


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    root = args.output_dir / "deb-root"
    if root.exists():
        shutil.rmtree(root)
    app = root / "opt" / "archive-workbench-ai"
    apps = root / "usr" / "share" / "applications"
    usr_bin = root / "usr" / "bin"
    debian = root / "DEBIAN"
    app.mkdir(parents=True)
    apps.mkdir(parents=True)
    usr_bin.mkdir(parents=True)
    debian.mkdir(parents=True)

    target = app / "aw-ai"
    shutil.copy2(args.binary, target)
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    (usr_bin / "aw-ai").symlink_to("/opt/archive-workbench-ai/aw-ai")
    desktop_src = Path(__file__).with_name("archive-workbench-ai-setup.desktop")
    shutil.copy2(desktop_src, apps / desktop_src.name)
    (debian / "control").write_text(
        "\n".join(
            [
                "Package: archive-workbench-ai",
                f"Version: {args.version}",
                "Section: science",
                "Priority: optional",
                "Architecture: amd64",
                "Maintainer: Alex Colman",
                "Depends: xdg-utils",
                "Description: Local assisted-analysis engine for Archive Workbench",
                "", 
            ]
        ),
        encoding="utf-8",
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"archive-workbench-ai_{args.version}_amd64.deb"
    subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(root), str(output)], check=True)
    print(output)


if __name__ == "__main__":
    main()
