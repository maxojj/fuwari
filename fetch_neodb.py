import requests
import json
import os
import random

TOKEN = os.getenv('NEODB_TOKEN')
OUTPUT_PATH = "src/content/movies.json"
MAX_ITEMS = 50  # 调整为 50 条

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
                
                # 1. 提取标题
                title = item.get('display_title') or item.get('title')
                
                # 2. 提取评分 (rating_grade)
                rating = entry.get('rating_grade') or 0
                
                # 3. 提取年份 (year)
                year = item.get('year') or ""
                
                # 4. 提取评论 (comment_text)
                comment = entry.get('comment_text') or ""

                print(f"成功抓取: {title} | 评分: {rating} | 年份: {year}")

                results.append({
                    "title": title,
                    "poster": item.get('cover_image_url'),
                    "rating": rating, # 重新加入评分字段
                    "year": year,     # 加入年份字段
                    "comment": comment,
                    "date": entry.get('created_time')[:10] if entry.get('created_time') else "",
                    "link": f"https://neodb.social{item.get('url')}"
                })
            
            page += 1
            
        except Exception as e:
            print(f"API请求异常: {e}")
            break
    
    if results:
        # 在保存前进行随机乱序处理
        random.shuffle(results)
        
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"更新完成，已随机打乱并存入 {len(results)} 条数据到 {OUTPUT_PATH}")

if __name__ == "__main__":
    get_movies()
