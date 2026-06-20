#!/usr/bin/env python3
"""
把 extract_comments.py 产出的 comments.json 切成若干小批次文件，
便于 Claude 分批翻译（避免一次性处理过多内容）。

用法:
    python3 split_comments.py <comments.json> <输出目录> [--size 100]

输出: <输出目录>/batch_001.json, batch_002.json, ...
每个文件是一个数组，元素结构与 comments.json 相同（含 id / source 等字段）。
翻译时只需把每个元素的 source 翻译后填到 target 字段。
"""

import argparse
import json
import math
import os
import sys


def main():
    ap = argparse.ArgumentParser(description="切分 comments.json 为小批次")
    ap.add_argument("comments_json", help="extract_comments.py 的输出")
    ap.add_argument("out_dir", help="输出目录")
    ap.add_argument("--size", type=int, default=100, help="每批条数，默认 100")
    args = ap.parse_args()

    with open(args.comments_json, "r", encoding="utf-8") as f:
        comments = json.load(f)

    os.makedirs(args.out_dir, exist_ok=True)
    n_batches = max(1, math.ceil(len(comments) / args.size))
    width = max(3, len(str(n_batches)))

    for b in range(n_batches):
        chunk = comments[b * args.size : (b + 1) * args.size]
        # 为每个元素初始化空的 target 字段
        for c in chunk:
            c.setdefault("target", "")
        out_path = os.path.join(args.out_dir, f"batch_{b + 1:0{width}d}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False, indent=1)

    print(f"共 {len(comments)} 条注释，切成 {n_batches} 批（每批 ≤ {args.size} 条）")
    print(f"输出目录: {args.out_dir}")


if __name__ == "__main__":
    main()
