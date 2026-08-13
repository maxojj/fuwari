import requests
import json
import os
import random

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

    print(f"开始抓取 NeoDB 数据 (目标: {MAX_ITEMS} 条)...")

    while len(results) < MAX_ITEMS:
        # 电影完成列表 API
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
                
                # 1. 标题 (display_title 是 NeoDB 推荐的本地化标题)
                title = item.get('display_title') or item.get('title')
                
                # 2. 评分 (NeoDB 标记对象的评分)
                rating = entry.get('rating_grade') or 0
                
                # 3. 关键：年份字段。NeoDB 电影模型中使用 year_released
                # 如果 year_released 依然没有，则尝试取 pubdate 的年份
                year = item.get('year_released')
                if not year and item.get('pubdate'):
                    pub_list = item.get('pubdate', [])
                    if pub_list:
                        # 提取第一个日期的前四位
                        year = pub_list[0][:4]
                
                # 4. 评论
                comment = entry.get('comment_text') or ""

                print(f"已抓取: {title} | 年份: {year or 'N/A'} | 评分: {rating}")

                results.append({
                    "title": title,
                    "poster": item.get('cover_image_url'),
                    "rating": rating,
                    "year": str(year) if year else "", # 确保是字符串
                    "comment": comment,
                    "date": entry.get('created_time')[:10] if entry.get('created_time') else "",
                    "link": f"https://neodb.social{item.get('url')}"
                })
            
            page += 1
            
        except Exception as e:
            print(f"API请求异常: {e}")
            break
    
    if results:
        # 保存前随机乱序
        random.shuffle(results)
        
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"更新完成，最新 {len(results)} 条数据已存入 {OUTPUT_PATH}")

if __name__ == "__main__":
    get_movies()
