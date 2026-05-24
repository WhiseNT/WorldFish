"""
Agent 全局助手数据模型与持久化仓库
支持：多对话Session、记忆、Skill、Agent.md、Sub-Agent
"""

import json
import os
import shutil
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Config
from .world import WorldManager


# ============================================================
# 消息 / 会话模型
# ============================================================

@dataclass
class AgentMessage:
    """单条对话消息"""
    role: str           # "user" | "assistant" | "tool" | "system"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None       # tool 消息的发送者名
    options: Optional[List[Dict[str, Any]]] = None  # agent 提供的选项（单选/多选）
    reasoning_content: str = ""       # DeepSeek 等推理模型的思维链内容
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.name:
            d["name"] = self.name
        if self.options:
            d["options"] = self.options
        if self.reasoning_content:
            d["reasoning_content"] = self.reasoning_content
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id"),
            name=data.get("name"),
            options=data.get("options"),
            reasoning_content=data.get("reasoning_content", ""),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class AgentSession:
    """Agent 对话会话"""
    session_id: str
    world_id: str                    # 关联的世界观 ID（空字符串 = 全局模式）
    title: str                       # 会话标题
    messages: List[AgentMessage] = field(default_factory=list)
    usage: Dict[str, Any] = field(default_factory=dict)
    context_stats: Dict[str, Any] = field(default_factory=dict)
    context_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "world_id": self.world_id,
            "title": self.title,
            "messages": [m.to_dict() for m in self.messages],
            "usage": self.usage,
            "context_stats": self.context_stats,
            "context_snapshots": self.context_snapshots,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentSession":
        return cls(
            session_id=data.get("session_id", ""),
            world_id=data.get("world_id", ""),
            title=data.get("title", ""),
            messages=[AgentMessage.from_dict(m) for m in (data.get("messages") or [])],
            usage=data.get("usage") or {},
            context_stats=data.get("context_stats") or {},
            context_snapshots=data.get("context_snapshots") or [],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


# ============================================================
# 记忆条目
# ============================================================

@dataclass
class MemoryEntry:
    """Agent 记忆条目"""
    entry_id: str
    world_id: str
    key: str                         # 记忆键（如 "user_preference", "context_summary"）
    value: Any                       # 记忆内容
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "world_id": self.world_id,
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        return cls(
            entry_id=data.get("entry_id", ""),
            world_id=data.get("world_id", ""),
            key=data.get("key", ""),
            value=data.get("value"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


# ============================================================
# Skill 定义
# ============================================================

@dataclass
class Skill:
    """Agent Skill"""
    skill_id: str
    name: str
    description: str
    instructions: str                # Skill 的具体指令/流程
    world_id: str = ""               # 世界级 Skill（空 = 全局 Skill）
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions,
            "world_id": self.world_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        return cls(
            skill_id=data.get("skill_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            instructions=data.get("instructions", ""),
            world_id=data.get("world_id", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


# ============================================================
# AgentManager — 文件持久化仓库
# ============================================================

class AgentManager:
    """Agent 数据管理器（文件级持久化）"""

    AGENT_DIR = os.path.join(Config.UPLOAD_FOLDER, "agent")
    _lock = threading.RLock()

    @classmethod
    def _ensure_dir(cls, *subdirs: str):
        path = os.path.join(cls.AGENT_DIR, *subdirs)
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def _world_scope_name(cls, world_id: str = "") -> str:
        world_id = str(world_id or "").strip()
        if not world_id:
            return "_global"
        if not WorldManager.is_valid_world_id(world_id):
            raise ValueError(f"非法世界观 ID: {world_id}")
        return world_id

    # ---- Session ----

    @classmethod
    def _session_file(cls, session_id: str) -> str:
        return os.path.join(cls._ensure_dir("sessions"), f"{session_id}.json")

    @classmethod
    def create_session(cls, world_id: str = "", title: str = "") -> AgentSession:
        with cls._lock:
            sid = f"sess_{uuid.uuid4().hex[:12]}"
            session = AgentSession(
                session_id=sid,
                world_id=world_id,
                title=title or f"Conversation {datetime.now().strftime('%m-%d %H:%M')}",
            )
            cls.save_session(session)
            return session

    @classmethod
    def save_session(cls, session: AgentSession) -> AgentSession:
        with cls._lock:
            session.updated_at = datetime.now().isoformat()
            with open(cls._session_file(session.session_id), "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
            return session

    @classmethod
    def get_session(cls, session_id: str) -> Optional[AgentSession]:
        path = cls._session_file(session_id)
        if not os.path.exists(path):
            return None
        with cls._lock:
            with open(path, "r", encoding="utf-8") as f:
                return AgentSession.from_dict(json.load(f))

    @classmethod
    def list_sessions(cls, world_id: Optional[str] = None) -> List[AgentSession]:
        cls._ensure_dir("sessions")
        sessions = []
        for fname in os.listdir(os.path.join(cls.AGENT_DIR, "sessions")):
            if fname.endswith(".json"):
                sid = fname[:-5]
                session = cls.get_session(sid)
                if session:
                    if world_id is None or session.world_id == world_id:
                        sessions.append(session)
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    @classmethod
    def delete_session(cls, session_id: str) -> bool:
        with cls._lock:
            path = cls._session_file(session_id)
            if os.path.exists(path):
                os.remove(path)
                return True
            return False

    # ---- Agent.md ----

    @classmethod
    def _agent_md_file(cls, world_id: str) -> str:
        if world_id:
            return WorldManager._safe_join_world_path(world_id, "agent.md")
        return os.path.join(cls._ensure_dir(), "global_agent.md")

    @classmethod
    def get_agent_md(cls, world_id: str = "") -> str:
        path = cls._agent_md_file(world_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    @classmethod
    def save_agent_md(cls, content: str, world_id: str = "") -> None:
        path = cls._agent_md_file(world_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    # ---- Memory ----

    @classmethod
    def _memory_file(cls, world_id: str) -> str:
        return os.path.join(cls._ensure_dir("memory"), f"{cls._world_scope_name(world_id)}.json")

    @classmethod
    def get_memories(cls, world_id: str = "") -> Dict[str, Any]:
        path = cls._memory_file(world_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    @classmethod
    def set_memory(cls, key: str, value: Any, world_id: str = "") -> None:
        with cls._lock:
            path = cls._memory_file(world_id)
            memories = {}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    memories = json.load(f)
            memories[key] = value
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(memories, f, ensure_ascii=False, indent=2)

    @classmethod
    def get_memory(cls, key: str, world_id: str = "") -> Any:
        memories = cls.get_memories(world_id)
        return memories.get(key)

    @classmethod
    def delete_memory(cls, key: str, world_id: str = "") -> bool:
        with cls._lock:
            path = cls._memory_file(world_id)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    memories = json.load(f)
                if key in memories:
                    del memories[key]
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(memories, f, ensure_ascii=False, indent=2)
                    return True
            return False

    # ---- Skills ----

    @classmethod
    def _skills_file(cls, world_id: str = "") -> str:
        return os.path.join(cls._ensure_dir("skills"), f"{cls._world_scope_name(world_id)}.json")

    @classmethod
    def list_skills(cls, world_id: str = "") -> List[Skill]:
        path = cls._skills_file(world_id)
        skills = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    skills = [Skill.from_dict(s) for s in data]
        # 合并全局 Skills
        if world_id:
            global_skills = cls.list_skills("")
            existing_names = {s.name for s in skills}
            for gs in global_skills:
                if gs.name not in existing_names:
                    skills.append(gs)

        # 合并已启用的发现 Skills
        enabled_cfg = cls.get_enabled_discovered()
        if enabled_cfg:
            discovered = cls.scan_discovered_skills()
            existing_names = {s.name for s in skills}
            for ds in discovered:
                if enabled_cfg.get(ds["name"], False) and ds["name"] not in existing_names:
                    skills.append(Skill(
                        skill_id=f"disc_{ds['name']}",
                        name=ds["name"],
                        description=ds.get("description", ""),
                        instructions=ds.get("instructions", ""),
                        world_id="",
                    ))
        return skills

    @classmethod
    def save_skill(cls, skill: Skill) -> Skill:
        with cls._lock:
            path = cls._skills_file(skill.world_id)
            skills = []
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        skills = [Skill.from_dict(s) for s in data]
            # 如有同名则替换
            replaced = False
            for i, s in enumerate(skills):
                if s.skill_id == skill.skill_id or s.name == skill.name:
                    skills[i] = skill
                    replaced = True
                    break
            if not replaced:
                skills.append(skill)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump([s.to_dict() for s in skills], f, ensure_ascii=False, indent=2)
            return skill

    @classmethod
    def delete_skill(cls, skill_id: str, world_id: str = "") -> bool:
        with cls._lock:
            path = cls._skills_file(world_id)
            if not os.path.exists(path):
                return False
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    return False
            new_list = [s for s in data if s.get("skill_id") != skill_id]
            if len(new_list) == len(data):
                return False
            with open(path, "w", encoding="utf-8") as f:
                json.dump(new_list, f, ensure_ascii=False, indent=2)
            return True

    # ---- Discovered Skills (filesystem scan) ----

    # Directories to scan for skills
    SKILL_SCAN_DIRS = [
        os.path.expanduser("~/.agents/skills"),
        os.path.expanduser("~/.claude/skills"),
        os.path.expanduser("~/.openclaw/skills"),
    ]

    @classmethod
    def _discovered_config_file(cls) -> str:
        return os.path.join(cls._ensure_dir(), "discovered_skills.json")

    @classmethod
    def get_enabled_discovered(cls) -> Dict[str, bool]:
        """Returns {skill_name: enabled_bool} for discovered skills."""
        path = cls._discovered_config_file()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    @classmethod
    def set_discovered_enabled(cls, name: str, enabled: bool) -> None:
        with cls._lock:
            cfg = cls.get_enabled_discovered()
            cfg[name] = enabled
            with open(cls._discovered_config_file(), "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)

    @classmethod
    def scan_discovered_skills(cls) -> List[Dict[str, Any]]:
        """
        Scan standard skill directories for SKILL.md files.
        Returns list of {name, description, instructions, source_path, source_dir}
        """
        import re
        discovered = {}
        for scan_dir in cls.SKILL_SCAN_DIRS:
            if not os.path.isdir(scan_dir):
                continue
            try:
                for entry in os.listdir(scan_dir):
                    skill_dir = os.path.join(scan_dir, entry)
                    if not os.path.isdir(skill_dir):
                        continue
                    # Skip symlinks that don't resolve
                    if os.path.islink(skill_dir):
                        real = os.path.realpath(skill_dir)
                        if not os.path.isdir(real):
                            continue
                    skill_file = os.path.join(skill_dir, "SKILL.md")
                    if not os.path.isfile(skill_file):
                        continue

                    name = entry
                    description = ""
                    instructions = ""

                    try:
                        with open(skill_file, "r", encoding="utf-8") as f:
                            content = f.read()

                        # Parse YAML frontmatter
                        if content.startswith("---"):
                            end_idx = content.find("---", 3)
                            if end_idx > 0:
                                frontmatter = content[3:end_idx].strip()
                                body = content[end_idx + 3:].strip()
                                for line in frontmatter.split("\n"):
                                    line = line.strip()
                                    if line.startswith("name:"):
                                        name = line[5:].strip()
                                    elif line.startswith("description:"):
                                        description = line[12:].strip()
                                instructions = body
                            else:
                                instructions = content
                        else:
                            instructions = content
                    except Exception:
                        continue

                    # Don't override if already found from another source
                    if name not in discovered:
                        discovered[name] = {
                            "name": name,
                            "description": description,
                            "instructions": instructions[:5000],  # limit size
                            "source_path": skill_file,
                            "source_dir": os.path.basename(scan_dir),
                        }
            except Exception:
                continue

        return list(discovered.values())

    @classmethod
    def list_skills_with_discovered(cls, world_id: str = "") -> List[Dict[str, Any]]:
        """
        List manually-created skills + enabled discovered skills.
        Returns list of dicts with an extra 'origin' field ('created' or 'discovered').
        """
        created = cls.list_skills(world_id)
        result = []
        for s in created:
            d = s.to_dict()
            d["origin"] = "created"
            d["enabled"] = True
            result.append(d)

        # Merge in enabled discovered skills (skip if same name as created)
        created_names = {s["name"] for s in result}
        enabled_cfg = cls.get_enabled_discovered()
        if enabled_cfg:
            discovered = cls.scan_discovered_skills()
            for ds in discovered:
                if enabled_cfg.get(ds["name"], False) and ds["name"] not in created_names:
                    result.append({
                        "skill_id": f"disc_{ds['name']}",
                        "name": ds["name"],
                        "description": ds.get("description", ""),
                        "instructions": ds.get("instructions", ""),
                        "world_id": "",
                        "created_at": "",
                        "updated_at": "",
                        "origin": "discovered",
                        "enabled": True,
                    })
        return result
