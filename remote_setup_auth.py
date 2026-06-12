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
    tmp = Path(tempfile.gettempdir()) / "stock-tracker-auth.tar.gz"
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


def run(client, command: str) -> None:
    _, stdout, stderr = client.exec_command(command, get_pty=True)
    code = stdout.channel.recv_exit_status()
    text = (stdout.read() + stderr.read()).decode("utf-8", "replace")
    print(text.encode("ascii", "replace").decode("ascii")[-5000:])
    if code != 0:
        raise RuntimeError(f"Command failed ({code}): {command[:120]}")


def main() -> None:
    password = os.environ["DEPLOY_PASSWORD"]
    db_pass = os.environ.get("POSTGRES_PASSWORD", "stocktracker_prod_2026")
    secret_key = os.environ.get("APP_SECRET_KEY", "prod-secret-change-me-please-32chars")

    archive = build_archive()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username="root", password=password, timeout=20)

    sftp = client.open_sftp()
    remote_archive = "/tmp/stock-tracker-auth.tar.gz"
    sftp.put(str(archive), remote_archive)
    sftp.close()

    env_content = f"""APP_URL=http://49.51.195.205
SECRET_KEY={secret_key}
DATABASE_URL=postgresql+psycopg2://stocktracker:{db_pass}@127.0.0.1:5432/stocktracker
"""

    commands = f"""
set -e
tar -xzf {remote_archive} -C {REMOTE_DIR}
rm -f {remote_archive}
chmod +x {REMOTE_DIR}/deploy/setup-postgresql.sh
POSTGRES_PASSWORD='{db_pass}' bash {REMOTE_DIR}/deploy/setup-postgresql.sh
cat > {REMOTE_DIR}/.env <<'EOF'
{env_content}EOF
{REMOTE_DIR}/.venv/bin/pip install -r {REMOTE_DIR}/requirements.txt
cp {REMOTE_DIR}/deploy/stock-tracker.service /etc/systemd/system/stock-tracker.service
systemctl daemon-reload
systemctl enable postgresql stock-tracker
systemctl restart stock-tracker
sleep 3
curl -s http://127.0.0.1/api/health
curl -s http://127.0.0.1/login.html | head -c 120
"""
    run(client, commands)
    client.close()
    print("Deploy complete: http://49.51.195.205/register.html")


if __name__ == "__main__":
    main()
