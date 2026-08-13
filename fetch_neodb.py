import requests
import json
import os

TOKEN = os.getenv('NEODB_TOKEN')
OUTPUT_PATH = "src/content/movies.json"
MAX_ITEMS = 30 

def get_movies():
    results = []
    page = 1
    # 按照开发文档，我们保持 headers 规范
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Accept': 'application/json',
        # 强制请求中文环境
        'Accept-Language': 'zh-cn'
    }

    print("开始从 NeoDB 抓取数据...")

    while len(results) < MAX_ITEMS:
        # 文档路径: /api/me/shelf/complete
        url = f"https://neodb.social/api/me/shelf/complete?category=movie&page={page}"
        
        try:
            res = requests.get(url, headers=headers)
            res.raise_for_status()
            data = res.json()
            
            # data 包含 'data', 'pages', 'count'
            entries = data.get('data', [])
            if not entries:
                break
                
            for entry in entries:
                if len(results) >= MAX_ITEMS:
                    break
                
                item = entry.get('item', {})
                
                # 1. 标题逻辑：优先显示标题，如果 API 没给中文，我们取 title
                title = item.get('display_title') or item.get('title')
                
                # 2. 评分逻辑：根据文档，标记对象的评分字段是 rating_grade
                rating = entry.get('rating_grade') or 0
                
                # 3. 评论逻辑：文档明确指出是 comment_text
                comment = entry.get('comment_text') or ""

                print(f"成功获取: {title} | 评分: {rating} | 评论长度: {len(comment)}")

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
            print(f"API请求异常: {e}")
            break
    
    if results:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"更新完成，最新 {len(results)} 条数据已存入 {OUTPUT_PATH}")

if __name__ == "__main__":
    get_movies()
