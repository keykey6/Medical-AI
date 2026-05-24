"""共享密码哈希工具 — backend 和 admin 进程共用，避免代码重复。"""

import hashlib
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    return salt + ":" + hashlib.sha256((salt + password).encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    parts = password_hash.split(":", 1)
    if len(parts) != 2:
        return False
    salt, stored = parts
    return hashlib.sha256((salt + password).encode()).hexdigest() == stored
