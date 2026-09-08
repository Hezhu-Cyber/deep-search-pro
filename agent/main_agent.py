"""主智能体：基于 deepagents 的多智能体编排与异步流式执行引擎。"""
import shutil
from pathlib import Path

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver

from agent.llm import get_model
from agent.prompts import main_agent_content
from agent.subagents.database_query_agent import database_query_agent
from agent.subagents.knowledge_base_agent import knowledge_base_agent
from agent.subagents.network_search_agent import network_search_agent
from api.context import (
    reset_session_context,
    set_session_context,
    set_thread_context,
)
from api.monitor import monitor
from tools.markdown_tools import generate_markdown
from tools.pdf_tools import convert_md_to_pdf
from tools.upload_file_read_tool import read_file_content

# 主智能体延迟初始化：首次执行任务时才创建，加快服务启动、便于测试与热更新。
_agent_cache = None


def get_main_agent():
    """创建并缓存主智能体（deepagents 多智能体编排）。"""
    global _agent_cache
    if _agent_cache is None:
        _agent_cache = create_deep_agent(
            model=get_model(),
            system_prompt=main_agent_content["system_prompt"],
            tools=[generate_markdown, convert_md_to_pdf, read_file_content],
            checkpointer=InMemorySaver(),
            subagents=[
                database_query_agent,
                network_search_agent,
                knowledge_base_agent,
            ],
        )
    return _agent_cache


project_root_path = Path(__file__).parents[1].resolve()


async def run_deep_agent(task_query: str, session_id: str):
    """异步流式执行主智能体，并把每一步进度推送到前端 / 落盘为执行轨迹。

    Args:
        task_query: 用户提交的研究任务。
        session_id: 前端会话 ID（用于隔离输出目录与 WebSocket 通道）。
    """
    # 1. 为当前会话创建独立工作目录 output/session_<id>
    session_dir = project_root_path / "output" / f"session_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_dir_str = str(session_dir).replace("\\", "/")
    relative_session_dir_str = str(session_dir.relative_to(project_root_path)).replace(
        "\\", "/"
    )

    # 2. 若存在上传文件（updated/session_<id>），复制到工作目录并提示模型优先读取
    updated_dir_path = project_root_path / "updated" / f"session_{session_id}"
    updated_info_prompt = ""
    if updated_dir_path.exists():
        files = [f.name for f in updated_dir_path.iterdir() if f.is_file()]
        if files:
            for filename in files:
                shutil.copy2(updated_dir_path / filename, session_dir / filename)
            updated_info_prompt = (
                "\n    [已上传文件] 已加载到工作目录:\n"
                + "\n".join([f"    - {f}" for f in files])
                + "\n    请优先使用工具（read_file_content）读取并参考这些文件。"
            )

    # 3. 会话上下文（ContextVar）：供工具与监控在深层调用中安全取用
    session_dir_token = set_session_context(session_dir_str)
    session_id_token = set_thread_context(session_id)
    monitor.report_session_dir(session_dir_str)

    config = {"configurable": {"thread_id": session_id}}
    path_instruction = f"""
    【工作环境指令】
    工作目录: {relative_session_dir_str}
    {updated_info_prompt}

    规则：
    1. 新生成文件必须保存到工作目录：'{relative_session_dir_str}/filename'
    2. 读取已上传的文件时，请直接将文件名（例如：'开篇.txt'）作为 filename 参数传入（read_file_content）读取工具，不要带上任何目录前缀。
    3. 使用相对路径，禁止使用绝对路径
    4. 若存在上传文件，请先分析内容
    """

    try:
        # 4. 流式执行；解析 deepagents 输出，把子智能体调用与最终结果上报给 monitor
        async for chunk in get_main_agent().astream(
            {
                "messages": [
                    {"role": "user", "content": task_query + path_instruction}
                ]
            },
            config=config,
        ):
            for node_name, state in chunk.items():
                if not state or "messages" not in state:
                    continue
                messages = state["messages"]
                if not messages or not isinstance(messages, list):
                    continue
                last_msg = messages[-1]
                if node_name != "model":
                    continue
                if last_msg.tool_calls:
                    # 子智能体调用：deepagents 以 task 工具的形式调度子智能体
                    for tool_call in last_msg.tool_calls:
                        if tool_call["name"] == "task":
                            monitor.report_assistant(
                                tool_call["args"]["subagent_type"],
                                {"description": tool_call["args"]["description"]},
                            )
                elif last_msg.content:
                    # 主智能体最终结果
                    monitor.report_task_result(last_msg.content)
    except Exception as exc:  # noqa: BLE001
        monitor._emit("error", f"执行主智能发生异常信息：{exc}")
    finally:
        reset_session_context(session_dir_token, session_id_token)