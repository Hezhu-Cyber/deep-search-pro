"""轻量 Agent 评估：跑一批基准问题并统计关键词覆盖率。

用法（需要先配置 .env 中的 LLM 与 Tavily Key）：
    python evals/run_eval.py             # 运行全部基准问题
    python evals/run_eval.py --limit 3   # 只运行前 3 条
    python evals/run_eval.py --task r1   # 只运行指定问题

说明：
    - 结果写入 evals/reports/<时间戳>.json（该目录已被 gitignore）。
    - 关键词覆盖率是廉价回归指标，适合 prompt / 模型迭代时做快速对比。
"""
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from api import monitor  # noqa: E402
from agent.main_agent import run_deep_agent  # noqa: E402


def load_dataset() -> list[dict]:
    path = PROJECT_ROOT / "evals" / "dataset.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def score_result(result: str, expects: list[str]) -> dict:
    lowered = (result or "").lower()
    hits = {kw: (kw.lower() in lowered) for kw in expects}
    return {"hits": hits, "covered": sum(hits.values()), "total": len(expects)}


async def run_case(case: dict, collected: list[dict]) -> None:
    """运行单个用例，通过替换 report_task_result 捕获最终结果文本。"""
    tid = f"eval-{case['id']}"

    def capture(result: str) -> None:
        collected.append({"id": case["id"], "result": result})

    original = monitor.monitor.report_task_result
    monitor.monitor.report_task_result = capture  # type: ignore[method-assign]
    try:
        await run_deep_agent(case["task"], tid)
    finally:
        monitor.monitor.report_task_result = original


async def main(limit: int | None, only: str | None) -> None:
    cases = load_dataset()
    if only:
        cases = [c for c in cases if c["id"] == only]
    if limit:
        cases = cases[:limit]

    print(f"== Deep Search Pro Eval ==  共 {len(cases)} 条用例\n")
    rows = []
    for case in cases:
        collected: list[dict] = []
        start = time.time()
        try:
            await run_case(case, collected)
        except Exception as exc:  # noqa: BLE001
            print(f"[{case['id']}] 运行异常: {exc}")
            rows.append({"id": case["id"], "task": case["task"], "error": str(exc)})
            continue
        elapsed = round(time.time() - start, 1)
        rec = collected[-1] if collected else {}
        result = rec.get("result", "")
        score = score_result(result, case["expects"])
        coverage = round(score["covered"] / max(score["total"], 1) * 100)
        rows.append(
            {
                "id": case["id"],
                "task": case["task"],
                "coverage": coverage,
                "hits": score["hits"],
                "length": len(result),
                "elapsed_s": elapsed,
            }
        )
        print(
            f"[{case['id']}] 覆盖率 {coverage:3d}%  | 命中 {score['covered']}/{score['total']}  | 长度 {len(result)}  | {elapsed}s"
        )

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total": len(rows),
            "avg_coverage": round(sum(r.get("coverage", 0) for r in rows) / max(len(rows), 1)),
        },
        "rows": rows,
    }
    out_dir = PROJECT_ROOT / "evals" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"eval-{datetime.now():%Y%m%d-%H%M%S}.json"
    out_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n平均覆盖率: {report['summary']['avg_coverage']}%")
    print(f"报告已写入: {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deep Search Pro 轻量评估")
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 条")
    parser.add_argument("--task", type=str, default=None, help="只跑指定 id")
    args = parser.parse_args()
    asyncio.run(main(args.limit, args.task))