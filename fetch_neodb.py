import requests
import json
import os

TOKEN = os.getenv('NEODB_TOKEN')
OUTPUT_PATH = "src/content/movies.json"
MAX_ITEMS = 30 

def get_movies():
    results = []
    page = 1
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Accept': 'application/json'
    }

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
                
                # 核心：电影详情在 item 里
                item = entry.get('item', {})
                
                # 1. 拿中文名：优先取 display_title，没有就取 title
                title = item.get('display_title') or item.get('title')
                
                # 2. 拿评分：NeoDB API 的评分字段是 rating-grade 或 rating
                rating = entry.get('rating-grade') or entry.get('rating') or 0
                
                # 3. 拿评论：评论字段是 comment_text 或 comment
                comment = entry.get('comment_text') or entry.get('comment') or ""
                
                # 打印日志方便我们验证
                print(f"抓取成功: {title} | 评分: {rating} | 评论长度: {len(comment)}")

                results.append({
                    "title": title,
                    "poster": item.get('cover_image_url'),
                    "rating": rating,
                    "comment": comment,
                    "date": entry.get('created_time')[:10] if entry.get('created_time') else "",
                    "link": f"https://neodb.social{item.get('url')}"
                })
            
            page += 1
            
        except Exception as e:
            print(f"同步失败: {e}")
            break
    
    if results:
        # 必须确保目录存在
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"任务完成：成功同步 {len(results)} 条数据到 {OUTPUT_PATH}")

if __name__ == "__main__":
    get_movies()
