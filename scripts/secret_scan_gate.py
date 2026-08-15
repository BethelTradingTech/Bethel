"""Fail CI when high-confidence secrets or private environment files are tracked."""

from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]

ALLOWED_ENV_FILES = {".env.example", ".env.sample", ".env.template"}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Stripe live secret": re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b"),
    "GitHub classic token": re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),
    "GitHub fine-grained token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Slack bot token": re.compile(r"\bxoxb-[A-Za-z0-9-]{20,}\b"),
    "database URL with embedded password": re.compile(
        r"postgres(?:ql)?://[^\s:@/]+:[^\s@/]+@[^\s]+",
        re.IGNORECASE,
    ),
}

TEXT_SUFFIXES = {
    ".py", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".conf", ".md", ".txt", ".ps1", ".sh",
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def main() -> None:
    failures: list[str] = []
    for path in tracked_files():
        rel = path.relative_to(ROOT)
        name = path.name.lower()
        if name.startswith(".env") and name not in ALLOWED_ENV_FILES:
            failures.append(f"tracked environment file: {rel}")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and name not in {"dockerfile", "procfile"}:
            continue
        try:
            data = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(data):
                failures.append(f"{label}: {rel}")

    if failures:
        print("SECRET SCAN FAIL")
        for failure in failures:
            print(f" - {failure}")
        raise SystemExit(1)
    print("PASS: no high-confidence tracked secrets detected")


if __name__ == "__main__":
    main()
