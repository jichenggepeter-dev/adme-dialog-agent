from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", ".next", "node_modules"}
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REFERENCE_LINK = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)")


def markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".md", ".mdx"}
        and not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts)
    )


def link_targets(path: Path) -> list[tuple[int, str]]:
    targets: list[tuple[int, str]] = []
    in_fence = False
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        targets.extend((line_number, match.group(1)) for match in INLINE_LINK.finditer(line))
        reference = REFERENCE_LINK.match(line)
        if reference:
            targets.append((line_number, reference.group(1)))
    return targets


def local_path(raw_target: str) -> str | None:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    elif " " in target:
        target = target.split(" ", 1)[0]
    target = target.strip("<>\"'")
    if not target or target.startswith("#"):
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None
    return unquote(parsed.path)


def main() -> int:
    checked = 0
    broken: list[str] = []
    files = markdown_files()
    for document in files:
        for line_number, raw_target in link_targets(document):
            target = local_path(raw_target)
            if target is None:
                continue
            checked += 1
            resolved = (ROOT / target.lstrip("/")) if target.startswith("/") else (document.parent / target)
            if not resolved.resolve().exists():
                broken.append(
                    f"{document.relative_to(ROOT)}:{line_number}: {raw_target}"
                )

    print(f"Markdown files checked: {len(files)}")
    print(f"Repository-local links checked: {checked}")
    if broken:
        print("Broken repository-local links:")
        for item in broken:
            print(f"- {item}")
        return 1
    print("Broken repository-local links: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
