# ORM Session 生命周期规范

> 2026-06-09 固化，基于 `scoped_session.remove()` 引发的 detached object 教训

## 核心原则

**一个请求一个 session，请求结束自动关闭。**

## 铁律

### 1. 禁止使用 `scoped_session` + `remove()`

`scoped_session.remove()` 会**分离整个线程 identity map 中的所有 ORM 对象**。如果同进程内有后台代码（如调度器）持有这些对象，访问时会报：
```
Object <Project> cannot be converted to 'persistent' state, as this identity map is no longer valid
```

**已修复**：`shared/database/session.py` 已改用普通 `sessionmaker` + `db.close()`。

### 2. API 路由：统一使用 `Depends(get_db)`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from reins.common.database import get_db

router = APIRouter()

@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    return {"projects": [p.to_dict() for p in projects]}
```

`get_db` 是 FastAPI 依赖注入，自动管理 session 生命周期：
- 请求开始 → 创建 session
- 请求结束 → 自动 `session.close()`
- 异常 → 自动 `session.rollback()` + `close()`

### 3. 业务逻辑层：接收 session 参数

业务逻辑类/函数**不要自己创建 session**，由调用方（API 路由）传入：

```python
# ❌ 错误：业务逻辑自建 session
class MyLogic:
    def do_something(self):
        session = Session(engine)  # 不要用！
        try:
            ...
        finally:
            session.close()

# ✅ 正确：接收 session 参数
class MyLogic:
    def do_something(self, session: Session):
        ...  # 直接查询，不管理生命周期
```

调用方：
```python
@router.post("/do")
def do_something(req: MyRequest, db: Session = Depends(get_db)):
    return MyLogic().do_something(db)  # 传入 session
```

### 4. 非 API 代码（调度器、定时任务等）

不在 HTTP 请求上下文中，无法使用 `Depends(get_db)`。使用 `db.get_session()` + `try/finally`：

```python
# 调度器代码
def tick():
    session = db.get_session()
    try:
        projects = session.query(Project).filter(...).all()
        ...
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

或者用 `with` 语句：
```python
from sqlalchemy.orm import Session

def tick():
    with Session(db.engine) as session:
        projects = session.query(Project).filter(...).all()
        ...
        session.commit()
```

### 5. 禁止直接 `Session(engine)`（除非用 `with` 语句）

```python
# ❌ 错误：手动管理，容易泄漏
session = Session(engine)
result = session.query(...).first()
# 忘了 session.close() → 泄漏

# ✅ 正确：用 with 语句
with Session(engine) as session:
    result = session.query(...).first()
    session.commit()  # with 会自动 close
```

### 6. 不要在 session 关闭后持有 ORM 对象

返回 dict 或 Pydantic 模型，不要返回 ORM 对象：

```python
# ❌ 错误：返回 ORM 对象，调用方在 session 关闭后访问会报错
@router.get("/project/{id}")
def get_project(id: str, db: Session = Depends(get_db)):
    return db.query(Project).filter(Project.id == id).first()

# ✅ 正确：返回 dict
@router.get("/project/{id}")
def get_project(id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == id).first()
    if not project:
        raise HTTPException(404, "Not found")
    return project.to_dict()
```

## 自查清单

开发完成后运行以下检查：

```bash
# 检查是否还有 scoped_session
grep -rn "scoped_session" packages/server/src/

# 检查是否还有 Session(engine) 不用 with 语句
grep -rn "Session(.*engine)" packages/server/src/

# 检查是否还有 db.query() 快捷方法（已删除）
grep -rn "\.db\.query\(" packages/server/src/
```

**有输出 = 违规，必须修复。**

## 总结表

| 场景 | 正确做法 | 错误做法 |
|------|----------|----------|
| API 路由 | `db: Session = Depends(get_db)` | `Session(engine)` |
| 业务逻辑 | 接收 `session: Session` 参数 | 自建 session |
| 调度器/后台任务 | `db.get_session()` + `try/finally` | `scoped_session` |
| 返回数据 | `project.to_dict()` 或 Pydantic | 直接返回 ORM 对象 |
| Session 关闭 | `with Session(...)` 或 `try/finally` | 忘了 close |
