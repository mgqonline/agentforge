"""
Vision Token 图像压缩与分块适配器 (Vision Optimizer)
==================================================
技术方案：
  1. 智能缩放采样 (Smart Resizing)：限制最大分辨率，按比例等比缩放，降低图像 Patch / Vision Token 消耗
  2. 高宽高比切片 (Tile Cropping)：对于长图/多页文档自动切分为 512x512 网格切片，避免暴力压扁失真
  3. Base64 自动转换与 Token 占用预估
"""

import io
import base64
from typing import List, Tuple, Dict, Any
from PIL import Image

class VisionOptimizer:
    def __init__(self, max_dimension: int = 1024, detail_level: str = "auto"):
        self.max_dimension = max_dimension
        self.detail_level = detail_level

    def process_image(self, image_input: Any) -> Dict[str, Any]:
        """
        处理图像输入（支持文件路径、字节流或 PIL.Image 对象）
        返回优化后的 Base64 编码、优化信息以及预估 Vision Token 消耗
        """
        if isinstance(image_input, str):
            image = Image.open(image_input)
        elif isinstance(image_input, bytes):
            image = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, Image.Image):
            image = image_input
        else:
            raise ValueError("不支持的图像输入类型")

        orig_w, orig_h = image.size

        # 1. 智能长图切片判定
        aspect_ratio = max(orig_w, orig_h) / min(orig_w, orig_h)
        tiles: List[Image.Image] = []

        if aspect_ratio > 2.5 and (orig_w > 1024 or orig_h > 1024):
            # 长图模式：进行网格切片
            tiles = self._tile_long_image(image)
            mode = "tiled"
        else:
            # 基础智能缩放
            resized_img = self._resize_image(image)
            tiles = [resized_img]
            mode = "resized"

        # 2. 编码与计算 Token 消耗
        b64_list = []
        for t in tiles:
            buffered = io.BytesIO()
            # 格式统一转换为 JPEG 格式降低体积
            if t.mode in ("RGBA", "P"):
                t = t.convert("RGB")
            t.save(buffered, format="JPEG", quality=85)
            b64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            b64_list.append(f"data:image/jpeg;base64,{b64_str}")

        # 预估 Vision Token 消耗（按 512x512 网格为 170 tokens 计算）
        estimated_tokens = len(tiles) * 170 + 85

        return {
            "mode": mode,
            "original_size": (orig_w, orig_h),
            "tile_count": len(tiles),
            "estimated_tokens": estimated_tokens,
            "payload_urls": b64_list
        }

    def _resize_image(self, img: Image.Image) -> Image.Image:
        w, h = img.size
        if max(w, h) <= self.max_dimension:
            return img
        
        if w > h:
            new_w = self.max_dimension
            new_h = int(h * (self.max_dimension / w))
        else:
            new_h = self.max_dimension
            new_w = int(w * (self.max_dimension / h))
            
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    def _tile_long_image(self, img: Image.Image, tile_size: int = 512) -> List[Image.Image]:
        w, h = img.size
        tiles = []
        if h > w:
            # 纵向长图
            for y in range(0, h, tile_size):
                box = (0, y, w, min(y + tile_size, h))
                crop = img.crop(box)
                tiles.append(self._resize_image(crop))
        else:
            # 横向长图
            for x in range(0, w, tile_size):
                box = (x, 0, min(x + tile_size, w), h)
                crop = img.crop(box)
                tiles.append(self._resize_image(crop))
        return tiles


if __name__ == "__main__":
    optimizer = VisionOptimizer(max_dimension=768)
    
    # 模拟创建一个大尺寸超长测试图 (500x2500)
    test_large_img = Image.new("RGB", (500, 2500), color="blue")
    res = optimizer.process_image(test_large_img)
    
    print("📸 Vision Token 优化结果:")
    print(f"  - 原始尺寸: {res['original_size']}")
    print(f"  - 优化模式: {res['mode']}")
    print(f"  - 切片数量: {res['tile_count']}")
    print(f"  - 预估 Token 消耗: {res['estimated_tokens']} Tokens (未经优化可能需要 > 1500 Tokens)")
