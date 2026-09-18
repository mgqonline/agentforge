# 25-reasoning-rl · 大模型后训练强化学习与长思维链推理 (GRPO & Reasoning RL)

## 🎯 核心目标与应用场景

随着 DeepSeek-R1、OpenAI o1 的爆发，大语言模型从传统的“监督微调 (SFT)”全面演进至**基于推理阶段思考（Long-CoT）与规则强化学习（RL）**的全新范式。
本模块的核心目标是掌握 DeepSeek 提出的 **Group Relative Policy Optimization (GRPO)** 算法机制，摆脱对巨大 Critic 价值网络的依赖，通过规则驱动的纯强化学习激励模型“自主反思、自我纠错与探索推理”。

**应用场景**：
1. **复杂数学与逻辑推导**：通过规则验证器提供 0/1 判定，激励长思维链自主展开；
2. **代码生成与单元测试自闭环**：结合沙箱单元测试通过率作为准确性奖励，自迭代修复 Bug；
3. **结构化指令遵循**：强制约束模型输出 `<think>...</think>` 思考过程并格式化输出 JSON/XML。

---

## 🧠 技术原理与架构流程图

### 1. 为什么弃用 PPO 转向 GRPO？
传统 PPO（Proximal Policy Optimization）需要维护两个同等规模的模型：**Actor 策略模型**与 **Critic 价值模型**。Critic 网络不仅占据近 50% 显存，且在大模型复杂推理轨迹上的价值估计往往极不准确。

GRPO（组相对策略优化）的精髓在于：**同题多路采样 + 组内相对优势归一化**。
针对同一个输入 Prompt $q$，生成一组候选响应轨迹 $\{o_1, o_2, ..., o_G\}$，计算各个轨迹的综合规则奖励 $R_i$，并直接在组内进行标准化计算优势：

$$A_i = \frac{R_i - \text{mean}(R)}{\text{std}(R) + \epsilon}$$

优势 $A_i > 0$ 的轨迹梯度被正向放大激励；$A_i < 0$ 的劣质轨迹被抑制。

### 2. 复合规则奖励机制
- **准确性奖励 (Accuracy Reward)**：数值匹配或单元测试通过给予 1.0，失败给予 0.0；
- **格式规范性奖励 (Format Reward)**：严格包含成对闭合的 `<think>...</think>` XML 标签；
- **长度与复读机惩罚 (Length Penalty)**：对超出预期的重复无意义长思考施加梯度衰减惩罚。

### 3. 系统架构与数据流图

```mermaid
flowchart TD
    Q[用户输入 Prompt: 数学/代码/逻辑题] --> Sampler[Policy 策略模型多路采样 (Group Size G=4)]
    Sampler --> T1["轨迹 1: &lt;think&gt;正确推导&lt;/think&gt; 正确答案"]
    Sampler --> T2["轨迹 2: 无标签但答案正确"]
    Sampler --> T3["轨迹 3: &lt;think&gt;错误推导&lt;/think&gt; 错误答案"]
    Sampler --> T4["轨迹 4: &lt;think&gt;复读机冗余&lt;/think&gt; 正确答案"]

    T1 & T2 & T3 & T4 --> RuleEngine[复合规则奖励引擎 (Rule-based Reward Engine)]
    RuleEngine --> R1["R1 = 1.0 (优)"]
    RuleEngine --> R2["R2 = 0.7 (中)"]
    RuleEngine --> R3["R3 = 0.3 (差)"]
    RuleEngine --> R4["R4 = 0.5 (冗)"]

    R1 & R2 & R3 & R4 --> Norm[组内相对优势计算 Advantage Normalization]
    Norm --> A1["A1 = +1.45 (正向强烈更新)"]
    Norm --> A2["A2 = +0.29 (微弱正向更新)"]
    Norm --> A3["A3 = -1.26 (强烈抑制更新)"]
    Norm --> A4["A4 = -0.48 (抑制冗余长文本)"]

    A1 & A2 & A3 & A4 --> Optimizer[PPO-Clip 目标函数更新策略模型权重]
```

---

## 🛠️ 操作方法与执行命令

**1. 运行 GRPO 规则奖励打分与组内相对优势演示**
```bash
python 25-reasoning-rl/grpo_reasoning_pipeline.py
```

**2. 运行自动化单元测试套件**
```bash
python -m unittest 25-reasoning-rl/test_grpo.py
```

---

## ⚠️ 注意事项与踩坑记录

1. **奖励黑客攻击 (Reward Hacking)**：
   - 现象：若仅给思考长度正向奖励，模型会学会通过无休止地输出“等等，让我再想想…”来骗取奖励，变成“复读机模型”。
   - 对策：必须引入**长度惩罚上限 (Length Penalty)**，并在训练后期动态限制最大思考 Token 阈值。
2. **冷启动与格式崩塌**：
   - 现象：纯强化学习初期，模型可能完全不会输出 `<think>` 标签，导致格式奖励持续为 0。
   - 对策：在进行 GRPO 前，通常需要用少量包含 `<think>...</think>` 的优质 Cold-Start 数据进行数千步轻量 SFT 预热。
3. **除零异常与单一样本**：
   - 当组内所有采样的奖励相同时（$\text{std}(R) = 0$），优势计算会溢出，必须设置安全保护项 $\epsilon = 1e-6$。
