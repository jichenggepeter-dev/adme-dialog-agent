# Issue #1 小白教程：让 Python 依赖“写清楚、装得上、测得过”

这篇教程解释 GitHub Issue
[#1](https://github.com/jichenggepeter-dev/adme-dialog-agent/issues/1)
修复了什么，以及如何在不使用 API key、付费模型或外部 LLM 的情况下，
一步一步验证修复结果。

本任务不验证 ADME/ADMET 预测是否具有科学准确性。它只验证：

1. Python 项目能否正确说明自己需要哪些软件包；
2. 新环境能否按照说明完成安装；
3. 文件上传和后端测试能否正常运行。

## 1. 先理解三个依赖文件

### `requirements.txt`：开发环境购物清单

它告诉 `pip` 或 `uv`：

> 为了运行和测试这个仓库，请把清单里的软件包装上。

当前 README 和 CI 主要通过它安装后端依赖。

### `pyproject.toml`：项目身份证和正式合同

它记录：

- 项目名称和版本；
- 支持的 Python 版本；
- 普通用户运行项目必须安装的依赖；
- 开发者运行测试才需要的额外依赖；
- 使用什么工具构建 Python 包；
- 哪些目录属于 Python 包。

### `uv.lock`：一次精确采购留下的收据

`pyproject.toml` 可能只写 `fastapi`，而锁文件会记录当时实际解析出的具体
版本及其间接依赖。

修改 `pyproject.toml` 后，需要重新生成并检查 `uv.lock`。某个包碰巧出现在
锁文件中，不代表项目已经正确声明它是直接依赖。

## 2. 为什么需要三个相似名称的包

| 安装名称 | Python 中的名称 | 在本项目中的用途 |
| --- | --- | --- |
| `python-multipart` | `python_multipart` | 解析浏览器上传的文件 |
| `httpx` | `httpx` | Agent provider 的运行时 HTTP 配置 |
| `httpx2` | `httpx2` | Starlette/FastAPI 的 `TestClient` |

### `python-multipart`

浏览器上传 CSV 时，通常发送 `multipart/form-data` 请求。FastAPI 看到
`UploadFile` 和 `File(...)` 后，需要 `python-multipart` 把请求拆成文件名、
文件类型、内容和其他表单字段。

缺少它时，上传路由可能在导入或运行时失败。

### `httpx` 和 `httpx2`

它们是两个可以共存的独立发行包，不是“只能选择一个”的新旧版本关系。

```text
正常运行 Agent
  -> app/agent_runtime/provider.py
  -> httpx.Timeout
  -> OpenAI-compatible provider

运行后端测试
  -> pytest
  -> Starlette TestClient
  -> httpx2
  -> 在本机进程内调用 FastAPI
```

项目代码直接 `import httpx`，所以项目应当直接声明它，不能只依赖
`openai` 软件包顺便安装它。`httpx2` 仍然保留在开发和测试依赖中。

## 3. Issue #1 的最小修改

`pyproject.toml` 现在明确：

- 使用 setuptools 构建；
- 只把 `app*` 作为 Python 包，避免把 `frontend` 误认为 Python 包；
- 把 `python-multipart` 和 `httpx>=0.23.0,<1` 声明为运行时依赖；
- 把 `pytest` 和 `httpx2` 保留为开发依赖。

`requirements.txt` 也同时包含运行时 `httpx` 和测试用 `httpx2`。

最后重新生成 `uv.lock`，让正式合同和精确收据保持一致。

## 4. 准备一个不会污染日常环境的检查目录

以下命令适用于 macOS 或 Linux。先进入仓库根目录：

```bash
cd adme-dialog-agent
```

创建临时目录：

```bash
CHECK_ROOT="$(mktemp -d)"
echo "$CHECK_ROOT"
```

后续创建的虚拟环境、数据库和测试数据都放在这里，不会覆盖仓库中的
`.venv`、`.env` 或真实运行数据。

## 5. 路径 A：按照 `pyproject.toml` 安装

创建全新的 Python 3.11 环境：

```bash
uv venv --python 3.11 --seed "$CHECK_ROOT/pyproject-env"
"$CHECK_ROOT/pyproject-env/bin/python" -VV
```

最后一条命令应该显示 `Python 3.11.x`。

安装项目和开发依赖：

```bash
uv pip install \
  --python "$CHECK_ROOT/pyproject-env/bin/python" \
  -e ".[dev]"
```

这里：

- `-e` 表示 editable install，修改源码后不需要重复安装项目本身；
- `[dev]` 表示同时安装 `pytest` 和 `httpx2`。

检查依赖冲突：

```bash
uv pip check --python "$CHECK_ROOT/pyproject-env/bin/python"
"$CHECK_ROOT/pyproject-env/bin/python" -m pip check
```

成功时会看到类似：

```text
All installed packages are compatible
No broken requirements found.
```

## 6. 路径 B：按照 `requirements.txt` 安装

再创建一个完全独立的 Python 3.11 环境：

```bash
uv venv --python 3.11 --seed "$CHECK_ROOT/requirements-env"
uv pip install \
  --python "$CHECK_ROOT/requirements-env/bin/python" \
  -r requirements.txt
```

执行同样的依赖检查：

```bash
uv pip check --python "$CHECK_ROOT/requirements-env/bin/python"
"$CHECK_ROOT/requirements-env/bin/python" -m pip check
```

为什么需要两个环境？如果只在同一个环境里先后安装两种清单，第一种安装
留下的软件包可能掩盖第二种清单的遗漏。

## 7. 检查 Starlette 是否使用 `httpx2`

先用 `pyproject.toml` 环境运行：

```bash
"$CHECK_ROOT/pyproject-env/bin/python" - <<'PY'
import importlib
import warnings

import httpx
import httpx2

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    testclient_module = importlib.import_module("starlette.testclient")

messages = [str(item.message) for item in caught]

assert httpx.__name__ == "httpx"
assert httpx2.__name__ == "httpx2"
assert testclient_module.httpx.__name__ == "httpx2"
assert not any("install `httpx2` instead" in item for item in messages)

print("runtime HTTP package:", httpx.__name__)
print("Starlette TestClient package:", testclient_module.httpx.__name__)
print("Starlette warning check: PASS")
PY
```

预期结果：

```text
runtime HTTP package: httpx
Starlette TestClient package: httpx2
Starlette warning check: PASS
```

这证明两个包各自承担不同职责。

## 8. 模拟上传一个最小 CSV

这项测试只在本机 Python 进程中调用 FastAPI，不会上传到外部网站。

```bash
ADME_MOCK_MODE=true \
AGENT_ENABLED=false \
AGENT_DB_PATH="$CHECK_ROOT/upload-test.sqlite3" \
"$CHECK_ROOT/pyproject-env/bin/python" - <<'PY'
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    response = client.post(
        "/batch/upload",
        files={
            "file": (
                "batch.csv",
                b"smiles,name\nCCO,ethanol\n",
                "text/csv",
            )
        },
    )

assert response.status_code == 200, response.text
body = response.json()
assert body["file_type"] == "csv", body
assert body["row_count"] == 1, body
assert body["columns"] == ["smiles", "name"], body
assert body["suggested_mapping"]["smiles"] == "smiles", body

print("multipart upload route: PASS")
PY
```

这里的 `CCO` 是乙醇的一种文字结构表示。本测试只关心 CSV 是否被正确
接收和解析，不进行真实模型预测。

## 9. 运行完整后端测试

下面的命令显式关闭 Agent 和真实 LLM 集成测试，并移除常见的凭据环境变量：

```bash
env \
  -u OPENAI_API_KEY \
  -u AGENT_LLM_API_KEY \
  -u AGENT_LLM_BASE_URL \
  -u AGENT_LLM_MODEL \
  ADME_MOCK_MODE=true \
  AGENT_ENABLED=false \
  RUN_AGENT_LLM_INTEGRATION=0 \
  OPENAI_AGENTS_DISABLE_TRACING=1 \
  AGENT_DB_PATH="$CHECK_ROOT/full-suite.sqlite3" \
  "$CHECK_ROOT/pyproject-env/bin/python" -m pytest \
    -q \
    -ra \
    -W 'error:Using `httpx` with `starlette\.testclient` is deprecated'
```

Issue #1 验收时的结果是：

```text
105 passed, 2 skipped
```

两个 `skipped` 是预期行为。它们是需要真实本地 LLM 服务的集成测试，只有
明确设置 `RUN_AGENT_LLM_INTEGRATION=true` 才会运行。

随着项目以后增加测试，`passed` 数量可能变化。真正需要坚持的是：

- `0 failed`；
- `0 errors`；
- 两个真实 LLM 测试按正确原因跳过；
- 没有要求安装 `httpx2` 的 Starlette 警告；
- 没有 API key、付费模型或外部 LLM 调用。

然后把命令中的 `pyproject-env` 改成 `requirements-env`，再运行一次完整
测试，证明第二条安装路径也成立。

## 10. 检查锁文件和构建产物

确认锁文件与 `pyproject.toml` 一致：

```bash
uv lock --check
```

构建 wheel：

```bash
uv build --wheel --out-dir "$CHECK_ROOT/dist"
unzip -l "$CHECK_ROOT/dist/adme_dialog_agent-0.1.0-py3-none-any.whl"
```

列表中应该包含 `app/**` 和 `adme_dialog_agent-0.1.0.dist-info/**`，不应该
包含 `frontend/**`、`.env`、数据库或本地运行状态。

## 11. 如何读懂常见失败

| 现象 | 通常代表什么 |
| --- | --- |
| `No module named httpx` | 运行时依赖没有正确安装 |
| 提示安装 `python-multipart` | 文件上传解析依赖缺失 |
| 提示安装 `httpx2` | Starlette 没有找到正确的测试传输层 |
| `Multiple top-level packages discovered` | 没有明确 Python 包发现范围 |
| `No broken requirements found` | 已安装依赖之间没有已知冲突 |
| `failed` | 测试执行了，但结果不符合断言 |
| `error` | 测试通常还没真正开始，例如导入失败 |
| `skipped` | 测试按照条件被有意跳过 |

## 12. 什么时候可以关闭 GitHub Issue

推荐顺序：

```text
本地两条全新安装路径通过
  -> 本地完整测试通过
  -> 提交并推送修复
  -> GitHub Actions 在对应提交上通过
  -> 再关闭 Issue
```

因此，“本地测试通过”代表修复已经具备发布条件，但在代码还没有进入远端、
CI 还没有验证之前，公开 Issue 应继续保持 open。
