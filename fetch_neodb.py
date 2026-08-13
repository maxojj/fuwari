import requests
import json
import os

TOKEN = os.getenv('NEODB_TOKEN')
OUTPUT_PATH = "src/content/movies.json"
MAX_ITEMS = 50  # 改为最近 50 条

def get_movies():
    results = []
    page = 1
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Accept': 'application/json',
        'Accept-Language': 'zh-cn'
    }

    print("开始从 NeoDB 抓取最近 50 条电影数据...")

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
                
                title = item.get('display_title') or item.get('title')
                comment = entry.get('comment_text') or ""
                
                # 获取年份逻辑
                year = item.get('year') or ""

                print(f"成功获取: {title} | 年份: {year}")

                results.append({
                    "title": title,
                    "poster": item.get('cover_image_url'),
                    "year": year, # 保存年份
                    "comment": comment,
                    "date": entry.get('created_time')[:10] if entry.get('created_time') else "",
                    "link": f"https://neodb.social{item.get('url')}"
                })
            
            page += 1
            
        except Exception as e:
            print(f"API请求异常: {e}")
            break
    
    if results:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"更新完成，最新 {len(results)} 条数据已存入 {OUTPUT_PATH}")

if __name__ == "__main__":
    get_movies()
