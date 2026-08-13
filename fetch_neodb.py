import requests
import json
import os

TOKEN = os.getenv('NEODB_TOKEN')
OUTPUT_PATH = "src/content/movies.json"
MAX_ITEMS = 30 

def get_movies():
    results = []
    page = 1
    headers = {'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/json'}

    print("开始从 NeoDB 抓取数据...")

    while len(results) < MAX_ITEMS:
        url = f"https://neodb.social/api/me/shelf/complete?category=movie&page={page}"
        try:
            res = requests.get(url, headers=headers)
            res.raise_for_status()
            data = res.json()
            items = data.get('data', [])
            if not items:
                break
                
            for entry in items:
                if len(results) >= MAX_ITEMS:
                    break
                
                item = entry.get('item', {})
                
                # --- 1. 尝试所有可能的中文标题字段 ---
                # NeoDB API 可能会根据你的账号语言返回本地化标题
                title = item.get('display_title') or item.get('localized_title') or item.get('title')
                
                # --- 2. 尝试所有可能的评分字段 ---
                # 某些版本 API 叫 rating，某些叫 rating_grade
                rating = entry.get('rating') or entry.get('rating_grade') or entry.get('grade') or 0
                
                # --- 3. 评论字段 ---
                comment = entry.get('comment_text') or entry.get('comment') or ""

                # --- 调试打印：只打印第一条数据的原始键名，帮助定位 ---
                if len(results) == 0:
                    print(f"DEBUG - entry 包含的键: {list(entry.keys())}")
                    print(f"DEBUG - item 包含的键: {list(item.keys())}")

                print(f"抓取成功: {title} | 评分: {rating} | 评论长度: {len(comment)}")

                results.append({
                    "title": title,
                    "poster": item.get('cover_image_url'),
                    "rating": float(rating) if rating else 0,
                    "comment": comment,
                    "date": entry.get('created_time')[:10] if entry.get('created_time') else "",
                    "link": f"https://neodb.social{item.get('url')}"
                })
            page += 1
        except Exception as e:
            print(f"抓取失败: {e}")
            break
    
    if results:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"任务完成：成功同步 {len(results)} 条数据")

if __name__ == "__main__":
    get_movies()
