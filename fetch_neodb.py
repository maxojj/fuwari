import requests
import json
import os
import random
import re

TOKEN = os.getenv('NEODB_TOKEN')
OUTPUT_PATH = "src/content/movies.json"
MAX_ITEMS = 50 

def get_movies():
    results = []
    page = 1
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Accept': 'application/json',
        'Accept-Language': 'zh-cn'
    }

    print(f"开始从 NeoDB 抓取数据 (目标: {MAX_ITEMS} 条)...")

    while len(results) < MAX_ITEMS:
        url = f"https://neodb.social/api/me/shelf/complete?category=movie&page={page}"
        
        try:
            res = requests.get(url, headers=headers)
            res.raise_for_status()
            data = res.json()
            
            entries = data.get('data', [])
            if not entries:
                break
                
            for entry in entries:
                if len(results) >= MAX_ITEMS:
                    break
                
                item = entry.get('item', {})
                
                # 1. 标题
                title = item.get('display_title') or item.get('title')
                
                # 2. 评分
                rating = entry.get('rating_grade') or 0
                
                # 3. 解析年份 (NeoDB 的年份通常在 pubdate 数组里)
                year = ""
                pubdates = item.get('pubdate', [])
                if pubdates and len(pubdates) > 0:
                    # 取 pubdate 第一项的前四位数字，如 "2023-11-20" -> "2023"
                    match = re.search(r'\d{4}', pubdates[0])
                    if match:
                        year = match.group()
                
                # 如果 pubdate 没拿到，尝试从 orig_title 拿，例如 "Oppenheimer (2023)"
                if not year:
                    orig_title = item.get('orig_title', '')
                    match = re.search(r'\((\d{4})\)', orig_title)
                    if match:
                        year = match.group(1)

                # 4. 评论
                comment = entry.get('comment_text') or ""

                print(f"成功抓取: {title} | 年份: {year or '未知'} | 评分: {rating}")

                results.append({
                    "title": title,
                    "poster": item.get('cover_image_url'),
                    "rating": rating,
                    "year": year,
                    "comment": comment,
                    "date": entry.get('created_time')[:10] if entry.get('created_time') else "",
                    "link": f"https://neodb.social{item.get('url')}"
                })
            
            page += 1
            
        except Exception as e:
            print(f"API请求异常: {e}")
            break
    
    if results:
        # 随机乱序
        random.shuffle(results)
        
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"更新完成，已随机打乱并存入 {len(results)} 条数据到 {OUTPUT_PATH}")

if __name__ == "__main__":
    get_movies()
