### 项目根目录：`personal_ai_tutor`

```plaintext
personal_ai_tutor/
├── .env                  # 存储环境变量 (API密钥, 数据库连接字符串等)
├── .gitignore            # Git忽略文件配置
├── docker-compose.yml    # 【核心】用于一键启动所有服务的编排文件
├── Dockerfile            # 用于构建应用镜像的Dockerfile
├── README.md             # 项目说明文档
├── requirements.txt      # Python依赖包列表
│
└── src/                  # 【核心】所有源代码的根目录
    └── tutor_app/        # 我们的核心Python包
        ├── __init__.py
        │
        ├── core/         # 应用核心配置与通用功能
        │   ├── __init__.py
        │   └── config.py   # 使用Pydantic加载和管理环境变量
        │
        ├── db/           # 数据库模块
        │   ├── __init__.py
        │   ├── models.py   # 【重要】所有数据库表的模型定义 (SQLAlchemy)
        │   └── session.py  # 数据库会话管理
        │
        ├── rag/          # RAG及向量数据库相关逻辑
        │   ├── __init__.py
        │   ├── knowledge_base.py # 知识库管理 (文件加载、切分、向量化)
        │   └── retriever.py  # 带有元数据过滤的检索引擎
        │
        ├── schemas/      # 数据校验与序列化模型 (Pydantic Schemas)
        │   ├── __init__.py
        │   ├── question.py # Question模型的数据结构定义
        │   └── task.py     # Task模型的数据结构定义
        │
        ├── tasks/        # 【重要】Celery异步任务与LangGraph流程
        │   ├── __init__.py
        │   ├── celery_app.py # Celery应用实例的创建和配置
        │   ├── graphs.py   # LangGraph状态图(StateGraph)的定义
        │   └── generation.py # 核心的出题Celery任务定义
        │
        └── web/          # 【重要】Streamlit前端应用
            ├── __init__.py
            ├── app.py      # Streamlit应用主入口 (首页)
            └── pages/      # Streamlit的多页面目录
                ├── 1_📚_Knowledge_Base.py
                ├── 2_⚙️_Generation_Center.py
                ├── 3_✍️_Practice_Mode.py
                ├── 4_📝_Mock_Exam.py
                └── 5_📊_Analysis_Dashboard.py

```

### 各部分功能详解

- **根目录文件**:

  - `.env`: **绝不**将 API 密钥等敏感信息硬编码在代码里，全部写在这里。
  - `docker-compose.yml`: 这是项目的“总开关”。一个命令 (`docker-compose up`) 就能启动 Streamlit 应用、Celery Workers、Redis 和 PostgreSQL 数据库，极大简化了开发和部署。
  - `Dockerfile`: 告诉 Docker 如何打包我们的 Python 应用，包括安装`requirements.txt`中的所有依赖。
  - `requirements.txt`: 项目的所有 Python 依赖，通过`pip install -r requirements.txt`安装。

- **`src/tutor_app/`**: 我们的项目是一个标准的 Python 包。

  - **`core/`**: 存放全局配置。`config.py`会读取`.env`文件，并提供一个类型安全的配置对象供整个应用使用。
  - **`db/`**: 所有与结构化数据库（PostgreSQL）相关的代码。`models.py`是重中之重，它用代码定义了你的数据库表结构。
  - **`rag/`**: 所有与文档处理、向量化和检索相关的逻辑。`retriever.py`中的代码需要确保使用了元数据过滤，以实现知识库的严格隔离。
  - **`schemas/`**: 使用 Pydantic 定义数据结构。这能确保在不同模块间传递的数据是规范和有效的，例如，从 Celery 任务返回给数据库的题目数据必须符合`schemas/question.py`中定义的结构。
  - **`tasks/`**: 后台计算的核心。
    - `celery_app.py`: 初始化 Celery 实例，并连接到 Redis。
    - `graphs.py`: 这里是您定义复杂 LangGraph 流程的地方。
    - `generation.py`: 定义可被前端调用的 Celery 任务，例如 `create_question_generation_task()`。这个任务会去调用`graphs.py`中定义的流程。
  - **`web/`**: 你的 Streamlit 前端应用。
    - `app.py`: 网站的“首页”。
    - `pages/`: Streamlit 的魔法目录。放在这里面的 Python 文件会自动成为导航栏中的不同页面，文件名决定了页面的顺序和名称。这完美符合我们多功能模块的设计。

### 开发启动步骤

1.  **环境准备**:

    - 安装 Docker 和 Docker Compose。
    - 在项目根目录创建`.env`文件，并填入必要的配置：
      ```env
      # .env file
      DATABASE_URL="postgresql://user:password@db:5432/tutor_db"
      REDIS_URL="redis://redis:6379/0"
      OPENAI_API_KEY="sk-..."
      # 其他你需要的API密钥
      ```

2.  **构建并启动服务 (推荐)**:

    - 在项目根目录打开终端，运行命令：
      ```bash
      docker-compose up --build
      ```
    - 这个命令会：
      1.  根据`Dockerfile`构建你的应用镜像。
      2.  启动 PostgreSQL 数据库服务。
      3.  启动 Redis 服务。
      4.  启动 Streamlit 应用服务。
      5.  启动 Celery Worker 服务。
    - 现在，你可以在浏览器中访问 `http://localhost:8501` 来查看你的 Streamlit 应用了。

3.  **本地开发 (不使用 Docker)**:

    - 在多个终端窗口中分别启动各个服务：
      - **终端 1**: `redis-server` (需要先安装 Redis)
      - **终端 2**: `postgres -D /path/to/data` (需要先安装和配置 PostgreSQL)
      - **终端 3**: `celery -A src.tutor_app.tasks.celery_app worker -l info`
      - **终端 4**: `streamlit run src/tutor_app/web/app.py`

---

## **个人智能学习与测评平台 系统架构设计书**

**版本**: 1.0
**日期**: 2025 年 8 月 19 日

### 1\. 绪论

#### 1.1. 文档目的

本文档旨在详细阐述“个人智能学习与测评平台”的总体设计思想、系统架构、核心业务流程、模块功能和技术选型。它将作为后续开发、部署和迭代的指导性纲领。

#### 1.2. 系统概述

本系统是一个面向个人学习者、具备专业级功能的智能化知识内化与自我测评工具。用户作为系统的唯一使用者，同时扮演“**内容架构师（出题官）**”和“**学习者（应试者）**”两种角色。系统通过先进的异步任务处理架构，将大语言模型（LLM）驱动的内容生成过程与用户的高频交互过程完全解耦，旨在提供一个响应迅速、功能强大且高度个性化的学习环境。

#### 1.3. 核心设计思想

- **异步解耦**: 采用任务队列机制，将耗时的 AI 计算与轻量的前端交互分离，保证用户界面的极致流畅。
- **数据驱动**: 用户的学习行为被完整记录，通过数据分析驱动个性化的复习路径（如错题重练）。
- **隔离与准确**: 严格保证基于 RAG（检索增强生成）的内容生成过程在知识源上的隔离性，确保题目与原文高度相关且准确。
- **可扩展性**: 整体架构支持通过增加后台工作单元（Workers）的方式进行水平扩展，以应对未来更高的内容生成需求。

### 2\. 系统架构视图

#### 2.1. 逻辑架构

系统在逻辑上分为四个核心层次：

1.  **表现层 (Presentation Layer)**: 用户直接交互的界面，基于 **Streamlit** 构建。负责任务提交、学习交互和数据可视化。
2.  **应用服务层 (Application Service Layer)**: 系统的“大脑”，负责处理业务逻辑。它接收前端的请求，将其转化为异步任务，并推送到任务队列中。
3.  **后台计算层 (Background Computing Layer)**: 系统的“引擎”，由 **Celery** 管理的多个\*\*工作进程（Workers）\*\*组成。负责从队列中消费任务，执行复杂且耗时的 AI 计算（题目生成）。
4.  **数据持久层 (Data Persistence Layer)**: 系统的“记忆”，负责存储所有数据。
    - **结构化数据库 (PostgreSQL)**: 存储题库、用户信息、学习记录、任务状态等。
    - **向量数据库 (ChromaDB)**: 存储知识库文本的向量索引，用于 RAG 检索。
    - **消息中间件 (Redis)**: 作为 Celery 的 Broker，存储任务队列。

#### 2.2. 数据架构

- **结构化数据库 (PostgreSQL)**:

  - `KnowledgeSources`: 存储用户上传的知识源文件信息。
  - `GenerationTasks`: 存储用户提交的出题任务及其状态（排队中、处理中、已完成）。
  - `Questions`: **核心题库**。存储所有生成好的题目（题干、类型、选项、答案、解析、知识点标签、来源文件 ID）。
  - `PracticeLogs`: 记录每一次刷题的日志（题目 ID、用户答案、是否正确、时间戳）。
  - `Exams` 和 `ExamResults`: 存储模拟考试的试卷构成和考试结果。

- **向量数据库 (ChromaDB)**:

  - 存储文本块（Chunks）的向量。
  - **关键**: 每个向量必须包含**元数据（Metadata）**，如 `{'source_id': 'xxx'}`，用于在 RAG 检索时实现严格的知识源隔离。

### 3\. 核心业务流程

#### 3.1. 知识库与题目生成流程（异步工作流）

1.  **提交**: 用户在 Streamlit 界面选择一个或多个知识源文件，设定题型、数量等参数，创建一个**出题任务**。
2.  **入队**: 应用服务层将该任务打包成消息，发送至 **Redis** 的任务队列。前端立即响应“任务已提交”。
3.  **执行**: 后台的一个空闲 **Celery Worker** 进程从队列中获取该任务。
4.  **编排**: Worker 内部启动一个 **LangGraph** 流程，该流程负责：
    a. 根据任务中的`source_id`，**带元数据过滤器**从 ChromaDB 检索相关文本。
    b. **并发调用**（利用`asyncio`）LLM API，批量生成问题、答案和解析。
    c. 对生成内容进行质检和格式化。
5.  **入库**: LangGraph 流程执行完毕后，将生成的高质量题目批量存入 **PostgreSQL** 的`Questions`表中，并更新`GenerationTasks`表中的任务状态为“已完成”。

#### 3.2. 学习与测评流程（实时交互流）

##### 3.2.1. 刷题模式 (Practice Mode)

用户在刷题模式页面选择以下三种模式之一，所有操作均直接与 PostgreSQL 交互，响应极快。

1.  **只刷新题**:

    - **逻辑**: 从`Questions`表中，筛选出在`PracticeLogs`表中**不存在**的题目。
    - **SQL 示意**: `SELECT * FROM questions WHERE id NOT IN (SELECT DISTINCT question_id FROM practice_logs)`。

2.  **只刷错题**:

    - **逻辑**: 从`PracticeLogs`表中筛选出所有`is_correct = FALSE`的`question_id`，并用这些 ID 去`Questions`表中查询对应的题目。
    - **SQL 示意**: `SELECT * FROM questions WHERE id IN (SELECT question_id FROM practice_logs WHERE is_correct = FALSE)`。

3.  **刷新题 + 错题**:

    - **逻辑**: 这是上述两种逻辑的结合。系统可以设定一个比例（如 70%新题，30%错题），分别执行上述查询，然后将结果合并展示给用户。

每次答题后，答案和对错结果**立即**写入`PracticeLogs`表，并即时展示解析。

##### 3.2.2. 模拟考试模式 (Exam Mode)

1.  **组卷**: 用户选择范围和题型配比，系统从`Questions`数据库中抽取题目，动态生成一份试卷。
2.  **答题**: 用户在模拟环境中作答，所有答案暂存在会话中。
3.  **交卷与分析**: 用户提交试卷后，系统批量批改，将结果存入`ExamResults`表，并立即生成一份包含总分、知识点分析图谱等在内的详细报告。

### 4\. 模块详细设计

- **前端应用 (Streamlit)**:

  - **多页面应用**: 使用`st.navigation`或类似机制构建。
  - **页面划分**: 知识库管理、出题中心（含任务队列看板）、刷题练习、模拟考试、学习分析（数据可视化仪表盘）。
  - **状态管理**: 大量使用`st.session_state`来管理用户答题过程中的临时状态。

- **任务队列系统 (Celery & Redis)**:

  - **任务定义**: 在`tasks.py`中定义核心的 AI 出题任务（`@app.task`）。该任务函数应是异步的（`async def`），以支持内部的协程并发。
  - **Worker 启动**: 通过`celery -A ... worker`命令启动多个后台工作进程。

- **AI 生成核心 (LangChain & LangGraph)**:

  - **LangChain**: 用于构建原子的 RAG 链（检索-\>提示-\>模型-\>解析）。
  - **LangGraph**: 用于编排复杂、带循环和状态的出题工作流，确保生成过程的健壮性和可监控性。

### 5\. 非功能性需求

- **性能**: 前端交互响应时间应在毫秒级。后台题目生成速度取决于 LLM API，通过并发模型最大化吞吐量。
- **可靠性**: Celery 提供任务失败自动重试机制，保证出题任务的最终完成。
- **可扩展性**: 可通过增加 Celery Worker 进程数量来线性提升题目生成的并行处理能力。

### 6\. 技术栈选型

| 类别             | 技术                     | 角色                                       |
| :--------------- | :----------------------- | :----------------------------------------- |
| **前端**         | Streamlit                | 快速构建数据驱动的 Web 应用界面            |
| **后端**         | Python                   | 主要开发语言                               |
| **AI 框架**      | LangChain, LangGraph     | RAG 流程构建与复杂 AI 任务编排             |
| **任务队列**     | Celery                   | 分布式异步任务队列管理                     |
| **消息中间件**   | Redis                    | Celery 的 Broker，负责任务消息传递         |
| **结构化数据库** | PostgreSQL               | 存储题库、用户数据和任务状态               |
| **向量数据库**   | ChromaDB                 | 存储知识库文本向量，支持本地化部署         |
| **并发模型**     | Multiprocessing, Asyncio | 多进程利用多核，协程提升 IO 密集型任务效率 |

---

这份架构设计书全面融合了我们讨论的所有要点，为您提供了一个清晰、完整、且技术上可行的蓝图。
