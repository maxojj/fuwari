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
        # 使用 shelf/complete 接口获取“看过”列表
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
                
                # entry 包含你的交互数据（评分、评价）
                # item 包含电影本身的数据（标题、海报）
                item = entry.get('item', {})
                
                # 提取评分：NeoDB API 中 rating 通常直接在 entry 下
                rating = entry.get('rating')
                # 提取评价：NeoDB API 中评论字段可能是 comment 或内容描述
                comment = entry.get('comment') or ""
                
                # 提取标题：优先取 item 里的 title，这通常是 NeoDB 存储的中文名
                title = item.get('title')
                
                # 打印一条日志到 GitHub Actions 控制台，方便调试
                print(f"成功抓取: {title} | 评分: {rating} | 评论长度: {len(comment)}")

                results.append({
                    "title": title,
                    "poster": item.get('cover_image_url'),
                    "rating": rating if rating else 0,
                    "comment": comment,
                    "date": entry.get('created_time')[:10] if entry.get('created_time') else "",
                    "link": f"https://neodb.social{item.get('url')}"
                })
            
            page += 1
            
        except Exception as e:
            print(f"抓取失败: {e}")
            break
    
    if results:
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"任务完成：成功同步 {len(results)} 条数据到 {OUTPUT_PATH}")

if __name__ == "__main__":
    get_movies()
