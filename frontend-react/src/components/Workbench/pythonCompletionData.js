/**
 * Python 代码方法与 API 自动快捷提醒数据集 (IntelliSense & CheatSheet)
 * 支持输入点号（例如 `os.`、`json.`、`client.`、`workflow.`、`collection.`）自动匹配下属所有方法与变量
 */

// ==========================================
// 1. 模块/对象级点号属性访问映射表 (Dot Completion Map)
// ==========================================
export const MODULE_MEMBERS_MAP = {
  // 1.1 os 模块下的所有常用方法和变量
  'os': [
    { name: 'getenv', kind: 'Method', signature: 'os.getenv(key: str, default: Optional[str] = None) -> Optional[str]', snippet: 'getenv("${1:KEY}", "${2:default}")', doc: '获取指定环境变量的值。如果键不存在，则返回默认值 default（缺省为 None）。' },
    { name: 'environ', kind: 'Variable', signature: 'os.environ: _Environ[str]', snippet: 'environ', doc: '映射环境变量的字典式对象。支持读取如 os.environ["PATH"] 或设置 os.environ["KEY"] = "val"。' },
    { name: 'path', kind: 'Module', signature: 'os.path: module', snippet: 'path', doc: '提供平台通用的文件路径处理子模块（包含 join, exists, abspath, dirname, split 等）。' },
    { name: 'makedirs', kind: 'Method', signature: 'os.makedirs(name: str, mode: int = 0o777, exist_ok: bool = False) -> None', snippet: 'makedirs("${1:path}", exist_ok=${2:True})', doc: '递归创建多级目录。当 exist_ok=True 时，若目标目录已存在则不抛出异常。' },
    { name: 'mkdir', kind: 'Method', signature: 'os.mkdir(path: str, mode: int = 0o777) -> None', snippet: 'mkdir("${1:path}")', doc: '创建单层目录。如果目录已存在或父目录缺失，则抛出 OSError。' },
    { name: 'listdir', kind: 'Method', signature: 'os.listdir(path: str = ".") -> List[str]', snippet: 'listdir("${1:.}")', doc: '返回指定路径目录下所有文件和子目录的名称列表（不含 "." 和 ".."）。' },
    { name: 'remove', kind: 'Method', signature: 'os.remove(path: str) -> None', snippet: 'remove("${1:filepath}")', doc: '删除指定路径的文件。若路径为目录，请使用 os.rmdir()。' },
    { name: 'rmdir', kind: 'Method', signature: 'os.rmdir(path: str) -> None', snippet: 'rmdir("${1:dirpath}")', doc: '删除指定的空目录。如果目录非空则会抛出 OSError。' },
    { name: 'rename', kind: 'Method', signature: 'os.rename(src: str, dst: str) -> None', snippet: 'rename("${1:src}", "${2:dst}")', doc: '重命名或移动文件或目录。从 src 变更为 dst。' },
    { name: 'getcwd', kind: 'Method', signature: 'os.getcwd() -> str', snippet: 'getcwd()', doc: '获取并返回当前进程的工作目录绝对路径。' },
    { name: 'chdir', kind: 'Method', signature: 'os.chdir(path: str) -> None', snippet: 'chdir("${1:path}")', doc: '将当前工作目录更改为指定路径 path。' },
    { name: 'walk', kind: 'Method', signature: 'os.walk(top: str, topdown: bool = True) -> Iterator[Tuple[str, List[str], List[str]]]', snippet: 'walk("${1:dirpath}")', doc: '通过在目录树中游走输出目录中的文件名。产出 (dirpath, dirnames, filenames)。' },
    { name: 'system', kind: 'Method', signature: 'os.system(command: str) -> int', snippet: 'system("${1:echo hello}")', doc: '在子 shell 中执行指定操作系统命令（注：生产沙箱内受 AST 安全策略管控）。' },
    { name: 'cpu_count', kind: 'Method', signature: 'os.cpu_count() -> Optional[int]', snippet: 'cpu_count()', doc: '返回系统中的 CPU 核心数，若无法确定则返回 None。' },
    { name: 'sep', kind: 'Variable', signature: 'os.sep: str', snippet: 'sep', doc: '当前操作系统的路径分隔符（Unix 为 "/"，Windows 为 "\\"）。' },
    { name: 'linesep', kind: 'Variable', signature: 'os.linesep: str', snippet: 'linesep', doc: '当前操作系统的换行分隔符（Unix 为 "\\n"，Windows 为 "\\r\\n"）。' },
    { name: 'name', kind: 'Variable', signature: 'os.name: str', snippet: 'name', doc: '操作系统依赖模块的名称（如 "posix", "nt", "java"）。' }
  ],

  // 1.2 os.path 子模块方法与变量
  'os.path': [
    { name: 'join', kind: 'Method', signature: 'os.path.join(path: str, *paths: str) -> str', snippet: 'join(${1:path1}, ${2:path2})', doc: '智能拼接一个或多个路径组件，自动补充平台对应的斜杠分隔符。' },
    { name: 'exists', kind: 'Method', signature: 'os.path.exists(path: str) -> bool', snippet: 'exists("${1:path}")', doc: '检测指定路径的文件或目录是否存在。' },
    { name: 'abspath', kind: 'Method', signature: 'os.path.abspath(path: str) -> str', snippet: 'abspath("${1:path}")', doc: '返回指定路径的归一化绝对路径版本。' },
    { name: 'dirname', kind: 'Method', signature: 'os.path.dirname(path: str) -> str', snippet: 'dirname("${1:path}")', doc: '返回文件路径的目录名称部分。' },
    { name: 'basename', kind: 'Method', signature: 'os.path.basename(path: str) -> str', snippet: 'basename("${1:path}")', doc: '返回路径的基名（文件名或末级目录名）。' },
    { name: 'splitext', kind: 'Method', signature: 'os.path.splitext(path: str) -> Tuple[str, str]', snippet: 'splitext("${1:path}")', doc: '将路径分割为 (文件名路径, 扩展名) 元组，例如 ("report", ".pdf")。' },
    { name: 'split', kind: 'Method', signature: 'os.path.split(path: str) -> Tuple[str, str]', snippet: 'split("${1:path}")', doc: '将路径拆分为 (目录, 文件名) 二元组。' },
    { name: 'isfile', kind: 'Method', signature: 'os.path.isfile(path: str) -> bool', snippet: 'isfile("${1:path}")', doc: '判断路径是否为现有的常规文件。' },
    { name: 'isdir', kind: 'Method', signature: 'os.path.isdir(path: str) -> bool', snippet: 'isdir("${1:path}")', doc: '判断路径是否为现有的目录。' },
    { name: 'getsize', kind: 'Method', signature: 'os.path.getsize(path: str) -> int', snippet: 'getsize("${1:path}")', doc: '返回文件的大小（以字节为单位）。' }
  ],
  'path': [
    { name: 'join', kind: 'Method', signature: 'path.join(path: str, *paths: str) -> str', snippet: 'join(${1:path1}, ${2:path2})', doc: '智能拼接一个或多个路径组件。' },
    { name: 'exists', kind: 'Method', signature: 'path.exists(path: str) -> bool', snippet: 'exists("${1:path}")', doc: '检测指定路径的文件或目录是否存在。' },
    { name: 'abspath', kind: 'Method', signature: 'path.abspath(path: str) -> str', snippet: 'abspath("${1:path}")', doc: '返回指定路径的绝对路径。' }
  ],

  // 1.3 json 模块
  'json': [
    { name: 'dumps', kind: 'Method', signature: 'json.dumps(obj: Any, ensure_ascii: bool = True, indent: Optional[int] = None) -> str', snippet: 'dumps(${1:obj}, ensure_ascii=${2:False}, indent=${3:2})', doc: '将 Python 结构对象序列化为格式化 JSON 字符串。' },
    { name: 'loads', kind: 'Method', signature: 'json.loads(s: str) -> Any', snippet: 'loads(${1:json_str})', doc: '将包含 JSON 文档的字符串反序列化为 Python 字典/列表对象。' },
    { name: 'dump', kind: 'Method', signature: 'json.dump(obj: Any, fp: IO[str], indent: Optional[int] = None) -> None', snippet: 'dump(${1:obj}, ${2:file_obj}, indent=${3:2})', doc: '将 Python 对象序列化为 JSON 并写入文件句柄。' },
    { name: 'load', kind: 'Method', signature: 'json.load(fp: IO[str]) -> Any', snippet: 'load(${1:file_obj})', doc: '从文件句柄读取并反序列化 JSON 文档。' },
    { name: 'JSONDecodeError', kind: 'Class', signature: 'json.JSONDecodeError', snippet: 'JSONDecodeError', doc: '反序列化非法 JSON 文本时抛出的内置异常类。' }
  ],

  // 1.4 asyncio 模块
  'asyncio': [
    { name: 'run', kind: 'Method', signature: 'asyncio.run(coro: Coroutine) -> Any', snippet: 'run(${1:main()})', doc: '运行异步主协程，自动创建、运行并关闭事件循环。' },
    { name: 'gather', kind: 'Method', signature: 'asyncio.gather(*aws, return_exceptions: bool = False) -> List[Any]', snippet: 'gather(${1:task1}, ${2:task2})', doc: '并发调度执行多个异步协程任务并等待汇总结果列表。' },
    { name: 'sleep', kind: 'Method', signature: 'asyncio.sleep(delay: float, result: Any = None) -> Coroutine', snippet: 'sleep(${1:1})', doc: '非阻塞挂起当前协程任务指定秒数。' },
    { name: 'create_task', kind: 'Method', signature: 'asyncio.create_task(coro: Coroutine) -> Task', snippet: 'create_task(${1:coro()})', doc: '将协程包装为 Task 放入当前事件循环并发调度。' },
    { name: 'Queue', kind: 'Class', signature: 'asyncio.Queue(maxsize: int = 0)', snippet: 'Queue()', doc: '专为协程优化的 FIFO 异步队列数据结构。' }
  ],

  // 1.5 sys 模块
  'sys': [
    { name: 'path', kind: 'Variable', signature: 'sys.path: List[str]', snippet: 'path', doc: '包含模块搜索路径的目录字符串列表。' },
    { name: 'argv', kind: 'Variable', signature: 'sys.argv: List[str]', snippet: 'argv', doc: '命令行参数列表，argv[0] 通常为脚本文件路径。' },
    { name: 'exit', kind: 'Method', signature: 'sys.exit(arg: Optional[Any] = 0) -> None', snippet: 'exit(${1:0})', doc: '退出当前 Python 进程，退出状态码 0 代表成功。' },
    { name: 'version', kind: 'Variable', signature: 'sys.version: str', snippet: 'version', doc: '当前 Python 解释器的版本号与编译环境信息。' }
  ],

  // 1.6 time 模块
  'time': [
    { name: 'sleep', kind: 'Method', signature: 'time.sleep(secs: float) -> None', snippet: 'sleep(${1:1})', doc: '同步阻塞当前线程指定秒数。' },
    { name: 'time', kind: 'Method', signature: 'time.time() -> float', snippet: 'time()', doc: '返回自 Unix 纪元以来的浮点秒数时间戳。' },
    { name: 'perf_counter', kind: 'Method', signature: 'time.perf_counter() -> float', snippet: 'perf_counter()', doc: '高精度单调性能计数器，常用于基准耗时评测。' }
  ],

  // 1.7 re 正则模块
  're': [
    { name: 'compile', kind: 'Method', signature: 're.compile(pattern: str, flags: int = 0) -> Pattern', snippet: 'compile(r"${1:pattern}")', doc: '编译正则表达式为 Pattern 对象，大幅提升高频匹配效率。' },
    { name: 'search', kind: 'Method', signature: 're.search(pattern: str, string: str, flags: int = 0) -> Optional[Match]', snippet: 'search(r"${1:pattern}", ${2:text})', doc: '扫描整个字符串，返回第一个成功匹配的 Match 对象。' },
    { name: 'match', kind: 'Method', signature: 're.match(pattern: str, string: str, flags: int = 0) -> Optional[Match]', snippet: 'match(r"${1:pattern}", ${2:text})', doc: '仅从字符串的开头位置尝试匹配正则表达式。' },
    { name: 'findall', kind: 'Method', signature: 're.findall(pattern: str, string: str, flags: int = 0) -> List[str]', snippet: 'findall(r"${1:pattern}", ${2:text})', doc: '以列表形式返回字符串中所有非重叠匹配项。' },
    { name: 'sub', kind: 'Method', signature: 're.sub(pattern: str, repl: str, string: str, count: int = 0) -> str', snippet: 'sub(r"${1:pattern}", "${2:repl}", ${3:text})', doc: '将匹配到的模式子串替换为目标字符串 repl。' }
  ],

  // 1.8 LangGraph 状态图实例 (workflow / graph)
  'workflow': [
    { name: 'add_node', kind: 'Method', signature: 'workflow.add_node(node_name: str, action_func: Callable) -> None', snippet: 'add_node("${1:node_name}", ${2:action_func})', doc: '向状态图中添加处理节点。' },
    { name: 'add_edge', kind: 'Method', signature: 'workflow.add_edge(start_node: str, end_node: str) -> None', snippet: 'add_edge("${1:start}", "${2:end}")', doc: '添加确定性单向流转连边。' },
    { name: 'add_conditional_edges', kind: 'Method', signature: 'workflow.add_conditional_edges(source: str, path_func: Callable, path_map: dict) -> None', snippet: 'add_conditional_edges("${1:source}", ${2:route_func}, {"${3:condition}": "${4:target}"})', doc: '添加条件动态路由分支连边。' },
    { name: 'compile', kind: 'Method', signature: 'workflow.compile(checkpointer=None, interrupt_before=None, interrupt_after=None) -> CompiledStateGraph', snippet: 'compile(checkpointer=${1:MemorySaver()})', doc: '将状态图网络编译为可执行应用实例。' }
  ],
  'graph': [
    { name: 'add_node', kind: 'Method', signature: 'graph.add_node(node_name: str, action_func: Callable) -> None', snippet: 'add_node("${1:node_name}", ${2:action_func})', doc: '向状态图中添加处理节点。' },
    { name: 'add_edge', kind: 'Method', signature: 'graph.add_edge(start_node: str, end_node: str) -> None', snippet: 'add_edge("${1:start}", "${2:end}")', doc: '添加确定性连边。' },
    { name: 'add_conditional_edges', kind: 'Method', signature: 'graph.add_conditional_edges(source: str, path_func: Callable, path_map: dict) -> None', snippet: 'add_conditional_edges("${1:source}", ${2:route_func}, {"${3:condition}": "${4:target}"})', doc: '添加条件路由分支连边。' },
    { name: 'compile', kind: 'Method', signature: 'graph.compile(checkpointer=None) -> CompiledStateGraph', snippet: 'compile(checkpointer=${1:MemorySaver()})', doc: '将状态图编译为应用实例。' }
  ],

  // 1.9 编译后的 LangGraph 应用 (app)
  'app': [
    { name: 'invoke', kind: 'Method', signature: 'app.invoke(input: dict, config: Optional[dict] = None) -> dict', snippet: 'invoke({"messages": [{"role": "user", "content": "${1:你好}"}]})', doc: '同步流转执行图，返回最终状态 state。' },
    { name: 'ainvoke', kind: 'Method', signature: 'await app.ainvoke(input: dict, config: Optional[dict] = None) -> dict', snippet: 'ainvoke({"messages": [{"role": "user", "content": "${1:你好}"}]})', doc: '异步流转执行状态图。' },
    { name: 'stream', kind: 'Method', signature: 'app.stream(input: dict, config: Optional[dict] = None, stream_mode: str = "values")', snippet: 'stream({"messages": [{"role": "user", "content": "${1:你好}"}]}, stream_mode="${2:values}")', doc: '流式返回节点执行过程与状态增量。' },
    { name: 'astream', kind: 'Method', signature: 'app.astream(input: dict, config: Optional[dict] = None, stream_mode: str = "values")', snippet: 'astream({"messages": [{"role": "user", "content": "${1:你好}"}]}, stream_mode="${2:values}")', doc: '异步流式返回。' },
    { name: 'get_state', kind: 'Method', signature: 'app.get_state(config: dict) -> StateSnapshot', snippet: 'get_state(config={"configurable": {"thread_id": "${1:thread_1}"}})', doc: '获取指定会话 thread_id 的最新检查点状态快照。' },
    { name: 'update_state', kind: 'Method', signature: 'app.update_state(config: dict, values: dict, as_node: Optional[str] = None)', snippet: 'update_state(config, {"${1:key}": "${2:val}"})', doc: '向状态图持久化快照中注入更新值。' }
  ],

  // 1.10 大模型 Client 实例 (client)
  'client': [
    { name: 'chat', kind: 'Module', signature: 'client.chat: Chat', snippet: 'chat', doc: '包含 completions 对话模型交互服务。' },
    { name: 'embeddings', kind: 'Module', signature: 'client.embeddings: Embeddings', snippet: 'embeddings', doc: '文本嵌入向量生成服务。' },
    { name: 'models', kind: 'Module', signature: 'client.models: Models', snippet: 'models', doc: '查询可用模型列表与元数据。' },
    { name: 'api_key', kind: 'Variable', signature: 'client.api_key: str', snippet: 'api_key', doc: '当前配置的 API Key 凭证。' },
    { name: 'base_url', kind: 'Variable', signature: 'client.base_url: URL', snippet: 'base_url', doc: '当前配置的模型网关代理根 URL。' }
  ],
  'client.chat': [
    { name: 'completions', kind: 'Module', signature: 'client.chat.completions: Completions', snippet: 'completions', doc: '对话补全接口门面。' }
  ],
  'client.chat.completions': [
    { name: 'create', kind: 'Method', signature: 'client.chat.completions.create(model: str, messages: list, temperature: float = 0.7, stream: bool = False)', snippet: 'create(\n    model="${1:deepseek-chat}",\n    messages=[{"role": "user", "content": "${2:你好}"}],\n    temperature=${3:0.3}\n)', doc: '发起大模型推理对话生成。' }
  ],
  'client.embeddings': [
    { name: 'create', kind: 'Method', signature: 'client.embeddings.create(input: Union[str, List[str]], model: str)', snippet: 'create(input=["${1:text}"], model="${2:bge-m3}")', doc: '批量生成文本向量 Embedding。' }
  ],

  // 1.11 ChromaDB 向量集合 (collection)
  'collection': [
    { name: 'add', kind: 'Method', signature: 'collection.add(documents: List[str], metadatas: List[dict] = None, ids: List[str] = None)', snippet: 'add(documents=[${1:"text"}], metadatas=[{"source": "${2:doc.pdf}"}], ids=["${3:id_1}"])', doc: '向向量库中批量添加知识文本块与元数据。' },
    { name: 'query', kind: 'Method', signature: 'collection.query(query_texts: List[str], n_results: int = 3, where: dict = None)', snippet: 'query(query_texts=["${1:query}"], n_results=${2:3})', doc: '余弦语义相似度搜索，召回前 N 条最贴近切片。' },
    { name: 'get', kind: 'Method', signature: 'collection.get(ids: List[str] = None, where: dict = None)', snippet: 'get(ids=["${1:id_1}"])', doc: '根据 ID 或元数据过滤条件精确检索文档。' },
    { name: 'delete', kind: 'Method', signature: 'collection.delete(ids: List[str] = None, where: dict = None)', snippet: 'delete(ids=["${1:id_1}"])', doc: '从向量集合中删除指定切片。' },
    { name: 'count', kind: 'Method', signature: 'collection.count() -> int', snippet: 'count()', doc: '获取当前集合中的向量切片总条数。' },
    { name: 'peek', kind: 'Method', signature: 'collection.peek(limit: int = 10) -> dict', snippet: 'peek(limit=${1:5})', doc: '预览集合前几条样本数据。' }
  ]
};

// ==========================================
// 2. 核心代码模板库 (供速查抽屉与全局提示)
// ==========================================
export const PYTHON_METHODS_CATALOG = [
  {
    category: 'LangGraph 智能体状态图',
    categoryIcon: 'Workflow',
    name: 'StateGraph',
    signature: 'StateGraph(state_schema: Type[TypedDict]) -> StateGraph',
    snippet: 'workflow = StateGraph(${1:AgentState})\n${0}',
    doc: '初始化 LangGraph 状态图。传入作为全局上下文契约的 TypedDict 状态定义类。',
    kind: 'Class',
    example: `from typing import TypedDict, Annotated, List
import operator
from langgraph.graph import StateGraph, START, END

class AgentState(TypedDict):
    messages: Annotated[List[dict], operator.add]

workflow = StateGraph(AgentState)`
  },
  {
    category: 'LangGraph 智能体状态图',
    categoryIcon: 'Workflow',
    name: 'add_node',
    signature: 'workflow.add_node(node_name: str, action_func: Callable) -> None',
    snippet: 'workflow.add_node("${1:agent_node}", ${2:agent_action_function})\n${0}',
    doc: '向状态图中添加一个处理节点。action_func 接收当前 state 并返回部分更新的字典。',
    kind: 'Method',
    example: `def call_model(state: AgentState):
    return {"messages": [{"role": "assistant", "content": "Done"}]}`
  },
  {
    category: 'LangGraph 智能体状态图',
    categoryIcon: 'Workflow',
    name: 'add_edge',
    signature: 'workflow.add_edge(start_node: str, end_node: str) -> None',
    snippet: 'workflow.add_edge("${1:node_a}", "${2:node_b}")\n${0}',
    doc: '添加确定性单向连边。从起始节点无条件流转到目标节点。',
    kind: 'Method',
    example: 'workflow.add_edge(START, "agent_node")\nworkflow.add_edge("agent_node", END)'
  },
  {
    category: 'LangGraph 智能体状态图',
    categoryIcon: 'Workflow',
    name: 'add_conditional_edges',
    signature: 'workflow.add_conditional_edges(source: str, path_func: Callable, path_map: dict) -> None',
    snippet: 'workflow.add_conditional_edges(\n    "${1:source_node}",\n    ${2:route_decision_func},\n    {\n        "${3:action}": "${4:target_node}",\n        "finish": END\n    }\n)\n${0}',
    doc: '添加条件路由分支连边。path_func 判定下一个路由分支，path_map 映射分支名称到具体节点。',
    kind: 'Method',
    example: `def should_continue(state: AgentState) -> str:
    return "tools" if "tool_calls" in state["messages"][-1] else "finish"`
  },
  {
    category: 'LangGraph 智能体状态图',
    categoryIcon: 'Workflow',
    name: 'compile',
    signature: 'workflow.compile(checkpointer=None) -> CompiledStateGraph',
    snippet: 'app = workflow.compile(checkpointer=${1:MemorySaver()})\n${0}',
    doc: '将构建好的图网络编译为可执行应用实例。支持挂载持久化检查点（Checkpointer）。',
    kind: 'Method',
    example: 'from langgraph.checkpoint.memory import MemorySaver\napp = workflow.compile(checkpointer=MemorySaver())'
  },
  {
    category: '大模型调用 (OpenAI / DeepSeek)',
    categoryIcon: 'Sparkles',
    name: 'OpenAI',
    signature: 'OpenAI(api_key: Optional[str] = None, base_url: Optional[str] = None) -> OpenAI',
    snippet: 'client = OpenAI(\n    api_key=os.getenv("${1:OPENAI_API_KEY}", "${2:dummy-key}"),\n    base_url=os.getenv("${3:OPENAI_BASE_URL}", "https://api.deepseek.com")\n)\n${0}',
    doc: '初始化 OpenAI 规范模型客户端（原生兼容 DeepSeek、vLLM、Ollama）。',
    kind: 'Class',
    example: 'from openai import OpenAI\nclient = OpenAI()'
  },
  {
    category: '大模型调用 (OpenAI / DeepSeek)',
    categoryIcon: 'Sparkles',
    name: 'chat.completions.create',
    signature: 'client.chat.completions.create(model: str, messages: list, temperature: float = 0.7) -> ChatCompletion',
    snippet: 'response = client.chat.completions.create(\n    model="${1:deepseek-chat}",\n    messages=[\n        {"role": "system", "content": "${2:你是一位企业架构专家。}"},\n        {"role": "user", "content": "${3:需求分析}"}\n    ],\n    temperature=${4:0.3}\n)\nanswer = response.choices[0].message.content\n${0}',
    doc: '发起多轮对话文本补全请求。返回生成的结构化消息内容或流式响应。',
    kind: 'Method',
    example: 'res = client.chat.completions.create(model="qwen2.5-7b", messages=[{"role": "user", "content": "hi"}])'
  },
  {
    category: '向量检索与 Hybrid RAG',
    categoryIcon: 'Database',
    name: 'PersistentClient',
    signature: 'chromadb.PersistentClient(path: str = "./chroma_db") -> Client',
    snippet: 'import chromadb\nchroma_client = chromadb.PersistentClient(path="${1:./chroma_db}")\n${0}',
    doc: '初始化本地磁盘持久化向量数据库客户端。关闭进程后数据不丢失。',
    kind: 'Class',
    example: 'import chromadb\nclient = chromadb.PersistentClient(path="./chroma_db")'
  },
  {
    category: '企业安全与运维治理',
    categoryIcon: 'ShieldCheck',
    name: 'verify_sandbox_safety',
    signature: 'verify_sandbox_safety(code: str) -> Tuple[bool, Optional[str]]',
    snippet: 'is_safe, error_msg = verify_sandbox_safety(${1:code_content})\nif not is_safe:\n    raise PermissionError(f"安全检测拦截: {error_msg}")\n${0}',
    doc: '执行前 AST 语法树深度检测，严禁恶意导入 `os.system`、`subprocess`、`eval` 等越权操作。',
    kind: 'Function',
    example: 'safe, reason = verify_sandbox_safety(code)'
  },
  {
    category: 'Python 异步与工程常用',
    categoryIcon: 'Terminal',
    name: 'os.getenv',
    signature: 'os.getenv(key: str, default: Optional[str] = None) -> Optional[str]',
    snippet: 'os.getenv("${1:MODEL_NAME}", "${2:deepseek-chat}")\n${0}',
    doc: '安全读取系统环境变量，若未配置则回退到缺省默认值。',
    kind: 'Function',
    example: 'key = os.getenv("OPENAI_API_KEY", "default-val")'
  }
];

// ==========================================
// 3. 动态智能补全提供器核心逻辑
// ==========================================
export function getPythonCompletionItems(monaco, range, lineUntilPosition = '') {
  if (!monaco) return [];

  // 1. 检查是否存在点号属性访问：例如 "os." 或 "os.path." 或 "json." 或 "client."
  // 匹配类似：abc. 或 abc.def. 后接可选的已输入字符
  const dotMatch = lineUntilPosition.match(/([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*)\.([a-zA-Z0-9_]*)$/);

  if (dotMatch) {
    const fullPrefix = dotMatch[1].toLowerCase(); // 例如 "os", "os.path", "client.chat"
    const memberList = MODULE_MEMBERS_MAP[fullPrefix];

    if (memberList && memberList.length > 0) {
      return memberList.map((member, idx) => {
        let kind = monaco.languages.CompletionItemKind.Method;
        if (member.kind === 'Variable') kind = monaco.languages.CompletionItemKind.Variable;
        else if (member.kind === 'Class') kind = monaco.languages.CompletionItemKind.Class;
        else if (member.kind === 'Module') kind = monaco.languages.CompletionItemKind.Module;
        else if (member.kind === 'Field') kind = monaco.languages.CompletionItemKind.Field;

        return {
          label: member.name,
          kind: kind,
          detail: `(${member.kind.toLowerCase()}) ${member.signature}`,
          documentation: {
            value: `### \`${fullPrefix}.${member.name}\`\n**定义**: \`${member.signature}\`\n\n${member.doc}`
          },
          insertText: member.snippet || member.name,
          insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
          range: range,
          sortText: String(idx).padStart(4, '0') // 保持精选顺序排列
        };
      });
    }
  }

  // 2. 非点号场景：返回顶层推荐模块、类名与全局方法模板
  const topLevelSuggestions = [];

  // 2.1 常见模块名称推荐（支持用户敲入 os, json, sys 时秒速补全）
  const topModules = [
    { name: 'os', detail: '标准库: 操作系统接口 (文件系统、环境变量、路径)', kind: monaco.languages.CompletionItemKind.Module, snippet: 'os' },
    { name: 'json', detail: '标准库: JSON 序列化与反序列化工具', kind: monaco.languages.CompletionItemKind.Module, snippet: 'json' },
    { name: 'sys', detail: '标准库: Python 运行时系统与环境', kind: monaco.languages.CompletionItemKind.Module, snippet: 'sys' },
    { name: 'time', detail: '标准库: 时间与性能计数器', kind: monaco.languages.CompletionItemKind.Module, snippet: 'time' },
    { name: 'asyncio', detail: '标准库: 异步并发协程框架', kind: monaco.languages.CompletionItemKind.Module, snippet: 'asyncio' },
    { name: 're', detail: '标准库: 正则表达式匹配', kind: monaco.languages.CompletionItemKind.Module, snippet: 're' },
    { name: 'chromadb', detail: 'AI 向量数据库 SDK', kind: monaco.languages.CompletionItemKind.Module, snippet: 'chromadb' }
  ];

  topModules.forEach((mod, idx) => {
    topLevelSuggestions.push({
      label: mod.name,
      kind: mod.kind,
      detail: mod.detail,
      documentation: { value: `**Python 模块: \`${mod.name}\`**\n输入 \`${mod.name}.\` 可进一步自动列出其所有下属方法和变量。` },
      insertText: mod.snippet,
      range: range,
      sortText: `0_${String(idx).padStart(2, '0')}_${mod.name}`
    });
  });

  // 2.2 核心常用代码模版库
  PYTHON_METHODS_CATALOG.forEach((item, idx) => {
    let kind = monaco.languages.CompletionItemKind.Method;
    if (item.kind === 'Class') kind = monaco.languages.CompletionItemKind.Class;
    else if (item.kind === 'Function') kind = monaco.languages.CompletionItemKind.Function;
    else if (item.kind === 'Snippet') kind = monaco.languages.CompletionItemKind.Snippet;

    topLevelSuggestions.push({
      label: item.name,
      kind: kind,
      detail: `[${item.category}] ${item.signature}`,
      documentation: {
        value: `### \`${item.name}\`\n**签名**: \`${item.signature}\`\n\n${item.doc}\n\n**实操示例**:\n\`\`\`python\n${item.example}\n\`\`\``
      },
      insertText: item.snippet,
      insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
      range: range,
      sortText: `1_${String(idx).padStart(2, '0')}_${item.name}`
    });
  });

  return topLevelSuggestions;
}

// ==========================================
// 4. 鼠标悬停文档提示 (Hover Provider)
// ==========================================
export function getPythonHoverInfo(monaco, word, lineContent = '') {
  if (!word) return null;

  // 1. 尝试匹配点号前缀，例如 "os.getenv"
  if (lineContent) {
    for (const [prefix, members] of Object.entries(MODULE_MEMBERS_MAP)) {
      if (lineContent.includes(`${prefix}.${word}`)) {
        const found = members.find(m => m.name.toLowerCase() === word.toLowerCase());
        if (found) {
          return {
            contents: [
              { value: `**\`${prefix}.${found.name}\`** (${found.kind.toLowerCase()})` },
              { value: `\`\`\`python\n${found.signature}\n\`\`\`` },
              { value: `${found.doc}` }
            ]
          };
        }
      }
    }
  }

  // 2. 尝试从各个模块中直接查找同名成员
  for (const [prefix, members] of Object.entries(MODULE_MEMBERS_MAP)) {
    const found = members.find(m => m.name.toLowerCase() === word.toLowerCase());
    if (found) {
      return {
        contents: [
          { value: `**\`${prefix}.${found.name}\`** (${found.kind.toLowerCase()})` },
          { value: `\`\`\`python\n${found.signature}\n\`\`\`` },
          { value: `${found.doc}` }
        ]
      };
    }
  }

  // 3. 顶层模板库匹配
  const match = PYTHON_METHODS_CATALOG.find((item) => 
    item.name.toLowerCase() === word.toLowerCase()
  );
  if (match) {
    return {
      contents: [
        { value: `**[${match.category}] \`${match.name}\`**` },
        { value: `\`\`\`python\n${match.signature}\n\`\`\`` },
        { value: `${match.doc}\n\n**示例**:\n\`\`\`python\n${match.example}\n\`\`\`` }
      ]
    };
  }

  return null;
}
