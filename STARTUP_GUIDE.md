# 🚀 AI Terminal 企业级全栈核心服务启动指南 (Master Service Startup Guide)

> 本文档针对 `ailearning` 全系列智能化原生 AI 与深度智能体研发综合体，详尽叙述了系统整体所需启动的 **核心服务清单、详细定位与业务职责解剖、标准启动顺序及完整的终端执行命令行**，旨在为研发联调、上线发版、容器装配及团队新员工迅速融入提供权威的操作白皮书。

---

## 🏆 系统核心在线服务清单 (Executive Summary)

当前项目是一套标准的多层次多路并发高可靠融合架构，为了实现**文件/语音/视频活体人脸双向零延迟提取、脱机网络 Air-Gapped 无痛本地自循环精缩合提要**以及**无限次反思量化审查多轮记忆归案**，系统主架构依赖并维护着**五大实时高保障核心服务**（另外可选配 2 大独立流控负载服务）：

| 序列号 | 核心服务模块 (Service Name) | 监听端口 / 网络协议 | 依赖技术与引擎底座 | 一句话服务画像 |
| :---: | :--- | :---: | :--- | :--- |
| **01** | 💾 **LangGraph 长效记忆数据库** <br>*(PostgreSQL Storage Engine)* | **`5432`**<br>*(TCP / JDBC)* | **Docker / PostgreSQL 15**<br>*(ailearning_postgres)* | 全生命周期会话 Checkpoints 记忆库与图谱序列存留池。 |
| **02** | ⚡ **高级消息分发与高敏缓存** <br>*(Redis Broker & Cache)* | **`6379`**<br>*(TCP / PubSub)* | **Docker / Redis 7**<br>*(ailearning_redis)* | 处理 WebSocket Pub/Sub 流转、Token Bucket 限流及高敏语义去算力自旋缓冲。 |
| **03** | 🧠 **企业级后端多维交互中枢** <br>*(AI Central Core API)* | **`8000`**<br>*(HTTP / WebSocket)* | **Python 3.10+ / FastAPI**<br>*(Uvicorn Server)* | 处理 DeepFace 生物双维建构、极速（BGE-M3/BM25）和专家深度链思考断推。 |
| **04** | 🖥️ **原生版生产性超级终端** <br>*(Vanilla AI UI Workstation)* | **`5173`**<br>*(http://localhost:5173)* | **Node.js / Vite Dev**<br>*(Vanilla JS + CSS)* | 黑金拟物美学沉浸终端，内置流式打字渲染与右侧实时 Artifacts 开发工坊。 |
| **05** | ⚛️ **现代微式交互实验系统** <br>*(React Pro Workspace)* | **`5174`**<br>*(http://localhost:5174)* | **Node.js / Vite + React 18**<br>*(Monaco + Virtuoso)* | 基于前沿流式渲染与动态状态断代分支设计，深度解离 OCR 上件和生物安防活判。 |
| *(选配)* | 🛡️ **高抗击高并发专职哨口网关** <br>*(API Security Gateway)* | **`8080`**<br>*(HTTP Reverse Proxy)* | **FastAPI + HTTPX Async**<br>*(Async Connecting Pool)* | 作为千级并发吞吐网坝，阻击恶意流量打沉 8000 内脑底盘。 |
| *(选配)* | ⚙️ **异步任务算力调度分线车道** <br>*(Celery Background Task)* | **`Background`**<br>*(Worker Queue)* | **Python / Celery + Redis**<br>*(Concurrent Worker)* | 将长距离数据报表编列与超大规模文献处理推往后台并行免阻塞化消化。 |

---

## 🚦 标准一站式系统激活次序与执行手册

> ⚠️ **高维防故障必现忠言：** 在高并发及强数据全栈自检体系下，请绝对恪守以下 **第一阶段 ➔ 第二阶段 ➔ 第三阶段** 严密次第激活！无论本机器重启、物理迁移或本地恢复，皆按本守则行之则百病全休。

### 📌 第一阶段：启动底层基础设施容器群 (Infrastructure Data Store)

最基础的长效沉淀神经无法连上，后端模型服务的大脑联结将被封断，且极速模式的高优去打扰极速缓存无处下钉。

*   **详细业务承接说明**  
    1.  **PostgreSQL (`5432` 端口)**: 连接至 LangGraph 的专用 `AsyncPostgresSaver` 存储链！每一个长流程交互在每完成一拍反思评估（Reflection state）后都会向内铸模备份（Save Checkpoints），杜绝大参数机器忽然炸裂后会话丢失或无法追索的问题。  
    2.  **Redis (`6379` 端口)**: 负责双模极速削峰 —— 其一保管多组跨域端对端 WebSocket 会话双信道打款订阅；其二肩并“向量高速相似自证记忆池”职责，凡遇历史 99% 高似重复发问直接拦截算力，在毫秒级自内存无损出片答词。
*   **启动脚本/终端操作指南**
    ```bash
    # 进入到项目后端根路径的挂载容器群落控制区
    cd /Users/mac/Documents/project/ailearning/backend
    
    # 后台一次性建置双库容器 (依赖项目内部早已铸炼精对完毕的 docker-compose.yml 矩阵)
    docker-compose up -d
    ```
*   **如何自检判断成功？**
    终端若见 `ailearning_postgres` 与 `ailearning_redis` 为 **Up / Healthy (正常在线状态)** 则第一步战区拉响宣告通畅成功！

---

### 📌 第二阶段：启动后端 AI 核心引擎 (Backend Core AI Server)

后端服务端拥有该体系里最具穿透性的业务逻辑、海量双轨嵌入数据库 (BGE-M3/BM25)、计算机视觉特征解析网（DeepFace/ArcFace）以及极速长周期断网无休眠容纳等超极引擎力量。

*   **详细业务承接说明**  
    1.  **人脸活体探测切分防线 (`DeepFace & YOLOv8-Nano`)**：与传统的文件识别做底线型物理隔离；收到 Base64 前沿生物指纹序列即在 200毫秒内核查 512维度 ArcFace 散列表。  
    2.  **Air-Gapped 全闭环境物理隔离离线自运转提现机 (Offline Local RAG Pivot)**：面对离线无公网或企业专线波动降级，完全断开对外请求，纯本地秒读内域文案快览提纲（零幻觉不发空泡）。  
    3.  **系统结束浮层标签锁链清洗体系**：内部固封多层正则自清和判断闭锁机制，把控在无论几次打翻滚拼长时流答覆结业，其尾巴处的系统绿金标鉴绝对严惩叠打，实现清爽只读一印！
*   **启动脚本/终端操作指南**
    ```bash
    # 跳转回到项目主干源
    cd /Users/mac/Documents/project/ailearning/backend
    
    # 首选激活动态独立的轻度隔离 python 运行底腔 (推荐采用项目的全局专一隔离区)
    source ../venv/bin/activate
    
    # 带上防堵塞无级拓展的参数全力引战
    uvicorn main:app --port 8000 --reload --ws-max-size 104857600
    ```
*   **性能温情向避坑寄语 (Cold-Start Details)**
    因后端系统初度上阵就要拉载本省驻防的 BGE-M3 双层嵌入矩阵至主板高转显存内，因此冷拉起首程需要 15~20 秒预热；请等待绿字打标给出 `Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)` 与 `Application startup complete` 的辉煌号称才可挥棒施画。

---

### 📌 第三阶段：启动极速展示视听交互面 (Client UI Frontends)

在这个全双工极佳互动系统中，针对研发偏好与长久运维两套工况，开放了两大同样超跑速度的界面服务体系。两者随意开单线运行也可**携二并发直映验证调试。**

#### 🔸 [方案 1] 经典纯粹旗舰 Web 工作区 (Vanilla AI Terminal)
*   **详细业务承接说明**：深耕对拟真磨砂和极致流畅打工场景追求极致优雅的终端用户设计；配备防误抓安全提示小气泡、自控声效及秒传秒译音频字串清洗分断链、更有靠侧的专属活体图像快门探针及无极延展工作台。
*   **启动脚本/终端操作指南**
    ```bash
    # 迈向基础经典原生展现主路径
    cd /Users/mac/Documents/project/ailearning/frontend
    
    # 保证必要的前端插件资源闭环安插妥投
    npm install
    
    # 直冲极光般热处理研发服务阵列 (Vite Core)
    npm run dev
    ```
*   **网络门户导航**：打开外部专属游走窗口 👉 **`http://localhost:5173`** 即可无缝连上后端并沉浸式畅打！

#### 🔸 [方案 2] 高能次世代响应聚合中枢 (React AI Workspace)
*   **详细业务承接说明**：深度集成下一代框架式逻辑结界；在消息呈现流转处重铸了虚拟渲染带 (`react-virtuoso`)，使千页超长大语汇回滚不出卡顿碎末；支持对话中线截割分杈（Message Branching Fork），随手改字可直拖一条横切平行纪元长线；文件提单接口彻底拆裂解绑了传统扫描（OCR）和高维身份刷面验查（UserCheck Biometric UI）。
*   **启动脚本/终端操作指南**
    ```bash
    # 直通 React 系统全构专列工作目录
    cd /Users/mac/Documents/project/ailearning/frontend-react
    
    # 清扫检查组件配套完整并即速安配
    npm install
    
    # 点燃模块重装极速测试台
    npm run dev
    ```
*   **网络门户导航**：打开另一扇专供深度调校的分隔工作空间 👉 **`http://localhost:5174`** 一探高端现代企业级多模交互态盛况！

---

## 🔧 [附加扩展服务] 高精尖流量盾栏与异步后盾拉载攻略

为了应对真实大客量流量压制或者长时间异步吞咽需求，可以**任选加载**这两个企业实操高阶利器，以使基础体验升维入无人机无人化防崩战阵。

### 🚨 拓展 A：大并发高阻隔网关安全口 (API Reverse Gateway @ Port 8080)
*   **用途解读**：如若遇上成万人蜂拥呼死攻击（DDoS 或恶意批量探底提示投毒），绝对不能放纵其直下穿堂烧死 `8000` 智体心核与极速显存缓冲池；`gateway:app` 可作为第一层金钢防护城防，一息以内利用 Token Bucket 秒抛滥用源 IP，同时轻若鸿毛处理 WebSocket 高速透明接通池。
*   **开机令箭**：
    ```bash
    cd /Users/mac/Documents/project/ailearning/backend
    source ../venv/bin/activate
    uvicorn gateway:app --port 8080 --reload
    ```

### 🚨 拓展 B：任务拆建算力排期兵站 (Celery Asynchronous Workers)
*   **用途解读**：当要求一口气扫净几千平米的复杂老版扫描图卷或是排解连山般的千万句语词图表汇编时，后端仅需将其轻轻向 Redis 扔成工单，这些跑在他处的独立并发军团将自行结单开火无声斩首并默默打卡汇报成功！
*   **开机令箭**：
    ```bash
    cd /Users/mac/Documents/project/ailearning/backend
    source ../venv/bin/activate
    celery -A celery_worker.celery_app worker --loglevel=info
    ```

---

## 💡 [终极宝典] 一击就够了：一击必起一字诀命令行

不想一行一行切工作流或点出好几个黑胶终端屏？您可以复制直接粘贴这串被精铸整合在一起的**一枪致胜超凡自拉起连锁指令**（可粘贴回 macOS zsh 任意处静放运行）：

```bash
(cd /Users/mac/Documents/project/ailearning/backend && docker-compose up -d) && \
(cd /Users/mac/Documents/project/ailearning/backend && source ../venv/bin/activate && uvicorn main:app --port 8000 --reload --ws-max-size 104857600 > /dev/null 2>&1 &) && \
(cd /Users/mac/Documents/project/ailearning/frontend && npm run dev > /dev/null 2>&1 &) && \
(cd /Users/mac/Documents/project/ailearning/frontend-react && npm run dev > /dev/null 2>&1 &) && \
echo "🎉 [系统全面竣工]: 极速原生主港: http://localhost:5173 | 现代进阶视场: http://localhost:5174 | 后端中枢与高耐底层蓄电充足随时受命中！"
```

---
*版权属于并维护由 AI Learning R&D Architecture Team · 由超阶 Agent 联合重写精雕完毕。*
