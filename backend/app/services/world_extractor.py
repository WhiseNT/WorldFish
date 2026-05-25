"""
世界观提取服务
"""

from app.utils.llm_client import LLMClient
from app.utils.logger import get_logger

logger = get_logger('worldfish.service.world_extractor')


class WorldExtractor:
    """世界观提取器"""
    
    def __init__(self):
        self.llm_client = LLMClient(role="parser")
    
    def extract_from_text(self, text):
        """从文本提取世界观信息"""
        try:
            prompt = f"""
你是一个专业的世界观分析器，请从以下文本中提取出完整的世界观信息，包括：

1. 世界观基本信息：名称、描述、时代背景
2. 实体信息：人物、国家、组织等
3. 事件信息：重要事件、时间线
4. 设定信息：科技水平、政治体制、文化特点等

请以JSON格式返回，结构如下：
{
  "world_info": {
    "name": "世界观名称",
    "description": "世界观描述",
    "era": "时代背景"
  },
  "entities": [
    {
      "name": "实体名称",
      "type": "实体类型（人物/国家/组织等）",
      "attributes": {"属性1": "值1", "属性2": "值2"}
    }
  ],
  "events": [
    {
      "name": "事件名称",
      "description": "事件描述",
      "date": "事件时间",
      "entities": ["相关实体1", "相关实体2"]
    }
  ],
  "settings": {
    "科技水平": "描述",
    "政治体制": "描述",
    "文化特点": "描述"
  }
}

文本内容：
{text}
"""
            
            response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )
            
            # 解析LLM返回的JSON
            import json
            extracted_data = json.loads(response)
            
            logger.info(f"成功提取世界观信息，实体数量: {len(extracted_data.get('entities', []))}, 事件数量: {len(extracted_data.get('events', []))}")
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"提取世界观失败: {str(e)}")
            # 返回默认结构
            return {
                "world_info": {
                    "name": "未知世界观",
                    "description": "从文本中提取的世界观",
                    "era": "未知时代"
                },
                "entities": [],
                "events": [],
                "settings": {}
            }
