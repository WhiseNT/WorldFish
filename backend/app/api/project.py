"""项目管理API。"""

from flask import Blueprint, request, jsonify
from app.models.project import ProjectManager
from app.models.world import WorldManager
from app.utils.logger import get_logger

project_bp = Blueprint('project', __name__)
logger = get_logger('worldfish.api.project')


@project_bp.route('/create', methods=['POST'])
def create_project():
    """创建新项目"""
    try:
        data = request.json or {}
        world_id = data.get('world_id')
        world_text = None

        if world_id:
            world = WorldManager.get_world(world_id)
            if not world:
                return jsonify({
                    'success': False,
                    'message': '关联世界观不存在'
                }), 404
            world_text = world.to_text()

        project = ProjectManager.create_project(
            name=data.get('name'),
            description=data.get('description', ''),
            world_id=world_id,
            settings=data.get('settings', {})
        )

        if data.get('simulation_requirement'):
            project.simulation_requirement = data.get('simulation_requirement', '')

        if world_text:
            project.total_text_length = len(world_text)
            project.settings = {
                **(project.settings or {}),
                'source_type': 'world_builder',
                'source_world_id': world_id,
            }
            ProjectManager.save_extracted_text(project.project_id, world_text)

        ProjectManager.save_project(project)

        return jsonify({
            'success': True,
            'project_id': project.project_id,
            'project': project.to_dict(),
            'message': '项目创建成功'
        })
    except Exception as e:
        logger.error(f"创建项目失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'创建失败: {str(e)}'
        }), 500


@project_bp.route('/', methods=['GET'])
def get_projects():
    """获取项目列表"""
    try:
        limit = request.args.get('limit', 50, type=int)
        world_id = request.args.get('world_id') or None
        projects = ProjectManager.list_projects(limit=limit, world_id=world_id)
        return jsonify({
            'success': True,
            'projects': [p.to_dict() for p in projects]
        })
    except Exception as e:
        logger.error(f"获取项目列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}'
        }), 500


@project_bp.route('/<project_id>', methods=['GET'])
def get_project(project_id):
    """获取项目详情"""
    try:
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                'success': False,
                'message': '项目不存在'
            }), 404
        
        return jsonify({
            'success': True,
            'project': project.to_dict()
        })
    except Exception as e:
        logger.error(f"获取项目失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}'
        }), 500


@project_bp.route('/<project_id>', methods=['PUT'])
def update_project(project_id):
    """更新项目信息"""
    try:
        data = request.json
        project = ProjectManager.update_project(project_id, data)
        if project is None:
            return jsonify({
                'success': False,
                'message': '项目不存在'
            }), 404

        return jsonify({
            'success': True,
            'message': '项目更新成功'
        })
    except Exception as e:
        logger.error(f"更新项目失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500


@project_bp.route('/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    """删除项目"""
    try:
        deleted = ProjectManager.delete_project(project_id)
        if not deleted:
            return jsonify({
                'success': False,
                'message': '项目不存在'
            }), 404

        return jsonify({
            'success': True,
            'message': '项目删除成功'
        })
    except Exception as e:
        logger.error(f"删除项目失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }), 500
