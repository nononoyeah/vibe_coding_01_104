"""阶段3 接口集成测试（对应 NL2SQL-10）。

运行前请启动后端:
    cd data-analysis/backend
    uvicorn app.main:app --reload --port 8000

运行:
    python test_api_phase3.py
    python test_api_phase3.py --base http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class TestResult:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []

    def ok(self, name: str) -> None:
        self.passed.append(name)
        print(f"  ✅ {name}")

    def fail(self, name: str, detail: str) -> None:
        self.failed.append(f"{name}: {detail}")
        print(f"  ❌ {name} — {detail}")

    @property
    def success(self) -> bool:
        return not self.failed


def http_json(
    base: str,
    method: str,
    path: str,
    body: dict | None = None,
    *,
    expected_status: int | None = None,
) -> tuple[int, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        base + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = raw
        if expected_status is not None and status == expected_status:
            return status, payload
        raise
    if expected_status is not None and status != expected_status:
        raise AssertionError(f"期望 HTTP {expected_status}，实际 {status}: {payload}")
    return status, payload


def http_delete(base: str, path: str, *, expected_status: int = 204) -> int:
    req = urllib.request.Request(base + path, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
        if status != expected_status:
            raise
        return status
    if status != expected_status:
        raise AssertionError(f"期望 HTTP {expected_status}，实际 {status}")
    return status


def parse_sse_events(raw: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    event_name = "message"
    for line in raw.split("\n"):
        line = line.strip("\r")
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("data:"):
            data = json.loads(line[5:].strip())
            events.append((event_name, data))
    return events


def http_sse_chat(base: str, session_id: str, message: str) -> list[tuple[str, dict]]:
    body = json.dumps({"session_id": session_id, "message": message}).encode("utf-8")
    req = urllib.request.Request(
        base + "/api/chat",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        raw = resp.read().decode("utf-8")
    return parse_sse_events(raw)


def run_tests(base: str) -> TestResult:
    result = TestResult()
    print(f"\n{'=' * 60}\n阶段3 接口测试 — {base}\n{'=' * 60}")

    # 1. Health
    print("\n[1] 探活 /api/health")
    try:
        status, data = http_json(base, "GET", "/api/health")
        if status == 200 and data.get("version") == "0.2.0" and data.get("phase") == 3:
            result.ok("GET /api/health 返回 0.2.0 phase3")
        else:
            result.fail("GET /api/health", f"响应异常: {data}")
    except Exception as e:  # noqa: BLE001
        result.fail("GET /api/health", str(e))
        return result

    # 2. Sessions CRUD
    print("\n[2] 会话 CRUD /api/sessions")
    session_id: str | None = None
    try:
        status, sess = http_json(base, "POST", "/api/sessions", {"title": "接口测试会话"}, expected_status=201)
        session_id = sess["id"]
        if not session_id:
            result.fail("POST /api/sessions", "未返回 id")
        else:
            result.ok("POST /api/sessions 创建会话")

        status, sessions = http_json(base, "GET", "/api/sessions")
        if status == 200 and any(s["id"] == session_id for s in sessions):
            result.ok("GET /api/sessions 列表包含新会话")
        else:
            result.fail("GET /api/sessions", "列表中找不到新会话")

        status, one = http_json(base, "GET", f"/api/sessions/{session_id}")
        if status == 200 and one["id"] == session_id:
            result.ok("GET /api/sessions/{id} 获取详情")
        else:
            result.fail("GET /api/sessions/{id}", str(one))

        status, msgs = http_json(base, "GET", f"/api/sessions/{session_id}/messages")
        if status == 200 and msgs == []:
            result.ok("GET /api/sessions/{id}/messages 初始为空")
        else:
            result.fail("GET /api/sessions/{id}/messages", str(msgs))

        try:
            http_json(base, "GET", "/api/sessions/not-exist-id", expected_status=404)
            result.ok("GET /api/sessions/{id} 不存在返回 404")
        except Exception as e:  # noqa: BLE001
            result.fail("GET /api/sessions/{id} 404", str(e))

    except Exception as e:  # noqa: BLE001
        result.fail("会话 CRUD", str(e))
        return result

    assert session_id

    # 3. Chat SSE — NL → SQL → result → token → chart → done
    print("\n[3] SSE 问答 /api/chat")
    try:
        events = http_sse_chat(
            base,
            session_id,
            "统计每个城市的客户数量，按数量从高到低排序",
        )
        types = [data.get("type") for _, data in events]
        event_names = [name for name, _ in events]

        if "sql" in types:
            sql_evt = next(data for _, data in events if data.get("type") == "sql")
            sql = sql_evt.get("sql", "")
            if sql.upper().strip().startswith("SELECT") and "customers" in sql.lower():
                result.ok("SSE sql 事件含合法 SELECT")
            else:
                result.fail("SSE sql", sql)
        else:
            result.fail("SSE sql 事件", f"未收到，事件序列: {types}")

        if "result" in types:
            res = next(data for _, data in events if data.get("type") == "result")
            if res.get("columns") and res.get("rows") is not None:
                result.ok(f"SSE result 事件含 columns/rows (row_count={res.get('row_count')})")
            else:
                result.fail("SSE result", str(res))
        else:
            result.fail("SSE result 事件", f"未收到，事件序列: {types}")

        if "token" in types:
            token = next(data for _, data in events if data.get("type") == "token")
            if token.get("content"):
                result.ok("SSE token 事件含 content")
            else:
                result.fail("SSE token", str(token))
        else:
            result.fail("SSE token 事件", f"未收到，事件序列: {types}")

        if "chart" in types:
            chart = next(data for _, data in events if data.get("type") == "chart")
            option = chart.get("option") or {}
            if isinstance(option, dict) and ("series" in option or "title" in option):
                result.ok("SSE chart 事件含 ECharts option")
            else:
                result.fail("SSE chart", str(chart))
        else:
            result.fail("SSE chart 事件", f"未收到，事件序列: {types}")

        if types[-1] == "done":
            result.ok("SSE 以 done 事件结束")
        else:
            result.fail("SSE done", f"末事件为 {types[-1] if types else '无'}")

        # 事件顺序：sql 在 result 前，result 在 token 前
        if types.index("sql") < types.index("result") < types.index("token"):
            result.ok("SSE 事件顺序 sql → result → token")
        else:
            result.fail("SSE 事件顺序", str(types))

        if event_names and all(n in ("sql", "result", "token", "chart", "done", "error") for n in event_names):
            result.ok("SSE event 名称合法")
        else:
            result.fail("SSE event 名称", str(event_names))

    except Exception as e:  # noqa: BLE001
        result.fail("POST /api/chat SSE", str(e))

    # 4. 消息持久化
    print("\n[4] 消息持久化")
    try:
        _, msgs = http_json(base, "GET", f"/api/sessions/{session_id}/messages")
        roles = [m["role"] for m in msgs]
        if "user" in roles and "assistant" in roles:
            result.ok("消息已持久化（含 user + assistant）")
        else:
            result.fail("消息持久化", str(msgs))

        assistant = next((m for m in msgs if m["role"] == "assistant"), None)
        if assistant and assistant.get("sql"):
            result.ok("assistant 消息含 sql 字段")
        else:
            result.fail("assistant sql 字段", str(assistant))

        _, sess = http_json(base, "GET", f"/api/sessions/{session_id}")
        if sess.get("chartOption"):
            result.ok("会话 chartOption 已更新")
        else:
            result.fail("chartOption", "为空")

    except Exception as e:  # noqa: BLE001
        result.fail("消息持久化", str(e))

    # 5. 上下文记忆（第二轮）
    print("\n[5] 上下文记忆（多轮对话）")
    try:
        events2 = http_sse_chat(base, session_id, "刚才结果里客户最多的城市是哪个？")
        types2 = [data.get("type") for _, data in events2]
        if "done" in types2 and "error" not in types2:
            result.ok("第二轮对话 SSE 正常结束")
        else:
            result.fail("第二轮对话", str(types2))

        _, msgs2 = http_json(base, "GET", f"/api/sessions/{session_id}/messages")
        if len(msgs2) >= 4:
            result.ok(f"多轮消息已累积 (共 {len(msgs2)} 条可见消息)")
        else:
            result.fail("多轮消息数量", str(len(msgs2)))

    except Exception as e:  # noqa: BLE001
        result.fail("上下文记忆", str(e))

    # 6. 错误用例
    print("\n[6] 错误用例")
    try:
        events_err = http_sse_chat(base, "00000000-0000-0000-0000-000000000000", "测试")
        if any(data.get("type") == "error" for _, data in events_err):
            result.ok("不存在 session_id 返回 error 事件")
        else:
            result.fail("不存在 session_id", str(events_err))
    except Exception as e:  # noqa: BLE001
        result.fail("不存在 session_id", str(e))

    # 7. 删除会话
    print("\n[7] 删除会话")
    try:
        http_delete(base, f"/api/sessions/{session_id}")
        result.ok("DELETE /api/sessions/{id} 返回 204")
        try:
            http_json(base, "GET", f"/api/sessions/{session_id}", expected_status=404)
            result.ok("删除后 GET 返回 404")
        except Exception as e:  # noqa: BLE001
            result.fail("删除后 GET", str(e))
    except Exception as e:  # noqa: BLE001
        result.fail("DELETE /api/sessions/{id}", str(e))

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="阶段3 接口集成测试")
    parser.add_argument("--base", default="http://127.0.0.1:8000", help="API 根地址")
    args = parser.parse_args()

    result = run_tests(args.base.rstrip("/"))

    print(f"\n{'=' * 60}")
    print(f"通过: {len(result.passed)}  失败: {len(result.failed)}")
    if result.failed:
        print("\n失败详情:")
        for item in result.failed:
            print(f"  - {item}")
    print("=" * 60)

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
