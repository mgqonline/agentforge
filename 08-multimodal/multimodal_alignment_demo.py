import torch
import torch.nn as nn

# ==========================================
# 1. 视觉编码器 (Vision Encoder) - 如 ViT 或 CLIP Vision
# ==========================================
class VisionEncoder(nn.Module):
    def __init__(self, image_size=224, patch_size=16, vision_dim=1024):
        super().__init__()
        # 一张图片被切分成 (224/16) * (224/16) = 14 * 14 = 196 个 Patch
        self.num_patches = (image_size // patch_size) ** 2
        self.vision_dim = vision_dim
        
        # 模拟卷积层把 16x16x3 的像素块提取成高维特征
        self.patch_embed = nn.Conv2d(3, vision_dim, kernel_size=patch_size, stride=patch_size)
        
        # 模拟 Transformer 模块 (略去了具体层叠结构)
        self.transformer = nn.TransformerEncoderLayer(d_model=vision_dim, nhead=8)

    def forward(self, images):
        # 输入: [Batch, Channels, Height, Width] -> [1, 3, 224, 224]
        x = self.patch_embed(images)        # [1, 1024, 14, 14]
        x = x.flatten(2).transpose(1, 2)    # [1, 196, 1024] 
        # 输出: 196 个视觉 Token，每个维度是 1024 (视觉空间的语言)
        return self.transformer(x)

# ==========================================
# 2. 投影层 / 适配器 (Projection Adapter)
# ==========================================
class ProjectionLayer(nn.Module):
    def __init__(self, vision_dim=1024, text_dim=4096):
        super().__init__()
        # 核心翻译官：把视觉维度 (1024) 强行转换到 LLM 的文本维度 (4096)
        # LLaVA 1.5 采用的是两层 MLP，这里使用简单线性层模拟
        self.mlp = nn.Sequential(
            nn.Linear(vision_dim, text_dim),
            nn.GELU(),
            nn.Linear(text_dim, text_dim)
        )

    def forward(self, vision_tokens):
        # 输入: [1, 196, 1024]
        # 输出: [1, 196, 4096] (视觉 Token 变成了可以伪装成文本 Token 的样子)
        return self.mlp(vision_tokens)

# ==========================================
# 3. 语言模型主干 (LLM Main Body) - 如 LLaMA
# ==========================================
class MultimodalLLM(nn.Module):
    def __init__(self, vocab_size=32000, text_dim=4096):
        super().__init__()
        self.text_dim = text_dim
        # 文本 Embedding：将文字词汇库的字映射为 4096 维向量
        self.text_embed = nn.Embedding(vocab_size, text_dim)
        
        # 大模型内部的 Transformer 层 (模拟)
        self.llm_decoder = nn.TransformerDecoderLayer(d_model=text_dim, nhead=32)
        
    def forward(self, text_ids, image_embeddings):
        # 1. 把文本 ID 变成向量: [1, 10] -> [1, 10, 4096]
        text_embeddings = self.text_embed(text_ids)
        
        # 2. 🌟 历史性的时刻：跨模态拼接！
        # 把通过投影层“翻译”好的图像 Token，和真实的文本 Token 拼在一起
        # 此时 LLM 看到的不再是图片，而是一个长达 196 + 10 = 206 长度的高维序列
        # [1, 196, 4096] concat [1, 10, 4096] -> [1, 206, 4096]
        combined_embeddings = torch.cat([image_embeddings, text_embeddings], dim=1)
        
        # 3. 送入大模型大脑进行自回归推理
        output = self.llm_decoder(combined_embeddings, combined_embeddings)
        return output

# ==========================================
# 4. 全流程实战演示 (Pipeline Demo)
# ==========================================
if __name__ == "__main__":
    print("🚀 启动多模态图文对齐演示...")
    
    # 假设输入：一张 224x224 的随机图片，以及一段文字 prompt
    dummy_image = torch.randn(1, 3, 224, 224) 
    # 模拟文本 "[BOS] 请描述这张图片：" 对应的 10 个 token ID
    dummy_text_ids = torch.randint(0, 32000, (1, 10))
    
    # 实例化组件
    vision_encoder = VisionEncoder(vision_dim=1024)
    projection_adapter = ProjectionLayer(vision_dim=1024, text_dim=4096)
    llm = MultimodalLLM(vocab_size=32000, text_dim=4096)
    
    # [Step 1] 眼睛看图：提取视觉 Token
    v_tokens = vision_encoder(dummy_image)
    print(f"👁️ 视觉编码后形状: {v_tokens.shape} -> 代表产生了 196 个 1024 维的纯视觉 Token")
    
    # [Step 2] 翻译对齐：投射到文本空间
    aligned_v_tokens = projection_adapter(v_tokens)
    print(f"🌉 投影翻译后形状: {aligned_v_tokens.shape} -> 代表 196 个视觉 Token 成功转换为 4096 维的 LLM 格式")
    
    # [Step 3] 联合推理：输入大模型大脑
    final_features = llm(dummy_text_ids, aligned_v_tokens)
    print(f"🧠 大模型内部特征形状: {final_features.shape} -> 包含了 (196 图像 + 10 文本) 共 206 个 Token，准备预测下一个词！")
