import os
import sys
import io
import csv

sys.path.insert(0, os.path.dirname(__file__))
from auth_governance import get_billing_summary, generate_billing_csv_content
from model_router import model_failover_router

def test_billing_summary_calculation():
    """测试 FinOps 账单财务汇总与工时估算计算"""
    summary = get_billing_summary()
    assert "total_tokens_consumed" in summary
    assert "total_cost_cny" in summary
    assert "total_hours_saved" in summary
    assert "tenants" in summary
    assert len(summary["tenants"]) > 0

    # 验证租户字段
    first_tenant = summary["tenants"][0]
    assert "tenant_id" in first_tenant
    assert "cost_cny" in first_tenant
    assert "hours_saved" in first_tenant
    assert "burn_rate_pct" in first_tenant

def test_billing_csv_generation():
    """测试 FinOps CSV 财务账单生成（带 UTF-8 BOM，字段齐全）"""
    csv_text = generate_billing_csv_content()
    # 验证 UTF-8 BOM 存在以防止 Excel 乱码
    assert csv_text.startswith("\ufeff")
    
    # 使用 csv reader 解析
    f = io.StringIO(csv_text[1:]) # 跳过 BOM 校验内容
    reader = csv.reader(f)
    header = next(reader)
    assert "交易流水号" in header[0]
    assert "所属租户/部门" in header[1]
    assert "操作账号" in header[2]
    assert "功能模块" in header[3]
    assert "详情备注" in header[4]
    assert "消耗Tokens" in header[5]
    assert "折算金额(¥)" in header[6]

def test_model_status_endpoint():
    """测试大模型路由集群健康度上报"""
    status = model_failover_router.get_cluster_status()
    assert "cluster_health" in status
    assert "nodes" in status
    assert len(status["nodes"]) >= 1

if __name__ == "__main__":
    print("🚀 正在运行 P0 特性核心自动化测试...")
    test_billing_summary_calculation()
    print("✅ [1/3] test_billing_summary_calculation 测试通过")
    test_billing_csv_generation()
    print("✅ [2/3] test_billing_csv_generation 测试通过")
    test_model_status_endpoint()
    print("✅ [3/3] test_model_status_endpoint 测试通过")
    print("🎉 P0 核心后端测试 100% 全部通过！")

