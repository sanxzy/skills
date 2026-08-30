"""Framework-agnostic, read-only project reconnaissance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FRAMEWORK_MARKERS = {
    "next": "Next.js",
    "react": "React",
    "@vitejs/plugin-react": "React + Vite",
    "vite": "Vite",
    "vue": "Vue",
    "nuxt": "Nuxt",
    "svelte": "Svelte",
    "@angular/core": "Angular",
    "solid-js": "Solid",
    "astro": "Astro",
    "remix": "Remix",
    "@tauri-apps/api": "Tauri",
    "electron": "Electron",
}


def _files(root: Path, limit: int = 200) -> list[str]:
    ignored = {".git", ".xzy-env", ".artifacts", "node_modules", "__pycache__"}
    result = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.relative_to(root).parts):
            continue
        result.append(path.relative_to(root).as_posix())
        if len(result) >= limit:
            break
    return result


def _package_manager(root: Path) -> str | None:
    for filename, manager in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("bun.lockb", "bun"), ("bun.lock", "bun"), ("package-lock.json", "npm")):
        if (root / filename).exists():
            return manager
    return "npm" if (root / "package.json").exists() else None


def _package_info(root: Path) -> dict[str, Any] | None:
    path = root / "package.json"
    if not path.is_file():
        return None
    try:
        package = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"path": str(path), "error": str(exc)}
    dependencies: dict[str, str] = {}
    dependencies.update(package.get("dependencies", {}))
    dependencies.update(package.get("devDependencies", {}))
    frameworks = sorted({label for marker, label in FRAMEWORK_MARKERS.items() if marker in dependencies})
    scripts = package.get("scripts", {})
    return {
        "path": str(path),
        "name": package.get("name"),
        "package_manager": _package_manager(root),
        "frameworks": frameworks,
        "scripts": scripts if isinstance(scripts, dict) else {},
        "dependencies": sorted(dependencies),
    }


def inspect_project(root: Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Project root is not a directory: {root}")
    package = _package_info(root)
    frameworks = package["frameworks"] if package else []
    if (root / "index.html").exists() and not frameworks:
        frameworks.append("static HTML")
    if (root / "pyproject.toml").exists():
        frameworks.append("Python project")
    if (root / "Cargo.toml").exists():
        frameworks.append("Rust project")
    candidate_names = {
        "index.html", "src/main.ts", "src/main.tsx", "src/main.js", "src/main.jsx",
        "src/App.tsx", "src/App.jsx", "app/page.tsx", "app/page.jsx", "pages/index.tsx",
        "pages/index.jsx", "manage.py", "pyproject.toml", "Cargo.toml", "go.mod",
    }
    files = _files(root)
    return {
        "project_root": str(root),
        "frameworks": sorted(set(frameworks)),
        "manifests": [file for file in files if Path(file).name in {"package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "go.mod", "pom.xml", "build.gradle"} or Path(file).suffix == ".csproj"],
        "package": package,
        "candidate_entrypoints": [file for file in files if file in candidate_names],
        "files": files,
        "notes": ["Project inspection is read-only.", "Use the existing project command for a dev server when a file URL is insufficient."],
    }
