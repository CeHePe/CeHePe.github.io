"""Check local file references in the site's source HTML.

The checker is intentionally read-only and uses only the Python standard
library. External URLs and same-page fragments are outside its scope.
Templates are skipped by default because they contain placeholder links; pass
``--include-templates`` when those placeholders should be audited as well.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRECTORIES = {".git", "dist", "node_modules"}
REFERENCE_ATTRIBUTES = {"href", "src", "poster"}


@dataclass(frozen=True)
class Reference:
    source: Path
    line: int
    attribute: str
    value: str


@dataclass(frozen=True)
class Problem:
    reference: Reference
    reason: str


class ReferenceParser(HTMLParser):
    def __init__(self, source: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.references: list[Reference] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self._collect(attrs)

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self._collect(attrs)

    def _collect(self, attrs: list[tuple[str, str | None]]) -> None:
        line, _ = self.getpos()
        for attribute, value in attrs:
            attribute = attribute.lower()
            if not value:
                continue
            if attribute in REFERENCE_ATTRIBUTES:
                self.references.append(
                    Reference(self.source, line, attribute, value.strip())
                )
            elif attribute == "srcset":
                for candidate in parse_srcset(value):
                    self.references.append(
                        Reference(self.source, line, attribute, candidate)
                    )


def parse_srcset(value: str) -> list[str]:
    """Return the URL portion of ordinary comma-separated srcset entries."""
    if value.lstrip().lower().startswith("data:"):
        return []
    return [
        entry.strip().split(maxsplit=1)[0]
        for entry in value.split(",")
        if entry.strip()
    ]


def discover_html(root: Path, include_templates: bool) -> list[Path]:
    html_files: list[Path] = []
    for path in root.rglob("*.html"):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRECTORIES for part in relative.parts):
            continue
        if not include_templates and relative.parts[0] == "templates":
            continue
        html_files.append(path)
    return sorted(html_files)


def local_target(reference: Reference, root: Path) -> tuple[Path | None, str | None]:
    value = reference.value.strip()
    if not value or value.startswith("#") or value.startswith("//"):
        return None, None

    try:
        parsed = urlsplit(value)
    except ValueError:
        return None, "invalid URL"

    if parsed.scheme or parsed.netloc:
        return None, None

    url_path = unquote(parsed.path)
    if not url_path:
        return None, None

    parts = PurePosixPath(url_path.lstrip("/")).parts
    base = root if url_path.startswith("/") else reference.source.parent
    target = base.joinpath(*parts).resolve()

    try:
        target.relative_to(root)
    except ValueError:
        return target, "escapes repository root"

    return target, None


def check_reference(reference: Reference, root: Path) -> Problem | None:
    target, error = local_target(reference, root)
    if error:
        return Problem(reference, error)
    if target is None:
        return None
    if target.is_file():
        return None
    if reference.attribute == "href" and target.is_dir():
        if (target / "index.html").is_file():
            return None
        return Problem(reference, "directory has no index.html")
    return Problem(reference, "target does not exist")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check local href, src, poster, and srcset references in source HTML."
    )
    parser.add_argument(
        "--include-templates",
        action="store_true",
        help="also check HTML under templates/",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    root = REPOSITORY_ROOT.resolve()
    html_files = discover_html(root, args.include_templates)
    references: list[Reference] = []

    for html_file in html_files:
        parser = ReferenceParser(html_file)
        parser.feed(html_file.read_text(encoding="utf-8"))
        parser.close()
        references.extend(parser.references)

    problems: list[Problem] = []
    local_references = 0
    for reference in references:
        target, error = local_target(reference, root)
        if target is not None or error is not None:
            local_references += 1
        problem = check_reference(reference, root)
        if problem:
            problems.append(problem)

    print(
        f"Checked {len(html_files)} HTML files and "
        f"{local_references} local references."
    )
    if not problems:
        print("All local references resolved.")
        return 0

    print(f"Found {len(problems)} problem(s):")
    for problem in problems:
        reference = problem.reference
        source = reference.source.relative_to(root)
        print(
            f"- {source}:{reference.line} "
            f"[{reference.attribute}] {reference.value!r}: {problem.reason}"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
