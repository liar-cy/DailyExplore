#!/usr/bin/env python3
"""Read and decrypt GitHub cookies from the local Microsoft Edge profile.

The JSON result is intended to be consumed through stdout by collect.mjs. Cookie
values are never written to the project or logs.
"""
import hashlib
import json
import os
import sqlite3
import subprocess
from pathlib import Path


CHROME_EPOCH_OFFSET = 11644473600


def decrypt_cookie(blob: bytes, key: bytes, db_version: int) -> str:
    if not blob.startswith((b"v10", b"v11")):
        return blob.decode("utf-8")
    decrypted = subprocess.run(
        ["openssl", "enc", "-d", "-aes-128-cbc", "-nopad", "-K", key.hex(),
         "-iv", (b" " * 16).hex()],
        input=blob[3:], capture_output=True, check=True,
    ).stdout
    padding = decrypted[-1]
    if not 1 <= padding <= 16 or decrypted[-padding:] != bytes([padding]) * padding:
        raise ValueError("invalid Edge cookie padding")
    decrypted = decrypted[:-padding]
    if db_version >= 24:
        decrypted = decrypted[32:]
    return decrypted.decode("utf-8")


def main() -> None:
    profile = os.environ.get("EDGE_PROFILE", "Default")
    edge_root = Path.home() / "Library/Application Support/Microsoft Edge"
    db_path = edge_root / profile / "Cookies"
    password = subprocess.run(
        ["security", "find-generic-password", "-w", "-s", "Microsoft Edge Safe Storage"],
        capture_output=True, check=True,
    ).stdout.rstrip(b"\n")
    key = hashlib.pbkdf2_hmac("sha1", password, b"saltysalt", 1003, dklen=16)

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        db_version = int(con.execute(
            "select value from meta where key='version'"
        ).fetchone()[0])
        rows = con.execute(
            """select host_key, name, path, expires_utc, is_secure, is_httponly,
                      samesite, encrypted_value
                 from cookies
                where host_key = 'github.com' or host_key = '.github.com'"""
        ).fetchall()
    finally:
        con.close()

    cookies = []
    same_site = {0: "Lax", 1: "Lax", 2: "Strict", -1: "None"}
    for domain, name, path, expires_utc, secure, http_only, samesite, blob in rows:
        try:
            value = decrypt_cookie(blob, key, db_version)
        except (UnicodeDecodeError, ValueError, subprocess.CalledProcessError):
            continue
        cookie = {
            "name": name,
            "value": value,
            "domain": domain,
            "path": path,
            "secure": bool(secure),
            "httpOnly": bool(http_only),
            "sameSite": same_site.get(samesite, "Lax"),
        }
        if expires_utc:
            cookie["expires"] = expires_utc / 1_000_000 - CHROME_EPOCH_OFFSET
        cookies.append(cookie)
    if not any(c["name"] == "user_session" for c in cookies):
        raise SystemExit("Edge 默认配置中没有可用的 GitHub user_session Cookie")
    print(json.dumps(cookies))


if __name__ == "__main__":
    main()
