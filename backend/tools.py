import json
import os
import sys
from typing import Any, Callable

from langchain_core.messages import HumanMessage
from agent_policy import WRITE_INTENT_PATTERN, evaluate_tool_policy

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


OPENAI_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "搜索企业知识库。适用于查询非结构化业务文档、项目资料、技术文档和知识库内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "需要在企业知识库中检索的问题或关键词。",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_sql_database",
            "description": "只读查询结构化 MySQL 数据库。仅允许 SELECT、SHOW、DESCRIBE、EXPLAIN 类查询。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "自然语言数据库查询需求。禁止写入、删除、建表、改表等高风险操作。",
                    }
                },
                "required": ["query"],
            },
        },
    },
]


def _tool_result(tool: str, ok: bool, data: str = "", error: str | None = None, **metadata: Any) -> dict[str, Any]:
    return {
        "ok": ok,
        "tool": tool,
        "data": data,
        "error": error,
        **metadata,
    }


def search_knowledge_base(query: str) -> dict[str, Any]:
    if not query or not query.strip():
        return _tool_result("search_knowledge_base", False, error="query is required", sources=[])

    try:
        from rag_engine import rag_engine

        if rag_engine.ensemble_retriever is None:
            rag_engine.build_or_load()
        context, sources = rag_engine.retrieve(query.strip(), k=4)
        return _tool_result(
            "search_knowledge_base",
            True,
            data=context,
            sources=sources,
        )
    except Exception as exc:
        return _tool_result("search_knowledge_base", False, error=str(exc), sources=[])


def query_sql_database(query: str) -> dict[str, Any]:
    if not query or not query.strip():
        return _tool_result("query_sql_database", False, error="query is required", sql_type="readonly")

    if WRITE_INTENT_PATTERN.search(query):
        return _tool_result(
            "query_sql_database",
            False,
            error="write or schema-changing database operations are not allowed in this tool",
            sql_type="readonly",
        )

    try:
        from examples.mysql_agent import build_mysql_agent

        sql_app = build_mysql_agent()
        result = sql_app.invoke({
            "messages": [HumanMessage(content=query.strip())],
            "iterations": 0,
        })
        return _tool_result(
            "query_sql_database",
            True,
            data=result["messages"][-1].content,
            sql_type="readonly",
        )
    except Exception as exc:
        return _tool_result("query_sql_database", False, error=str(exc), sql_type="readonly")


TOOL_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    "search_knowledge_base": search_knowledge_base,
    "query_sql_database": query_sql_database,
}


def execute_tool_call(
    name: str,
    arguments: str | dict[str, Any] | None,
    user_permissions: set[str] | None = None,
) -> dict[str, Any]:
    tool = TOOL_REGISTRY.get(name)
    if tool is None:
        return _tool_result(name or "unknown", False, error="unknown tool")

    try:
        parsed_args = json.loads(arguments or "{}") if isinstance(arguments, str) else (arguments or {})
    except json.JSONDecodeError as exc:
        return _tool_result(name, False, error=f"invalid arguments: {exc}")

    if not isinstance(parsed_args, dict):
        return _tool_result(name, False, error="invalid arguments: expected object")

    decision = evaluate_tool_policy(name, parsed_args, user_permissions or set())
    if not decision.allowed:
        return _tool_result(
            name,
            False,
            error=decision.reason,
            policy=decision.as_dict(),
        )

    try:
        return tool(**parsed_args)
    except TypeError as exc:
        return _tool_result(name, False, error=f"invalid arguments: {exc}")
    except Exception as exc:
        return _tool_result(name, False, error=str(exc))
