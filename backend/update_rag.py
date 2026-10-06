"""
⚠️ 已停用：本脚本会正则匹配并覆写 rag_engine.py 的源码。
================================================================================
历史背景
--------------------------------------------------------------------------------
`update_rag.py` 与 `update_rag_incremental.py` 并不是数据迁移脚本，而是「用正则
替换 rag_engine.py 方法体、再把结果写回源文件」的代码生成脚本。例如：

    content = re.sub(r'    def build_or_load\\(self\\):.*?    def retrieve\\(...',
                     new_build_or_load + ..., content, flags=re.DOTALL)
    with open("rag_engine.py", "w") as f:
        f.write(content)

这种做法有两个严重问题：
  1. 任何人误跑一次，rag_engine.py 就会被静默重写，且没有 diff 审查、没有回滚；
  2. 它依赖正则匹配方法签名。当前 retrieve 的默认参数已从 `k=10` 改为 `k=6`，
     正则早已匹配不上，脚本要么静默无效，要么产生难以察觉的破坏。

现在这些改动已经正式落到 rag_engine.py 源码里（增量索引、document_hashes 指纹表、
显式降级状态、语料白名单过滤），不再需要这类脚本。

如需修改 RAG 行为，请直接编辑 backend/rag_engine.py 并正常提交。
本文件仅为保留历史痕迹而存在，运行时会直接退出，不做任何写操作。
================================================================================
"""

import sys

MESSAGE = """
================================================================================
⛔ 该脚本已被停用，不会修改任何文件。

原因：它会正则匹配并覆写 backend/rag_engine.py 的源码，属于危险操作，
      且当前正则已与源码结构不匹配，运行结果不可预期。

需要调整 RAG 行为时，请：
  1. 直接编辑 backend/rag_engine.py；
  2. 运行 python3 -m py_compile backend/rag_engine.py 确认语法；
  3. 运行 python3 tests/test_e2e_smoke.py 确认未破坏既有功能。

若只是想重建知识库索引，请调用接口：
  POST /api/v1/knowledge/reindex
================================================================================
"""

if __name__ == "__main__":
    print(MESSAGE)
    sys.exit(1)