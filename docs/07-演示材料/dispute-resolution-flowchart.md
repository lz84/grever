# 智能体 间争议解决流程图

---

## 版本 1：完整流程图（适合详细讲解）

```mermaid
flowchart TD
    Start([多智能体 协同任务开始]) --> Task[任务执行]
    Task --> Opinion{出现意见分歧？}
    
    Opinion -->|否 | Continue[继续执行]
    Continue --> Task
    
    Opinion -->|是 | Step1
    
    subgraph Step1["步骤 1: 各方提案"]
        P1[智能体 A 提交方案<br/>带论据 + 约束]
        P2[智能体 B 提交方案<br/>带论据 + 约束]
        P3[...其他智能体]
    end
    
    P1 --> P2
    P2 --> P3
    P3 --> Step2Entry
    
    subgraph Step2["步骤 2: 相互修正"]
        Step2Entry[阅读其他智能体 方案]
        M2[寻找共同点]
        M3[提出妥协方案]
        M4{达成共识？}
    end
    
    Step2Entry --> M2
    M2 --> M3
    M3 --> M4
    
    M4 -->|是 ✅ | Step3
    M4 -->|否 ❌ | Step4{超时？}
    
    Step4 -->|否 ⏳ | Step2Entry
    Step4 -->|是 ⏰ | Step5
    
    subgraph Step3["步骤 3: 达成共识"]
        R1[记录决策依据]
        R2[更新任务状态]
        R3[继续执行任务]
    end
    
    R1 --> R2
    R2 --> R3
    R3 --> End([争议解决完成])
    
    subgraph Step5["步骤 4: 超时升级"]
        H1[自动打包争议快照]
        H2[→ 争议焦点]
        H3[→ 各方论据]
        H4[→ 已尝试的妥协方案]
        H5[→ 智能体 推荐建议]
        H6[推送给人类管理员]
    end
    
    H1 --> H2 --> H3 --> H4 --> H5 --> H6
    H6 --> Human[人类仲裁]
    
    Human --> Decision{人类做出决定}
    Decision --> Record[记录决策依据]
    Record --> End
    
    style Step1 fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    style Step2 fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    style Step3 fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    style Step5 fill:#fce4ec,stroke:#f44336,stroke-width:2px
    style Human fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    style Continue fill:#e8f5e9,stroke:#4caf50
    style End fill:#e8f5e9,stroke:#4caf50,stroke-width:3px
```

---

## 版本 2：简化版（适合 PPT 单页展示）

```mermaid
flowchart LR
    A[意见分歧] --> B[各方提案]
    B --> C[相互修正]
    C --> D{达成共识？}
    D -->|是 | E[执行共识方案]
    D -->|否 | F{超时？}
    F -->|否 | C
    F -->|是 | G[推送人类仲裁]
    G --> H[争议可视化]
    H --> I[人类一键决策]
    I --> E
    
    style A fill:#ffebee,stroke:#f44336
    style B fill:#e3f2fd,stroke:#2196f3
    style C fill:#fff3e0,stroke:#ff9800
    style E fill:#e8f5e9,stroke:#4caf50
    style G fill:#f3e5f5,stroke:#9c27b0
    style H fill:#f3e5f5,stroke:#9c27b0
    style I fill:#f3e5f5,stroke:#9c27b0
```

---

## 版本 3：带时间线的流程图（展示协商过程）

```mermaid
sequenceDiagram
    participant A as 智能体 A（麻子）
    participant B as 智能体 B（谷子）
    participant N as Nexus 平台
    participant H as 人类管理员
    
    Note over A,B: 任务执行中出现分歧
    A->>N: 提交方案 A（Playwright）<br/>论据：功能强
    B->>N: 提交方案 B（Scrapy）<br/>论据：速度快
    N->>A,B: 展示各方方案
    
    A->>B: 阅读方案 B
    B->>A: 阅读方案 A
    
    A->>N: 提出妥协：混合使用
    N->>B: 询问是否接受
    B->>N: 反对：维护成本高
    
    Note over N: ⏰ 超时（20 分钟）
    N->>H: 推送争议快照<br/>- 争议焦点<br/>- 各方论据<br/>- 妥协历史<br/>- 推荐建议
    
    H->>N: 批准推荐方案
    N->>A,B: 执行混合方案
    
    Note over A,B,N,H: ✅ 争议解决，任务继续
```

---

## 版本 4：泳道图（展示各角色职责）

```mermaid
flowchart TD
    subgraph Agent["🤖 智能体"]
        A1[提交方案]
        A2[阅读其他方案]
        A3[提出妥协]
        A4[执行共识/仲裁结果]
    end
    
    subgraph Nexus["⚙️ Nexus 平台"]
        N1[收集各方方案]
        N2[展示对比]
        N3[促进协商]
        N4[超时检测]
        N5[打包争议快照]
        N6[推送人类仲裁]
        N7[记录决策依据]
    end
    
    subgraph Human["👤 人类管理员"]
        H1[收到仲裁通知]
        H2[查看争议可视化]
        H3[一键做出决定]
    end
    
    A1 --> N1
    N1 --> N2
    N2 --> A2
    A2 --> A3
    A3 --> N3
    N3 --> A1
    
    N3 --> N4
    N4 -->|超时 | N5
    N5 --> N6
    N6 --> H1
    H1 --> H2
    H2 --> H3
    H3 --> N7
    N7 --> A4
    
    style Agent fill:#e3f2fd,stroke:#2196f3
    style Nexus fill:#f5f5f5,stroke:#9e9e9e
    style Human fill:#f3e5f5,stroke:#9c27b0
```

---

## 版本 5：PPT 精简版（最适合演讲）

```mermaid
flowchart TD
    Start([多智能体 意见分歧]) --> Propose[各方提案]
    Propose --> Negotiate[协商修正]
    Negotiate --> Check{达成共识？}
    Check -->|是 ✅ | Execute[执行共识]
    Check -->|否 ❌ | Timeout{超时？}
    Timeout -->|否 | Negotiate
    Timeout -->|是 ⏰ | Human[人类仲裁]
    Human --> Visualize[争议可视化]
    Visualize --> Decide[一键决策]
    Decide --> Execute
    
    style Start fill:#ffebee,stroke:#f44336,color:#000
    style Propose fill:#e3f2fd,stroke:#2196f3,color:#000
    style Negotiate fill:#fff3e0,stroke:#ff9800,color:#000
    style Execute fill:#e8f5e9,stroke:#4caf50,color:#000
    style Human fill:#f3e5f5,stroke:#9c27b0,color:#000
    style Visualize fill:#f3e5f5,stroke:#9c27b0,color:#000
    style Decide fill:#f3e5f5,stroke:#9c27b0,color:#000
```

---

## 使用建议

| 版本 | 场景 | 优点 |
|------|------|------|
| **版本 1** | 详细技术文档 | 完整展示所有步骤和判断 |
| **版本 2** | PPT 单页 | 简洁，横向布局节省空间 |
| **版本 3** | 时序说明 | 清晰展示时间线和交互 |
| **版本 4** | 角色分工 | 明确各智能体/平台/人类职责 |
| **版本 5** | **PPT 演讲推荐** | 颜色区分 + 表情符号，视觉友好 |

---

## 配色说明

| 颜色 | 含义 |
|------|------|
| 🔴 红色 | 问题/分歧起点 |
| 🔵 蓝色 | 智能体 活动 |
| 🟠 橙色 | 协商过程 |
| 🟢 绿色 | 成功解决 |
| 🟣 紫色 | 人类参与 |

---

## 金句配合

流程图旁边可以配这句话：

> **人在回路中，但不必事事亲为——人类做仲裁，不是当保姆。**

或者：

> **智能体 能协商，协商不成再升级——人类只需做选择题。**
