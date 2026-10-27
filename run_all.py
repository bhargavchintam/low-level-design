"""Run the demo in every design folder and print one PASS or FAIL row per design.

Python demos run with the same interpreter as this script. Java demos are
compiled with javac into a temporary folder and run with java. If javac is not
on PATH, the Java demos are skipped. The script exits with status 1 if any demo
fails, so CI can use it as is.

    python3 run_all.py                                # every design
    python3 run_all.py kv-cache-pool dynamic-batcher  # only these
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TIMEOUT_S = 120
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}  # keep __pycache__ out of the repo


def find_designs():
    """Yield (folder, language) for every folder that has a demo entry point."""
    for folder in sorted(p for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith(".")):
        if (folder / "main.py").is_file():
            yield folder, "python"
        elif (folder / "Main.java").is_file():
            yield folder, "java"


def error_line(text):
    """The most useful line of an error message.

    javac and the JVM put the cause on the first line ("error:" or
    "Exception in thread"); a Python traceback puts it on the last line.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if "error:" in line:
            return line
        if line.startswith("Exception in thread"):
            return line.split(" ", 4)[-1]  # drop 'Exception in thread "main"'
    return lines[-1] if lines else "no output"


def run(cmd, cwd):
    """Run one command. Return (ok, detail)."""
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return False, f"timed out after {TIMEOUT_S}s"
    if proc.returncode != 0:
        return False, error_line(proc.stderr or proc.stdout)
    return True, ""


def run_python(folder):
    return run([sys.executable, "main.py"], folder)


def run_java(folder):
    with tempfile.TemporaryDirectory() as classes:
        ok, detail = run(["javac", "-d", classes, "Main.java"], folder)
        if not ok:
            return False, f"javac {detail}"
        return run(["java", "-cp", classes, "Main"], folder)


def print_row(status, name, lang, elapsed, detail):
    if len(detail) > 70:
        detail = detail[:69] + "…"
    print(f"{status}  {name:<30} {lang:<6} {elapsed:>7}  {detail}".rstrip())


def main(names):
    designs = list(find_designs())
    if names:
        unknown = sorted(set(names) - {folder.name for folder, _ in designs})
        if unknown:
            sys.exit(f"unknown design: {', '.join(unknown)}")
        designs = [(folder, lang) for folder, lang in designs if folder.name in names]

    has_jdk = shutil.which("javac") is not None and shutil.which("java") is not None
    passed = failed = skipped = 0
    for folder, lang in designs:
        if lang == "java" and not has_jdk:
            skipped += 1
            print_row("SKIP", folder.name, lang, "", "javac not found")
            continue
        start = time.perf_counter()
        ok, detail = run_python(folder) if lang == "python" else run_java(folder)
        elapsed = f"{time.perf_counter() - start:.2f}s"
        if ok:
            passed += 1
        else:
            failed += 1
        print_row("PASS" if ok else "FAIL", folder.name, lang, elapsed, detail)

    summary = f"\n{passed}/{passed + failed} demos passed"
    if skipped:
        summary += f", {skipped} Java demo{'s' if skipped > 1 else ''} skipped (no javac)"
    print(summary)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
