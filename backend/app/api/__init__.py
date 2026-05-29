"""
API路由模块
"""

from flask import Blueprint

# 创建蓝图
graph_bp = Blueprint('graph', __name__)
simulation_bp = Blueprint('simulation', __name__)
report_bp = Blueprint('report', __name__)
world_build_bp = Blueprint('world_build', __name__)
agent_bp = Blueprint('agent', __name__)

# 导入模块
from . import graph  # noqa: E402, F401
from . import simulation  # noqa: E402, F401
from . import report  # noqa: E402, F401
from . import world_build  # noqa: E402, F401
from . import project  # noqa: E402, F401

from . import evolution  # noqa: E402, F401
from . import rag  # noqa: E402, F401
from . import agent  # noqa: E402, F401
from . import modules  # noqa: E402, F401
from . import collab  # noqa: E402, F401

# 从模块获取蓝图
project_bp = project.project_bp
evolution_bp = evolution.evolution_bp
rag_bp = rag.rag_bp
modules_bp = modules.modules_bp
collab_bp = collab.collab_bp

