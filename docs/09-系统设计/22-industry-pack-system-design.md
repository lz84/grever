# 行业包系统设计文档

> 版本：v1.0  
> 日期：2026-06-04  
> 状态：讨论稿  
> 范围：行业包的内容定义、物理格式、导入/导出、版本管理全体系  
> 前置文档：21-scenario-library-system-design.md

---

## 一、行业包是什么

### 1.1 定义

**行业包（Industry Pack）是 Nexus 系统中解决某一类行业问题的完整解决方案交付物。**

它是一个可导入导出的物理文件，包含一个行业在特定场景下需要的所有能力定义、场景模板、执行知识和参考数据。

**核心特征**：
- **物理制品**——不是 DB 里的逻辑分组，是一个真实的文件
- **可移植**——导入/导出，跨实例分享
- **自包含**——拿到就能用，不依赖目标系统的已有数据
- **版本化**——语义版本管理，支持升级

### 1.2 类比

| 行业包 | 类比 |
|--------|------|
| .nexus-pack 文件 | npm package tarball |
| manifest.json | package.json |
| checksum | package-lock integrity |
| 版本升级 | semver 语义版本 |
| 标准包 | 官方 npm 包 |
| 定制包 | fork 的社区包 |

---

## 二、行业包的三层内容

### 2.1 总体结构

```
行业包内容 = 能力层 + 场景层 + 知识层

能力层（需要什么能力）── Tags + Skills
场景层（做什么步骤）    ── Scenarios + Workflows
知识层（怎么做）        ── Prompt Templates + SOPs + Checklists + Reference Data
```

### 2.2 能力层

#### Tags（能力标签）

| 字段 | 类型 | 必填 | 说明 | 举例 |
|------|------|------|------|------|
| id | string | ✅ | 标签唯一 ID | `tag-chem-detect` |
| tag_name | string | ✅ | 中文名 | "危化品检测" |
| tag_name_en | string | ✅ | 英文名 | `HazardousChemicalDetection` |
| industry | string | ✅ | 所属行业 | "化工安全" |
| description | string | ✅ | 能力描述 | "能够识别和检测现场危化品泄漏" |
| dimension | string | ✅ | 能力维度 | "技术能力" |
| level | string | ✅ | 等级：basic/intermediate/advanced | "advanced" |
| prerequisites | string[] | ❌ | 前置标签 | `["tag-safety-basic"]` |
| tools | string[] | ❌ | 所需工具 | `["气体检测仪", "PH试纸"]` |
| examples | string[] | ❌ | 应用示例 | `["使用便携式气体检测仪识别氯气泄漏"]` |
| match_rules | object | ❌ | 匹配规则 | 关键词 + 最低置信度 |

#### Skills（技能定义）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | ✅ | 技能唯一 ID |
| name | string | ✅ | 技能名 |
| description | string | ✅ | 技能描述 |
| input_schema | object | ✅ | 输入参数定义 |
| output_schema | object | ✅ | 输出结果定义 |
| required_tags | string[] | ❌ | 需要的能力标签 |
| tool_dependency | string | ❌ | 依赖的工具 |

### 2.3 场景层

#### Scenarios（场景模板）

场景是可复用的解决方案蓝图，包含完整的 Goal→Project→Task 结构。

#### Workflows（工作流定义）

工作流定义场景中任务间的执行顺序、条件分支和并行关系。

### 2.4 知识层

#### Prompt Templates（提示词模板）

提示词模板是 Agent 执行任务时的 prompt 蓝图，实例化时注入具体参数。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | ✅ | 模板 ID |
| name | string | ✅ | 模板名 |
| scope | string | ✅ | 作用域：task/project/goal |
| template | string | ✅ | 提示词内容（含变量占位符） |
| variables | object | ❌ | 变量定义 |
| tags | string[] | ❌ | 适用的能力标签 |

#### SOPs（标准操作规程）

SOP 是行业任务的标准操作流程文档，用于 Agent 执行时的参考和验收依据。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | ✅ | SOP ID |
| name | string | ✅ | SOP 名称 |
| industry | string | ✅ | 所属行业 |
| content | string | ✅ | SOP 正文（Markdown 格式） |
| version | string | ✅ | 版本号 |
| tags | string[] | ❌ | 适用的能力标签 |
| related_tasks | string[] | ❌ | 关联的任务模板 ID |

#### Checklists（检查清单）

检查清单是任务执行前后的核对清单，确保关键步骤不遗漏。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | ✅ | 清单 ID |
| name | string | ✅ | 清单名称 |
| scope | string | ✅ | 作用域：pre_task/post_task/pre_project |
| items | ChecklistItem[] | ✅ | 检查项列表 |
| tags | string[] | ❌ | 适用的能力标签 |
| related_tasks | string[] | ❌ | 关联的任务模板 ID |

#### Reference Data（参考数据）

参考数据是行业任务执行时需要的参数表、阈值、对照表等静态数据。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | ✅ | 数据集 ID |
| name | string | ✅ | 数据集名称 |
| type | string | ✅ | 类型：table/lookup/constants |
| data | object | ✅ | 数据内容 |
| tags | string[] | ❌ | 适用的能力标签 |

---

## 三、物理文件格式

### 3.1 `.nexus-pack` 文件

`.nexus-pack` 文件是标准 zip 压缩包（.zip 格式，改后缀名）。

```
pack-root/
├── manifest.json          # 必须，包元数据
├── checksum.json          # 必须，完整性校验
├── signature.json         # 可选，数字签名
├── tags/                  # 能力标签
├── skills/                # 技能定义
├── scenarios/             # 场景模板
├── workflows/             # 工作流定义
├── prompts/               # 提示词模板
├── sops/                  # 标准操作规程
├── checklists/             # 检查清单
├── reference-data/        # 参考数据
└── assets/                # 附加资源
```

### 3.2 manifest.json（包元数据）

```json
{
  "format_version": "1.0",
  "id": "pack-chemical-emergency",
  "name": "化工厂危化品泄漏应急预案",
  "industry": "化工安全",
  "version": "1.2.0",
  "description": "...",
  "author": "Nexus Community",
  "license": "AGPL-3.0",
  "created_at": "2026-06-04T10:00:00Z",
  "updated_at": "2026-06-04T15:00:00Z",
  "pack_type": "standard",
  "base_pack_id": null,
  "dependencies": [
    { "id": "pack-hazmat-basic", "version": ">=1.0.0" }
  ],
  "contents": {
    "tags": [{ "id": "tag-chem-detect", "file": "tags/tag-001.json", "integrity": "sha256:abc123..." }],
    "skills": [...],
    "scenarios": [...],
    "workflows": [...],
    "prompts": [...],
    "sops": [...],
    "checklists": [...],
    "reference_data": [...]
  },
  "stats": {
    "tags_count": 15,
    "skills_count": 8,
    "scenarios_count": 3,
    "workflows_count": 3,
    "prompts_count": 12,
    "sops_count": 5,
    "checklists_count": 4,
    "reference_data_count": 2,
    "total_files": 52
  }
}
```

### 3.3 checksum.json（完整性校验）

```json
{
  "algorithm": "sha256",
  "files": {
    "manifest.json": "sha256:aaa111...",
    "tags/tag-001.json": "sha256:bbb222..."
  },
  "manifest_checksum": "sha256:aaa111..."
}
```

---

## 四、数据库设计

### 4.1 现有表修改（industry_packs）

```sql
ALTER TABLE industry_packs ADD COLUMN format_version TEXT DEFAULT '1.0';
ALTER TABLE industry_packs ADD COLUMN author TEXT;
ALTER TABLE industry_packs ADD COLUMN license TEXT DEFAULT 'proprietary';
ALTER TABLE industry_packs ADD COLUMN compatibility_min_version TEXT;
ALTER TABLE industry_packs ADD COLUMN compatibility_max_version TEXT;
ALTER TABLE industry_packs ADD COLUMN source_checksum TEXT;
ALTER TABLE industry_packs ADD COLUMN source_signature TEXT;
ALTER TABLE industry_packs ADD COLUMN import_source TEXT DEFAULT 'created';
ALTER TABLE industry_packs ADD COLUMN import_source_file TEXT;
ALTER TABLE industry_packs ADD COLUMN dependencies TEXT DEFAULT '[]';
```

### 4.2 新增表

| 表名 | 说明 |
|------|------|
| `industry_pack_versions` | 包版本历史 |
| `prompt_templates` | 提示词模板 |
| `sops` | 标准操作规程 |
| `checklists` | 检查清单 |
| `reference_data` | 参考数据 |

---

## 五、API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/industry-packs/{pack_id}/export` | 导出包 |
| POST | `/api/v1/industry-packs/import` | 导入包 |
| GET | `/api/v1/industry-packs/{pack_id}/versions` | 版本历史 |
| POST | `/api/v1/industry-packs/{pack_id}/upgrade` | 升级到新版本 |
| GET | `/api/v1/industry-packs/{pack_id}/diff/{other_pack_id}` | 包对比 |
| POST | `/api/v1/industry-packs/{pack_id}/validate` | 校验包完整性 |
| GET/POST/PUT/DELETE | `/api/v1/prompt-templates` | 提示词模板 CRUD |
| GET/POST/PUT/DELETE | `/api/v1/sops` | SOP CRUD |
| GET/POST/PUT/DELETE | `/api/v1/checklists` | 检查清单 CRUD |
| GET/POST/PUT/DELETE | `/api/v1/reference-data` | 参考数据 CRUD |

---

## 六、安全考虑

| 风险 | 防护 |
|------|------|
| zip bomb | 限制解压后总大小 ≤ 50MB |
| 路径遍历攻击 | 解压时校验所有文件路径不含 `../` |
| 篡改包内容 | checksum 校验 |
| 伪造来源 | 数字签名验证（可选） |

---

## 七、错误码

| 错误码 | 类型 | 说明 |
|--------|------|------|
| 40001 | invalid_package | 不是有效的 .nexus-pack 文件 |
| 40002 | checksum_mismatch | 文件完整性校验失败 |
| 40003 | missing_dependency | 缺少依赖包 |
| 40004 | incompatible_version | 包格式版本不兼容 |
| 40005 | incomplete_contents | 包内容不完整 |
| 40901 | pack_exists | 包已存在 |
| 40902 | version_not_newer | 导入版本不高于当前版本 |
| 40401 | pack_not_found | 包不存在 |

---

**版本：** v1.0  
**日期：** 2026-06-04  
**维护者：** 刚子
