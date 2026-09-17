import warnings
warnings.filterwarnings("ignore") # 忽略底层的实验性警告

from langchain_text_splitters import TokenTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_core.embeddings import FakeEmbeddings

# 我们准备一段包含“明显主题突变”的文本
# 第一段聊天气，第二段聊量子力学，第三段聊水果。
text_corpus = """
Today is a beautiful day. The sun is shining brightly in the clear blue sky. It is the perfect weather for a family picnic in the park. We should bring some sandwiches and enjoy the breeze.
However, quantum mechanics is a fundamental theory in physics. It provides a description of the physical properties of nature at the scale of atoms and subatomic particles. It is the foundation of all quantum physics, including quantum chemistry and quantum information science.
By the way, apples are usually red or green. Bananas are yellow and rich in potassium. Eating fresh fruit every day is very good for your health and immune system.
"""

def demo_sliding_window():
    print("=== 方案三：Token 滑动窗口切分 (Sliding Window Token Splitter) ===")
    print("【技术原理】：抛弃物理字符，直接调用大模型底层分词器 (如 tiktoken) 计算 Token。")
    print("【策略】：设置固定大小的滑动窗口（如 size=30），每次向右滑动一定的步长（如重叠 overlap=15）。")
    print("【优势】：绝对精确地控制输入给大模型的 Token 数量，永远不会爆上下文超限报错！\n")
    
    # 使用 OpenAI 官方的 tiktoken 分词器
    # chunk_size=30: 每个块最多30个Token
    # chunk_overlap=15: 下一块从上一块的一半开始，形成完美嵌套的滑动窗口
    splitter = TokenTextSplitter(chunk_size=30, chunk_overlap=15)
    chunks = splitter.split_text(text_corpus)
    
    for i, chunk in enumerate(chunks):
        safe_print = chunk.replace('\n', ' ')
        print(f"📦 窗口 [{i+1}] (Tokens: ~30): {safe_print}")

def demo_semantic_chunking():
    print("\n" + "="*60)
    print("=== 方案四：前沿的语义切分 (Semantic Chunking) ===")
    print("【技术原理】：不再死板地按字数或符号切！它先计算每一句话的“向量语义 (Embedding)”。")
    print("如果相邻两句话的“余弦相似度”突然发生断崖式下跌，说明作者在此处【切换了话题】，系统就会果断在这里切一刀！")
    print("【演示说明】：这里为了不消耗你的真实 API 额度，使用了 FakeEmbeddings（生成随机向量），所以在测试中切分点可能略显随机。但在生产中接上 OpenAIEmbeddings，它能完美将天气、量子物理、水果分成三块独立碎片！\n")
    
    # 生产环境中，请将 FakeEmbeddings 替换为真实的向量模型
    # 例如：embeddings = OpenAIEmbeddings()
    embeddings = FakeEmbeddings(size=128)
    
    # breakpoint_threshold_type="percentile" 表示取相似度下跌幅度最大的百分位点作为切割刀
    semantic_chunker = SemanticChunker(embeddings, breakpoint_threshold_type="percentile")
    
    # Langchain 实验库会发出一些警告，我们在头部已经屏蔽
    chunks = semantic_chunker.split_text(text_corpus)
    
    for i, chunk in enumerate(chunks):
        safe_print = chunk.replace('\n', ' ')
        print(f"🧠 语义碎块 [{i+1}] (独立主题): {safe_print}")

if __name__ == "__main__":
    print("🚀 启动高阶 RAG 文本切块策略演示...\n")
    demo_sliding_window()
    demo_semantic_chunking()
