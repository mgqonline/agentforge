from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter

# 这是模拟我们在上一步从 Complex_Labor_Contract.docx 和 Excel 中提取并转化为 Markdown 的超长富文本
complex_markdown_text = """
# Enterprise Master Service Agreement 2026
This document is highly confidential and contains proprietary business logic.

## 1. Background & Scope
This agreement establishes the terms for the enterprise AI transformation project. 
The project MUST be delivered by Q4. Failure to do so will result in a 10% penalty.
Our primary goal is to transition from legacy systems to a unified LLM architecture.

## 2. Deliverables & Pricing
| Phase | Deliverable | Cost (USD) |
|---|---|---|
| Phase 1 | RAG Knowledge Base Setup | $50,000 |
| Phase 2 | Agentic Workflow Orchestration | $120,000 |
| Phase 3 | Multimodal Model Deployment | $80,000 |

## 3. Legal Clauses
- Any dispute shall be resolved via arbitration in San Francisco, CA.
- The Non-Disclosure Agreement (NDA) remains valid for exactly 5 years after termination.
"""

def demo_recursive_splitter():
    print("=== 方案一：递归字符切分 (Recursive Character Splitter) ===")
    print("【技术原理】：优先按大段落(\\n\\n)切，如果还超长，再按单行(\\n)切，最后按空格切。这能最大程度保证一句话不被硬生生劈开。")
    
    # 在生产中，chunk_size 通常是 500-1000。这里为了演示效果故意设得很小 (150)
    # chunk_overlap (重叠区) 极其重要，防止 "San Francisco" 被切成上一块的 "San" 和下一块的 "Francisco"
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=150,
        chunk_overlap=30,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_text(complex_markdown_text)
    
    for i, chunk in enumerate(chunks):
        # 把换行符打印出来方便观察
        safe_print = chunk.replace('\n', '\\n')
        print(f"📦 碎片 [{i+1}] (长度: {len(chunk)}):\n   {safe_print}\n")

def demo_markdown_splitter():
    print("=== 方案二：Markdown 结构感知切分 (Markdown Header Splitter) ===")
    print("【技术原理】：不是无脑按字数切，而是根据 Markdown 标题 (##) 将文档按逻辑章节大卸八块。")
    print("【生产价值】：这是处理表格和层级文档的神器！把章节名塞进 Metadata 里，大模型就能知道这句话属于哪个章节！\n")
    
    # 告诉切分器：遇到一个 '#' 就把下面的内容归为 'Header 1'，遇到 '##' 就归为 'Header 2'
    headers_to_split_on = [
        ("#", "文档大标题"),
        ("##", "章节标题"),
    ]
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    chunks = splitter.split_text(complex_markdown_text)
    
    for i, chunk in enumerate(chunks):
        safe_print = chunk.page_content.replace('\n', '\\n')
        # 看看切分器有多聪明，它把标题全部提炼到了 metadata 里！
        print(f"📦 碎片 [{i+1}]")
        print(f"   🏷️ 注入的元数据 (Metadata): {chunk.metadata}")
        print(f"   📄 保留的正文 (Content): {safe_print}\n")

if __name__ == "__main__":
    print("🚀 启动 RAG 文本切块 (Chunking) 策略演示...\n")
    demo_recursive_splitter()
    print("-" * 60 + "\n")
    demo_markdown_splitter()
