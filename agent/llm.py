"""模型初始化：延迟创建，未配置环境变量时导入模块不会报错。"""
import os

from dotenv import find_dotenv, load_dotenv
from langchain.chat_models import init_chat_model

# 递归查找项目根目录的 .env 并加载
load_dotenv(find_dotenv())

# 支持从独立文件读取密钥，避免把敏感信息写进项目配置
api_key_file = os.getenv("OPENAI_API_KEY_FILE")
if not os.getenv("OPENAI_API_KEY") and api_key_file:
    with open(api_key_file, "r", encoding="utf-8") as key_file:
        os.environ["OPENAI_API_KEY"] = key_file.read().strip()

_model = None


def get_model():
    """延迟初始化并缓存 ChatModel（兼容任意 OpenAI 兼容协议的服务商）。"""
    global _model
    if _model is None:
        _model = init_chat_model(
            model=os.getenv("LLM_QWEN_MAX"),
            model_provider="openai",
        )
    return _model