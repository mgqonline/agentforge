import torch

try:
    import triton
    import triton.language as tl
except ImportError:
    triton = None
    tl = None
    print("❌ 未安装 triton 库。请在包含 Nvidia GPU 的 Linux 环境中执行 `pip install triton`。")
    print("⚠️ 注意：Triton 算子开发目前主要支持 Linux 环境下的 Nvidia/AMD GPU，在 Mac(Apple Silicon/Intel) 下可能无法原生运行。")
    
# Mock decorators so script doesn't crash on import
def dummy_jit(fn):
    return fn

if triton is not None:
    jit_decorator = triton.jit
    constexpr = tl.constexpr
else:
    jit_decorator = dummy_jit
    constexpr = type('dummy_constexpr', (), {})

# ==============================================================
# 17_triton_attention_operator.py
# ==============================================================
# GPU 底层算子开发实战：使用 Triton 编写基础版本的 Flash Attention
# 
# 为什么要用 Triton 写算子？
# 1. 传统 PyTorch 的 Attention 会在 GPU 的 HBM (主显存) 和 SRAM (高速缓存) 之间来回搬运 Q, K, V，非常慢。
# 2. Triton 允许我们用 Python 语法写 GPU 内核级代码（类似 CUDA）。
# 3. 我们可以控制 block 大小，将 Q, K, V 切块放入高速 SRAM 中算完再写回，这就是 FlashAttention 的核心思想。
# ==============================================================

@jit_decorator
def _fwd_kernel(
    Q, K, V, sm_scale,
    Out,
    stride_qz, stride_qh, stride_qm, stride_qk,
    stride_kz, stride_kh, stride_kn, stride_kk,
    stride_vz, stride_vh, stride_vn, stride_vk,
    stride_oz, stride_oh, stride_om, stride_on,
    Z, H, N_CTX,
    BLOCK_M: constexpr, BLOCK_DMODEL: constexpr, BLOCK_N: constexpr,
):
    """
    Triton Kernel 核心逻辑 (前向传播)
    我们为每一个 (batch, head, 序列的一个数据块) 分配一个 GPU 线程块 (Block)
    """
    # 1. 获取当前 Block 的坐标信息
    start_m = tl.program_id(0) # 对应的 Q 的行索引块
    off_hz = tl.program_id(1)  # 对应的 batch_size * num_heads 偏移

    # 初始化指针
    q_offset = off_hz * stride_qh
    k_offset = off_hz * stride_kh
    v_offset = off_hz * stride_vh
    o_offset = off_hz * stride_oh

    # 构建当前 block 中 Q, K, V 的内存偏移指针数组
    offs_m = start_m * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_n = tl.arange(0, BLOCK_N)
    offs_d = tl.arange(0, BLOCK_DMODEL)
    
    q_ptrs = Q + q_offset + offs_m[:, None] * stride_qm + offs_d[None, :] * stride_qk
    k_ptrs = K + k_offset + offs_n[:, None] * stride_kn + offs_d[None, :] * stride_kk
    v_ptrs = V + v_offset + offs_n[:, None] * stride_vn + offs_d[None, :] * stride_vk
    o_ptrs = Out + o_offset + offs_m[:, None] * stride_om + offs_d[None, :] * stride_on

    # 2. 从主显存 (HBM) 加载 Q 的这一个 Block 到 高速缓存 (SRAM)
    # 假定序列长度可以被 BLOCK 整除，这里不做掩码边界判断以保持代码简洁
    q = tl.load(q_ptrs)

    # 初始化用于累加的 accumulator
    m_i = tl.zeros([BLOCK_M], dtype=tl.float32) - float("inf")
    l_i = tl.zeros([BLOCK_M], dtype=tl.float32)
    acc = tl.zeros([BLOCK_M, BLOCK_DMODEL], dtype=tl.float32)

    # 3. 循环遍历 K 和 V 的各个 Block
    for start_n in range(0, N_CTX, BLOCK_N):
        start_n = tl.multiple_of(start_n, BLOCK_N)
        
        # 将 K, V 的块也拉入 SRAM
        k = tl.load(k_ptrs)
        v = tl.load(v_ptrs)

        # 核心：Q(SRAM) * K(SRAM) 
        qk = tl.zeros([BLOCK_M, BLOCK_N], dtype=tl.float32)
        qk += tl.dot(q, tl.trans(k))
        qk *= sm_scale

        # Online Softmax (FlashAttention 核心优化：边算边归一化，避免中间矩阵写入 HBM)
        m_ij = tl.maximum(m_i, tl.max(qk, 1))
        qk = qk - m_ij[:, None]
        p = tl.math.exp(qk)
        l_ij = tl.sum(p, 1)

        # 缩放先前的累加器
        alpha = tl.math.exp(m_i - m_ij)
        acc = acc * alpha[:, None]
        
        # 核心：计算百分比权重并乘以 V(SRAM)
        acc += tl.dot(p.to(tl.float16), v)

        # 更新 running max (m_i) 和 分母 (l_i)
        m_i = m_ij
        l_i = l_i * alpha + l_ij

        # 将 K 和 V 的指针推到下一个 Block
        k_ptrs += BLOCK_N * stride_kn
        v_ptrs += BLOCK_N * stride_vn

    # 收尾处理 softmax
    acc = acc / l_i[:, None]
    
    # 4. 把计算结果写回 HBM
    tl.store(o_ptrs, acc.to(tl.float16))

def triton_attention(q, k, v, sm_scale):
    """
    Python 包裹函数，用于拉起 Triton Kernel
    """
    # 确保输入在 GPU 上并且是连续的
    q = q.contiguous()
    k = k.contiguous()
    v = v.contiguous()
    
    # 形状: [batch, num_heads, seq_len, d_head]
    Z, H, N_CTX, D_HEAD = q.shape
    
    # 创建一块空显存用于存放输出
    out = torch.empty_like(q)

    # 启动网格的维度：我们需要多少个 GPU Block?
    # grid[0]: seq_len 切分的块数
    # grid[1]: batch * num_heads 的数量
    BLOCK_M = 64
    BLOCK_N = 64
    grid = (triton.cdiv(N_CTX, BLOCK_M), Z * H, 1)

    _fwd_kernel[grid](
        q, k, v, sm_scale,
        out,
        q.stride(0), q.stride(1), q.stride(2), q.stride(3),
        k.stride(0), k.stride(1), k.stride(2), k.stride(3),
        v.stride(0), v.stride(1), v.stride(2), v.stride(3),
        out.stride(0), out.stride(1), out.stride(2), out.stride(3),
        Z, H, N_CTX,
        BLOCK_M=BLOCK_M, BLOCK_N=BLOCK_N, BLOCK_DMODEL=D_HEAD,
        num_warps=4,
        num_stages=2,
    )
    return out

def main():
    print("=== 第十七课：AI 底层工程 —— GPU 算子级 Triton Attention 实现 ===")
    
    # 由于 Triton 强依赖 CUDA，在没有 GPU 的机器上做个兜底演示
    if not torch.cuda.is_available():
        print("⚠️ 检测到当前环境未包含 CUDA GPU。")
        print("⚠️ Triton 内核编译需要在带有 Nvidia GPU 的 Linux 环境下才能真正执行。")
        print("⚠️ 我们已经完成了底层算子代码的构建。你可以将本脚本放到 Linux/GPU 服务器上运行对比速度。")
        return

    # 初始化测试张量 (放进显存)
    batch_size = 2
    num_heads = 4
    seq_len = 1024
    d_head = 64
    
    print(f"\n[测试规模] Batch: {batch_size}, Heads: {num_heads}, SeqLen: {seq_len}, Dim: {d_head}")
    
    q = torch.randn(batch_size, num_heads, seq_len, d_head, device='cuda', dtype=torch.float16)
    k = torch.randn(batch_size, num_heads, seq_len, d_head, device='cuda', dtype=torch.float16)
    v = torch.randn(batch_size, num_heads, seq_len, d_head, device='cuda', dtype=torch.float16)
    sm_scale = 1.0 / (d_head ** 0.5)

    print("\n🚀 正在通过 Triton 编译并执行自定义 Attention GPU 内核...")
    
    # 预热
    triton_output = triton_attention(q, k, v, sm_scale)
    
    # 标准 PyTorch 实现用于对比准确性
    import torch.nn.functional as F
    torch_output = F.scaled_dot_product_attention(q, k, v, scale=sm_scale)
    
    # 验证正确性
    diff = torch.max(torch.abs(triton_output - torch_output))
    print(f"✅ 计算完成！与官方 PyTorch 的最大误差为: {diff.item():.6f}")
    if diff < 1e-2:
        print("🎉 我们的手写 GPU Triton 算子逻辑完全正确！")
    
if __name__ == "__main__":
    main()
