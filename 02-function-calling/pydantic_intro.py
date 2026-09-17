from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional

# 1. 定义一个严谨的数据模型
class UserProfile(BaseModel):
    # 基础类型约束
    name: str = Field(..., description="用户的姓名")
    
    # 范围约束：年龄必须在 0 到 120 之间
    age: int = Field(..., ge=0, le=120, description="用户的年龄")
    
    # 正则约束：邮箱格式
    email: str = Field(..., pattern=r"^\S+@\S+\.\S+$", description="用户的电子邮件")
    
    # 列表与可选字段
    tags: List[str] = Field(default_factory=list, description="用户的特征标签")
    vip_level: Optional[int] = Field(default=None, description="VIP等级，可为空")

print("=== Pydantic 核心功能演示 ===\n")

# --- 场景 1: 完美的数据解析与类型转换 ---
print("👉 场景 1: 正常数据输入 (自动类型转换)")
raw_json = '{"name": "张三", "age": "25", "email": "zhangsan@example.com"}' 
# 注意：上面的 age 传入的是字符串 "25"
user = UserProfile.model_validate_json(raw_json)
print(f"解析成功！类型已经被纠正：姓名={user.name}, 年龄={user.age}({type(user.age)}), 邮箱={user.email}")
print("-" * 50)

# --- 场景 2: 拦截不合法的数据 ---
print("\n👉 场景 2: 脏数据输入拦截")
dirty_json = '{"name": "李四", "age": 150, "email": "lisi_at_example_com"}'
try:
    bad_user = UserProfile.model_validate_json(dirty_json)
except ValidationError as e:
    print("❌ 拦截成功！发现了以下数据错误：")
    for error in e.errors():
        field_name = error['loc'][0]
        error_msg = error['msg']
        print(f"   - 字段 [{field_name}]: {error_msg}")
