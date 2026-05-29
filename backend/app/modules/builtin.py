"""内置模块声明。"""

from __future__ import annotations

from app.core.modules import ModuleManifest, ModuleRegistry
from app.api import agent_bp, collab_bp, evolution_bp, graph_bp, modules_bp, project_bp, rag_bp, report_bp, simulation_bp, world_build_bp

from .definitions import BackendModuleDefinition, BlueprintBinding


def _manifest(
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
    return ModuleManifest(
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
    )


def _binding(blueprint, url_prefix: str, guard: bool = True):
    return BlueprintBinding(blueprint=blueprint, url_prefix=url_prefix, guard=guard)


def get_builtin_module_definitions():
    """返回当前仓库已有能力对应的后端模块定义。"""
    return [
        BackendModuleDefinition(
            manifest=_manifest(
                'world-builder',
                '世界观构建',
                '管理世界观、实体、事件、地图与项目基础数据。',
                'core',
                routes=['/api/world', '/api/project'],
                nav=[{'label': '构建世界观', 'path': '/world-builder', 'order': 10}],
                capabilities=['api', 'ui', 'world-metadata'],
            ),
            blueprints=[
                _binding(world_build_bp, '/api/world'),
                _binding(project_bp, '/api/project'),
            ],
        ),
        BackendModuleDefinition(
            manifest=_manifest(
                'knowledge-graph',
                '知识图谱',
                '从文本资料构建本体和关系图谱，并提供图谱查询接口。',
                'core',
                routes=['/api/graph'],
                depends=['world-builder'],
                capabilities=['api', 'graph', 'ontology'],
            ),
            blueprints=[_binding(graph_bp, '/api/graph')],
        ),
        BackendModuleDefinition(
            manifest=_manifest(
                'rag',
                '知识库 / RAG',
                '上传资料、构建向量索引并在世界观上下文中检索资料。',
                'ai',
                routes=['/api/rag', '/api/files', '/api/worlds'],
                nav=[{'label': '知识库', 'path': '/rag', 'order': 30}],
                depends=['world-builder'],
                capabilities=['api', 'ui', 'rag', 'embedding'],
            ),
            blueprints=[_binding(rag_bp, '/api')],
        ),
        BackendModuleDefinition(
            manifest=_manifest(
                'simulation',
                '模拟推演',
                '基于世界观和角色档案运行多轮推演与演化。',
                'ai',
                routes=['/api/simulation', '/api/evolution'],
                nav=[{'label': '开始推演', 'path': '/simulation/new', 'order': 20}],
                depends=['world-builder'],
                capabilities=['api', 'ui', 'simulation'],
            ),
            blueprints=[
                _binding(simulation_bp, '/api/simulation'),
                _binding(evolution_bp, '/api/evolution'),
            ],
        ),
        BackendModuleDefinition(
            manifest=_manifest(
                'report',
                '报告生成',
                '汇总模拟、图谱和资料上下文，生成结构化报告。',
                'ai',
                routes=['/api/report'],
                depends=['simulation'],
                capabilities=['api', 'report', 'agent'],
            ),
            blueprints=[_binding(report_bp, '/api/report')],
        ),
        BackendModuleDefinition(
            manifest=_manifest(
                'agent',
                'Agent 助手',
                '提供浮动 Agent、工具调用和协作式信息整理能力。',
                'ai',
                routes=['/api/agent'],
                capabilities=['api', 'agent', 'tools'],
            ),
            blueprints=[_binding(agent_bp, '/api/agent')],
        ),
        BackendModuleDefinition(
            manifest=_manifest(
                'collaboration',
                '联机房间',
                '提供工作区、房间、成员在线状态、事件日志和 HTTP 同步基础设施。',
                'system',
                routes=['/api/collab'],
                nav=[{'label': '联机房间', 'path': '/collab', 'order': 40}],
                capabilities=['api', 'ui', 'workspace', 'room', 'presence', 'event-log', 'sync'],
            ),
            blueprints=[_binding(collab_bp, '/api/collab')],
        ),
        BackendModuleDefinition(
            manifest=_manifest(
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
            blueprints=[_binding(modules_bp, '/api/modules', guard=False)],
        ),
    ]


def register_builtin_modules(registry: ModuleRegistry):
    """兼容旧入口：仅注册 manifest，不安装蓝图。"""
    from app.core.modules import ManifestModule

    existing = {item['manifest']['id'] for item in registry.list(include_private=True)}
    for definition in get_builtin_module_definitions():
        if definition.manifest.id not in existing:
            registry.register(ManifestModule(definition.manifest))
