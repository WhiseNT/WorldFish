"""内置模块声明。"""

from __future__ import annotations

from app.core.modules import ManifestModule, ModuleManifest, ModuleRegistry


def _module(
    module_id: str,
    name: str,
    description: str,
    category: str,
    routes=None,
    nav=None,
    depends=None,
    capabilities=None,
    enabled_by_default: bool = True,
):
    return ManifestModule(ModuleManifest(
        id=module_id,
        name=name,
        version='0.1.0',
        description=description,
        category=category,
        depends=depends or [],
        routes=routes or [],
        nav=nav or [],
        capabilities=capabilities or ['api', 'ui'],
        enabled_by_default=enabled_by_default,
    ))


def register_builtin_modules(registry: ModuleRegistry):
    """注册当前仓库已有能力对应的内置模块。"""
    modules = [
        _module(
            'world-builder',
            '世界观构建',
            '管理世界观、实体、事件、地图与项目基础数据。',
            'core',
            routes=['/api/world', '/api/project'],
            nav=[{'label': '构建世界观', 'path': '/world-builder', 'order': 10}],
            capabilities=['api', 'ui', 'world-metadata'],
        ),
        _module(
            'knowledge-graph',
            '知识图谱',
            '从文本资料构建本体和关系图谱，并提供图谱查询接口。',
            'core',
            routes=['/api/graph'],
            depends=['world-builder'],
            capabilities=['api', 'graph', 'ontology'],
        ),
        _module(
            'rag',
            '知识库 / RAG',
            '上传资料、构建向量索引并在世界观上下文中检索资料。',
            'ai',
            routes=['/api/rag', '/api/files', '/api/worlds'],
            nav=[{'label': '知识库', 'path': '/rag', 'order': 30}],
            depends=['world-builder'],
            capabilities=['api', 'ui', 'rag', 'embedding'],
        ),
        _module(
            'simulation',
            '模拟推演',
            '基于世界观和角色档案运行多轮推演与演化。',
            'ai',
            routes=['/api/simulation', '/api/evolution'],
            nav=[{'label': '开始推演', 'path': '/simulation/new', 'order': 20}],
            depends=['world-builder'],
            capabilities=['api', 'ui', 'simulation'],
        ),
        _module(
            'report',
            '报告生成',
            '汇总模拟、图谱和资料上下文，生成结构化报告。',
            'ai',
            routes=['/api/report'],
            depends=['simulation'],
            capabilities=['api', 'report', 'agent'],
        ),
        _module(
            'agent',
            'Agent 助手',
            '提供浮动 Agent、工具调用和协作式信息整理能力。',
            'ai',
            routes=['/api/agent'],
            capabilities=['api', 'agent', 'tools'],
        ),
        _module(
            'settings',
            '系统设置',
            '管理 LLM、Embedding 与模块启停等系统配置。',
            'system',
            routes=['/api/modules'],
            nav=[
                {'label': 'LLM 配置', 'path': '/settings/llm', 'order': 900},
                {'label': '模块', 'path': '/settings/modules', 'order': 910},
            ],
            capabilities=['api', 'ui', 'settings'],
        ),
    ]

    existing = {item['manifest']['id'] for item in registry.list(include_private=True)}
    for module in modules:
        if module.manifest.id not in existing:
            registry.register(module)
