import os
import tarfile
import tempfile
from pathlib import Path

import paramiko

PROJECT = Path(__file__).resolve().parent
HOST = "49.51.195.205"
REMOTE_DIR = "/opt/stock-tracker"
EXCLUDE = {".venv", ".git", "__pycache__", "data/quotes.json"}


def build_archive() -> Path:
    tmp = Path(tempfile.gettempdir()) / "stock-tracker-update.tar.gz"
    with tarfile.open(tmp, "w:gz") as archive:
        for path in PROJECT.rglob("*"):
            if path.is_dir():
                continue
            rel = path.relative_to(PROJECT)
            if any(part in EXCLUDE for part in rel.parts):
                continue
            if rel.name.startswith("remote_") or rel.name.startswith("test_"):
                continue
            archive.add(path, arcname=str(rel))
    return tmp


def main() -> None:
    password = os.environ["DEPLOY_PASSWORD"]
    archive = build_archive()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username="root", password=password, timeout=20)

    sftp = client.open_sftp()
    remote_archive = "/tmp/stock-tracker-update.tar.gz"
    sftp.put(str(archive), remote_archive)
    sftp.close()

    commands = f"""
set -e
tar -xzf {remote_archive} -C {REMOTE_DIR}
rm -f {remote_archive}
systemctl restart stock-tracker
sleep 2
curl -s http://127.0.0.1/api/health
curl -s 'http://127.0.0.1/api/news?limit=10' | head -c 400
curl -s http://127.0.0.1/api/quotes | head -c 500
"""
    _, stdout, stderr = client.exec_command(commands, get_pty=True)
    stdout.channel.recv_exit_status()
    text = (stdout.read() + stderr.read()).decode("utf-8", "replace")
    print(text.encode("ascii", "replace").decode("ascii"))
    client.close()


if __name__ == "__main__":
    main()
