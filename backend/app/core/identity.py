"""协作身份与房间权限。

本轮提供轻量但真实的权限模型：
- 角色：owner > editor > viewer
- 写操作（发事件、发消息、改房间）要求成员存在且角色 >= editor
- 读操作要求成员存在（本地默认房间会自动赋予 owner，保证单机零配置可用）

未来阶段会接入真实账号体系，这里先把权限校验的边界确定下来。
"""

from __future__ import annotations

ROLE_OWNER = 'owner'
ROLE_EDITOR = 'editor'
ROLE_VIEWER = 'viewer'

# 兼容早期数据：member 视为 editor
_ROLE_LEVEL = {
    ROLE_VIEWER: 1,
    'member': 2,
    ROLE_EDITOR: 2,
    ROLE_OWNER: 3,
}

VALID_ROLES = {ROLE_OWNER, ROLE_EDITOR, ROLE_VIEWER, 'member'}


class PermissionError(Exception):
    """权限不足。"""

    def __init__(self, message: str, status: int = 403):
        super().__init__(message)
        self.message = message
        self.status = status


def role_level(role: str) -> int:
    return _ROLE_LEVEL.get(str(role or '').strip().lower(), 0)


def normalize_role(role: str, default: str = ROLE_EDITOR) -> str:
    cleaned = str(role or '').strip().lower()
    if cleaned not in VALID_ROLES:
        return default
    return ROLE_EDITOR if cleaned == 'member' else cleaned


def can_read(role: str) -> bool:
    return role_level(role) >= role_level(ROLE_VIEWER)


def can_write(role: str) -> bool:
    return role_level(role) >= role_level(ROLE_EDITOR)


def can_manage(role: str) -> bool:
    return role_level(role) >= role_level(ROLE_OWNER)
