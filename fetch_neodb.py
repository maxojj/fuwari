import requests
import json
import os
import random
import time

TOKEN = os.getenv("NEODB_TOKEN")
OUTPUT_PATH = "src/content/movies.json"

# 电影 + 电视剧合计最多抓取数量
MAX_ITEMS = 50

# NeoDB 分类
CATEGORIES = ["movie", "tv"]


def get_movies():
    if not TOKEN:
        print("错误：没有找到 NEODB_TOKEN 环境变量")
        return

    results = []

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json",
        "Accept-Language": "zh-cn",
    }

    print(
        f"开始抓取 NeoDB 数据，类型：电影 + 电视剧，目标：{MAX_ITEMS} 条..."
    )

    # 依次抓取电影和电视剧
    for category in CATEGORIES:
        if len(results) >= MAX_ITEMS:
            break

        page = 1

        print(f"\n开始抓取分类：{category}")

        while len(results) < MAX_ITEMS:
            url = (
                "https://neodb.social/api/me/shelf/complete"
                f"?category={category}&page={page}"
            )

            try:
                res = requests.get(
                    url,
                    headers=headers,
                    timeout=20,
                )
                res.raise_for_status()

                data = res.json()
                entries = data.get("data", [])

                if not entries:
                    print(f"{category} 没有更多数据")
                    break

                for entry in entries:
                    if len(results) >= MAX_ITEMS:
                        break

                    item = entry.get("item") or {}

                    # 标题
                    title = (
                        item.get("display_title")
                        or item.get("title")
                        or "未命名"
                    )

                    # NeoDB 标记对象的评分
                    rating = entry.get("rating_grade") or 0

                    # 年份
                    year = item.get("year_released")

                    if not year:
                        pubdate = item.get("pubdate") or []

                        if isinstance(pubdate, list) and pubdate:
                            first_date = str(pubdate[0])
                            year = first_date[:4]

                        elif isinstance(pubdate, str) and pubdate:
                            year = pubdate[:4]

                    # 评论
                    comment = entry.get("comment_text") or ""

                    # 标记日期
                    created_time = entry.get("created_time") or ""
                    date = str(created_time)[:10] if created_time else ""

                    # NeoDB 页面链接
                    item_url = item.get("url") or ""

                    if item_url.startswith("http"):
                        link = item_url
                    else:
                        link = f"https://neodb.social{item_url}"

                    movie = {
                        "title": title,
                        "poster": item.get("cover_image_url"),
                        "rating": rating,
                        "year": str(year) if year else "",
                        "comment": comment,
                        "date": date,
                        "link": link,
                    }

                    results.append(movie)

                    print(
                        f"已抓取 [{category}]: "
                        f"{title} | 年份: {year or 'N/A'} | 评分: {rating}"
                    )

                page += 1

                # 避免请求过快
                time.sleep(0.2)

            except requests.RequestException as e:
                print(f"{category} API 请求异常：{e}")
                break

            except ValueError as e:
                print(f"{category} JSON 解析异常：{e}")
                break

            except Exception as e:
                print(f"{category} 数据处理异常：{e}")
                break

    if not results:
        print("没有获取到任何 NeoDB 数据")
        return

    # 保存前随机乱序
    random.shuffle(results)

    output_dir = os.path.dirname(OUTPUT_PATH)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"\n更新完成，共获取 {len(results)} 条数据，"
        f"已保存至：{OUTPUT_PATH}"
    )


if __name__ == "__main__":
    get_movies()
