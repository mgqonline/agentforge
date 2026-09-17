import os
import requests
import time

API_URL = "http://127.0.0.1:8000/recognize"

def test_recognition_accuracy(test_dir: str):
    """
    自动化准确率达标测试脚本 (Target: >90%)
    
    预期的数据集目录结构：
    test_dataset/
      ├── zhangsan/
      │     ├── test_1.jpg
      │     ├── test_2.jpg
      ├── lisi/
      │     ├── test_1.jpg
    """
    if not os.path.exists(test_dir):
        print(f"⚠️ 未找到测试数据集目录 {test_dir}")
        print("请按规范建立测试集，以人名作为文件夹名称，里面放入该员工的测试图片。")
        return

    print("="*60)
    print("🚀 启动工业级人脸识别自动化压测 (达标线: >90%)")
    print("="*60)
    
    total_tests = 0
    correct_matches = 0
    
    # 遍历真实姓名文件夹
    for true_name in os.listdir(test_dir):
        person_path = os.path.join(test_dir, true_name)
        if not os.path.isdir(person_path):
            continue
            
        # 遍历里面的测试照片
        for img_name in os.listdir(person_path):
            if not img_name.endswith(('.jpg', '.png', '.jpeg')):
                continue
                
            img_path = os.path.join(person_path, img_name)
            total_tests += 1
            
            with open(img_path, "rb") as f:
                start_t = time.time()
                try:
                    # 调用我们写的 FastAPI 接口
                    response = requests.post(API_URL, files={"file": f})
                    res_json = response.json()
                except Exception as e:
                    print(f"[{img_name}] HTTP 请求失败: {e}")
                    continue
                end_t = time.time()
                
                # 核心逻辑：判断 AI 识别出的名字，是否与文件夹的真实名字一致
                if res_json.get("match") is True:
                    pred_name = res_json.get("person_name")
                    
                    if true_name.lower() in pred_name.lower():
                        correct_matches += 1
                        status = "✅ 识别正确"
                    else:
                        status = f"❌ 识别错误 (认成了 {pred_name})"
                else:
                    status = f"❌ 拒识 ({res_json.get('message')})"
                    
                print(f"[{true_name}/{img_name}] {status} | 算法耗时: {end_t - start_t:.3f}s")
                
    if total_tests == 0:
        print("⚠️ 数据集为空！")
        return
        
    # 计算最终正确率
    accuracy = (correct_matches / total_tests) * 100
    print("\n" + "="*60)
    print(f"📊 权威质量评估报告 (Quality Assurance Report)")
    print("="*60)
    print(f"• 压测样本总数: {total_tests} 张")
    print(f"• 模型成功命中: {correct_matches} 张")
    print(f"🏆 最终准确率 (Accuracy): {accuracy:.2f}%")
    
    if accuracy >= 90.0:
        print("\n🎉 【结论】模型准确率已达标 (>90%)，符合企业级上线投产标准！")
    else:
        print("\n⚠️ 【结论】准确率未达标。优化建议：")
        print("   1. 检查底层图库 (local_face_db) 中的照片是否过于模糊，必须保证底库照片是高清正脸。")
        print("   2. 测试集中的图片光线是否过暗或存在严重遮挡（口罩、墨镜）。")
        print("   3. 适当调整 face_api.py 中的 distance 阈值 (当前为 0.68，可稍微放宽至 0.70 降低拒识率)。")

if __name__ == "__main__":
    # 执行达标测试
    base_dir = os.path.dirname(os.path.abspath(__file__))
    test_recognition_accuracy(os.path.join(base_dir, "test_dataset"))
