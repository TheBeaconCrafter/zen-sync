#!/usr/bin/env python3
"""WebDAV Storage Box backend for zen-sync. No external dependencies."""

import base64
import json
import os
import socket
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


def log(msg):
    print(f"[storagebox] {msg}", file=sys.stderr, flush=True)


def _auth_header(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"


def _base_url(config):
    return config["url"].rstrip("/")


def _remote_prefix(config):
    prefix = config.get("path", "zen-sync").strip("/")
    return quote(prefix, safe="/") if prefix else ""


def webdav_request(method, key, data, config, timeout=60):
    base = _base_url(config)
    prefix = _remote_prefix(config)
    path = f"{prefix}/{key}" if prefix else key
    url = f"{base}/{path}"

    return _request_with_redirects(method, url, data, config, timeout=timeout)


def _request_with_redirects(method, url, data, config, timeout=60, max_redirects=5):
    current = url
    redirects = 0

    while True:
        req = Request(current, data=data if method in ("PUT", "POST") else None, method=method)
        req.add_header("Authorization", _auth_header(config["username"], config["password"]))
        if data is not None:
            req.add_header("Content-Type", "application/octet-stream")

        try:
            with urlopen(req, timeout=timeout) as resp:
                return resp.read() if method == "GET" else True
        except HTTPError as e:
            if e.code == 404 and method == "GET":
                return None

            if e.code in (301, 302, 307, 308):
                location = e.headers.get("Location")
                if location and redirects < max_redirects:
                    current = location
                    redirects += 1
                    continue

            raise


def ensure_remote_dir(config):
    prefix = _remote_prefix(config)
    if not prefix:
        return

    log(f"ensuring remote folder: {prefix}")
    base = _base_url(config)
    current = ""
    for part in prefix.split("/"):
        current = f"{current}/{part}" if current else part
        url = f"{base}/{current}"
        try:
            _request_with_redirects("MKCOL", url, None, config, timeout=20)
        except HTTPError as e:
            # 405 already exists, 409 parent missing race, 301/302 redirect handled upstream.
            if e.code not in (405, 409):
                raise


def _age_bin(config):
    return config.get("age_bin") or "age"


def _age_keygen_bin(config):
    return config.get("age_keygen_bin") or "age-keygen"


def _is_windows_exe(path):
    return str(path).lower().endswith(".exe")


def _to_windows_path(path):
    p = str(path)
    if p.startswith("/mnt/") and len(p) > 6:
        drive = p[5].upper()
        rest = p[7:].replace("/", "\\")
        return f"{drive}:\\{rest}"
    return p


def _run_age_exe_with_files(args, input_bytes, work_dir, timeout=120):
    os.makedirs(work_dir, exist_ok=True)
    in_fd, in_path = tempfile.mkstemp(prefix="zen-sync-in-", suffix=".bin", dir=work_dir)
    out_fd, out_path = tempfile.mkstemp(prefix="zen-sync-out-", suffix=".age", dir=work_dir)
    os.close(in_fd)
    os.close(out_fd)

    try:
        with open(in_path, "wb") as f:
            f.write(input_bytes)

        cmd = list(args)
        cmd = cmd + ["-o", _to_windows_path(out_path), _to_windows_path(in_path)]
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode() or "age command failed")

        with open(out_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(in_path)
        except OSError:
            pass
        try:
            os.remove(out_path)
        except OSError:
            pass


def encrypt_age(data, config):
    age_mode = config.get("age_mode", "keyfile")
    age_bin = _age_bin(config)

    if age_mode == "passphrase":
        passphrase_path = os.path.join(config.get("config_dir", os.path.expanduser("~/.config/zen-sync")), "passphrase")
        passphrase_path = os.path.expanduser(passphrase_path)
        with open(passphrase_path, encoding="utf-8") as f:
            passphrase = f.read().strip()
        try:
            proc = subprocess.run(
                [age_bin, "-p"],
                input=data,
                capture_output=True,
                env={**os.environ, "AGE_PASSPHRASE": passphrase},
                timeout=20,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "age passphrase mode timed out (likely waiting for interactive input). "
                "Re-run init and choose key file mode."
            ) from exc
    else:
        key_path = os.path.expanduser(config["age_key_path"])
        result = subprocess.run(
            [_age_keygen_bin(config), "-y", key_path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            with open(key_path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("# public key:"):
                        recipient = line.split(":", 1)[1].strip()
                        break
                else:
                    raise RuntimeError("age-keygen not found. Install age.")
        else:
            recipient = result.stdout.strip()

        if _is_windows_exe(age_bin):
            # WSL <-> Windows stdin piping to .exe can stall; use temp files instead.
            work_dir = os.path.dirname(os.path.abspath(key_path)) or os.getcwd()
            return _run_age_exe_with_files([age_bin, "-r", recipient], data, work_dir)

        proc = subprocess.run([age_bin, "-r", recipient], input=data, capture_output=True, timeout=120)

    if proc.returncode != 0:
        raise RuntimeError(f"age encrypt failed: {proc.stderr.decode()}")
    return proc.stdout


def decrypt_age(data, config):
    age_mode = config.get("age_mode", "keyfile")
    age_bin = _age_bin(config)

    if age_mode == "passphrase":
        passphrase_path = os.path.join(config.get("config_dir", os.path.expanduser("~/.config/zen-sync")), "passphrase")
        passphrase_path = os.path.expanduser(passphrase_path)
        with open(passphrase_path, encoding="utf-8") as f:
            passphrase = f.read().strip()
        try:
            proc = subprocess.run(
                [age_bin, "-d"],
                input=data,
                capture_output=True,
                env={**os.environ, "AGE_PASSPHRASE": passphrase},
                timeout=20,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "age passphrase mode timed out (likely waiting for interactive input). "
                "Re-run init and choose key file mode."
            ) from exc
    else:
        key_path = os.path.expanduser(config["age_key_path"])

        if _is_windows_exe(age_bin):
            work_dir = os.path.dirname(os.path.abspath(key_path)) or os.getcwd()
            return _run_age_exe_with_files([age_bin, "-d", "-i", _to_windows_path(key_path)], data, work_dir)

        proc = subprocess.run([age_bin, "-d", "-i", key_path], input=data, capture_output=True, timeout=120)

    if proc.returncode != 0:
        raise RuntimeError(f"age decrypt failed: {proc.stderr.decode()}")
    return proc.stdout


def pack_files(profile_path, files):
    buf = BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for rel in files:
            full = os.path.join(profile_path, rel)
            if os.path.exists(full):
                tar.add(full, arcname=rel)
    return buf.getvalue()


def unpack_files(data, profile_path):
    buf = BytesIO(data)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        for member in tar.getmembers():
            if member.name.startswith("/") or ".." in member.name:
                continue
            tar.extract(member, profile_path)


def cmd_push(config, profile_path, files):
    log("starting push")
    ensure_remote_dir(config)
    log("packing local session files")
    archive = pack_files(profile_path, files)
    log(f"packed archive: {len(archive)} bytes")
    log("encrypting archive with age")
    encrypted = encrypt_age(archive, config)
    log(f"uploading encrypted archive: {len(encrypted)} bytes")
    webdav_request("PUT", "session.tar.gz.age", encrypted, config)

    log("writing encrypted metadata")
    meta = json.dumps(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hostname": socket.gethostname(),
            "files": files,
            "size": len(archive),
        }
    ).encode()
    webdav_request("PUT", "meta.json.age", encrypt_age(meta, config), config)
    log("push completed")
    return len(archive), len(encrypted)


def cmd_pull(config, profile_path):
    log("starting pull")
    encrypted = webdav_request("GET", "session.tar.gz.age", None, config)
    if encrypted is None:
        log("no remote session archive found")
        return None
    log(f"downloaded encrypted archive: {len(encrypted)} bytes")
    log("decrypting archive")
    archive = decrypt_age(encrypted, config)
    log(f"decrypted archive: {len(archive)} bytes")
    log("extracting files into local profile")
    unpack_files(archive, profile_path)
    log("pull completed")
    return len(archive)


def cmd_status(config):
    log("reading remote metadata")
    encrypted = webdav_request("GET", "meta.json.age", None, config)
    if encrypted is None:
        log("no remote metadata found")
        return None
    log("decrypting remote metadata")
    return json.loads(decrypt_age(encrypted, config))


def ensure_remote_subdir(config, relpath):
    relpath = relpath.strip("/")
    if not relpath:
        return

    base = _base_url(config)
    prefix = _remote_prefix(config)
    current = prefix
    for part in relpath.split("/"):
        quoted = quote(part, safe="")
        current = f"{current}/{quoted}" if current else quoted
        url = f"{base}/{current}"
        try:
            _request_with_redirects("MKCOL", url, None, config, timeout=20)
        except HTTPError as e:
            if e.code not in (405, 409):
                raise


def _backup_slot_key(slot, name):
    return f"backups/{slot}/{name}"


def _delete_key_if_exists(key, config):
    try:
        webdav_request("DELETE", key, None, config, timeout=20)
    except HTTPError as e:
        if e.code != 404:
            raise


def _copy_key_if_exists(src_key, dst_key, config):
    data = webdav_request("GET", src_key, None, config, timeout=20)
    if data is None:
        return False
    parent = os.path.dirname(dst_key).strip("/")
    if parent:
        ensure_remote_subdir(config, parent)
    webdav_request("PUT", dst_key, data, config, timeout=60)
    return True


def cmd_backup(config, keep=3):
    """Rotate and create remote backups of the encrypted session blobs."""
    log(f"creating backup (keep={keep})")
    ensure_remote_dir(config)
    ensure_remote_subdir(config, "backups")

    names = ["session.tar.gz.age", "meta.json.age"]

    for slot in range(keep, 0, -1):
        if slot == keep:
            for name in names:
                _delete_key_if_exists(_backup_slot_key(slot, name), config)

        if slot > 1:
            prev = slot - 1
            for name in names:
                src = _backup_slot_key(prev, name)
                dst = _backup_slot_key(slot, name)
                if not _copy_key_if_exists(src, dst, config):
                    _delete_key_if_exists(dst, config)

    created = False
    for name in names:
        if _copy_key_if_exists(name, _backup_slot_key(1, name), config):
            created = True
        else:
            _delete_key_if_exists(_backup_slot_key(1, name), config)

    return {"created": created, "keep": keep}


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <test|push|pull|status|backup> <config_json>")
        sys.exit(1)

    cmd = sys.argv[1]
    config = json.loads(sys.argv[2])

    files = [
        "zen-sessions.jsonlz4",
        "zen-sessions-backup/clean.jsonlz4",
        "sessionstore-backups/recovery.jsonlz4",
        "sessionstore-backups/recovery.baklz4",
        "sessionstore-backups/previous.jsonlz4",
        "prefs.js",
        "containers.json",
    ]

    if cmd == "test":
        try:
            log("testing connection")
            ensure_remote_dir(config)
            webdav_request("GET", "meta.json.age", None, config, timeout=20)
            log("connection test completed")
            print("ok")
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(1)
    elif cmd == "push":
        raw, enc = cmd_push(config, config["profile"], files)
        print(json.dumps({"raw_size": raw, "encrypted_size": enc}))
    elif cmd == "pull":
        size = cmd_pull(config, config["profile"])
        if size is None:
            print(json.dumps({"error": "no remote session found"}))
        else:
            print(json.dumps({"size": size}))
    elif cmd == "status":
        meta = cmd_status(config)
        if meta is None:
            print(json.dumps({"error": "no remote session found"}))
        else:
            print(json.dumps(meta))
    elif cmd == "backup":
        keep = int(config.get("backup_keep", 3))
        if keep < 1:
            keep = 1
        print(json.dumps(cmd_backup(config, keep=keep)))
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
