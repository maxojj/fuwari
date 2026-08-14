import requests
import json
import os
import random
from datetime import datetime

TOKEN = os.getenv("NEODB_TOKEN")
OUTPUT_PATH = "src/content/movies.json"

# 电影和电视剧合计取最近的 50 条
MAX_ITEMS = 50

# NeoDB 的分类参数
CATEGORIES = ["movie", "tv"]

API_URL = "https://neodb.social/api/me/shelf/complete"


def parse_created_time(value):
    if not value:
        return 0

    try:
        value = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return 0


def get_year(item):
    year = item.get("year_released")

    if year:
        return str(year)

    pubdate = item.get("pubdate") or []

    if isinstance(pubdate, list):
        for value in pubdate:
            if value:
                return str(value)[:4]

    if isinstance(pubdate, str) and pubdate:
        return pubdate[:4]

    return ""


def get_link(item):
    item_url = item.get("url") or ""

    if not item_url:
        return ""

    if item_url.startswith("http://") or item_url.startswith("https://"):
        return item_url

    return f"https://neodb.social{item_url}"


def fetch_category(category):
    results = []
    page = 1

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
        "Accept-Language": "zh-cn",
    }

    while len(results) < MAX_ITEMS:
        print(f"正在获取 {category} 第 {page} 页...")

        try:
            response = requests.get(
                API_URL,
                headers=headers,
                params={
                    "category": category,
                    "page": page,
                },
                timeout=20,
            )
            response.raise_for_status()

            data = response.json()
            entries = data.get("data") or []

            if not entries:
                break

            for entry in entries:
                if len(results) >= MAX_ITEMS:
                    break

                item = entry.get("item") or {}
                created_time = entry.get("created_time") or ""

                title = (
                    item.get("display_title")
                    or item.get("title")
                    or "未命名作品"
                )

                result = {
                    "title": title,
                    "poster": item.get("cover_image_url"),
                    "rating": entry.get("rating_grade") or 0,
                    "year": get_year(item),
                    "comment": entry.get("comment_text") or "",
                    "date": str(created_time)[:10] if created_time else "",
                    "link": get_link(item),

                    # 临时字段，只用于最终排序
                    "_created_time": created_time,
                }

                results.append(result)

                print(
                    f"已获取 [{category}]："
                    f"{title} | {result['year'] or 'N/A'} | "
                    f"评分：{result['rating']}"
                )

            page += 1

        except Exception as error:
            print(f"{category} API 请求异常：{error}")
            break

    return results


def get_movies():
    if not TOKEN:
        print("错误：没有找到 NEODB_TOKEN 环境变量")
        return

    print(f"开始抓取 NeoDB 数据，最终取最近 {MAX_ITEMS} 条...")

    all_results = []

    for category in CATEGORIES:
        all_results.extend(fetch_category(category))

    if not all_results:
        print("没有获取到任何数据")
        return

    # 电影和电视剧合并后，按照实际标记时间排序
    all_results.sort(
        key=lambda item: parse_created_time(item["_created_time"]),
        reverse=True,
    )

    # 统一截取最近的前 MAX_ITEMS 条
    results = all_results[:MAX_ITEMS]

    # 删除临时字段，保持原有数据结构完全不变
    for item in results:
        item.pop("_created_time", None)

    # 最终展示时随机排列
    random.shuffle(results)

    output_dir = os.path.dirname(OUTPUT_PATH)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"更新完成，共写入 {len(results)} 条电影/电视剧记录："
        f"{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    get_movies()
