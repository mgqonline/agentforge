"""
DFL (Dynamic Fusion Layer & Decision-Focused Feedback Loop) 单元测试与验证套件
"""
from dfl_engine import dfl_fusion, dfl_feedback
from langchain_core.documents import Document

def test_dynamic_weights_exact_terms():
    # 针对专有名词、API、文件扩展名等密集 Query
    query = "api/agent/ws-ticket 接口 500 error in main.py"
    dense_w, sparse_w, diag = dfl_fusion.calculate_dynamic_weights(query)
    
    print("\n[Exact Query]:", diag)
    # 精确匹配和代码模式较多时，Sparse (BM25) 权重应得到显著提升
    assert sparse_w > 0.45
    assert round(dense_w + sparse_w, 2) == 1.0

def test_dynamic_weights_abstract_reasoning():
    # 针对长篇深度推理和抽象概念 Query
    query = "请详细分析微服务与单体架构在企业高并发场景下的核心权衡与设计模式演进总结"
    dense_w, sparse_w, diag = dfl_fusion.calculate_dynamic_weights(query)
    
    print("\n[Abstract Query]:", diag)
    # 抽象概念和分析词较多时，Dense (向量语义) 权重应占据优势
    assert dense_w > 0.50
    assert round(dense_w + sparse_w, 2) == 1.0

def test_dfl_fuse_and_rerank():
    doc1 = Document(page_content="关于数据库事务的 ACID 原理介绍", metadata={"id": 1})
    doc2 = Document(page_content="MySQL 性能调优与索引优化规范", metadata={"id": 2})
    doc3 = Document(page_content="网络通信 TCP 三次握手与四次挥手", metadata={"id": 3})
    
    dense_results = [(doc1, 0.95), (doc2, 0.85)]
    sparse_results = [(doc2, 12.5), (doc3, 8.0)]
    
    fused = dfl_fusion.fuse_and_rerank(dense_results, sparse_results, dense_weight=0.6, sparse_weight=0.4, top_k=2)
    assert len(fused) == 2
    # doc1 和 doc2 均有高得分，应出现在融合结果中
    assert any(d.metadata["id"] == 2 for d in fused)

def test_decision_focused_intent():
    # 正常业务查询
    eval_query = dfl_feedback.evaluate_intent("帮我查询一下订单 20260901 的发货状态")
    assert eval_query["decision_target"] == "QUERY_ACTION"
    assert eval_query["confidence"] >= 0.65
    assert not eval_query["needs_clarification"]

    # 高危写操作
    eval_danger = dfl_feedback.evaluate_intent("清空数据库所有测试表数据并重置")
    assert eval_danger["is_high_risk"] is True
    assert eval_danger["decision_target"] == "HIGH_RISK_ACTION"

    # 模糊短语 -> 触发主动澄清闭环
    eval_ambiguous = dfl_feedback.evaluate_intent("搞一下")
    assert eval_ambiguous["needs_clarification"] is True
    assert eval_ambiguous["clarification_prompt"] is not None
    assert eval_ambiguous["confidence"] < 0.65

if __name__ == "__main__":
    test_dynamic_weights_exact_terms()
    test_dynamic_weights_abstract_reasoning()
    test_dfl_fuse_and_rerank()
    test_decision_focused_intent()
    print("\n🎉 全部 DFL 语义理解与动态融合测试用例通过！")
