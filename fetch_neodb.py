import requests
import json
import os

# 配置
TOKEN = os.getenv('NEODB_TOKEN')
OUTPUT_PATH = "src/content/movies.json"
MAX_ITEMS = 30  # 你要求的取最新的30条记录

def get_movies():
    results = []
    page = 1
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Accept': 'application/json'
    }

    print("开始从 NeoDB 抓取数据...")

    while len(results) < MAX_ITEMS:
        # 抓取分类为 movie 且状态为 complete (看过) 的条目
        url = f"https://neodb.social/api/me/shelf/complete?category=movie&page={page}"
        
        try:
            res = requests.get(url, headers=headers)
            res.raise_for_status()
            data = res.json()
            
            items = data.get('data', [])
            if not items: # 如果没有更多数据了，跳出循环
                break
                
            for entry in items:
                if len(results) >= MAX_ITEMS:
                    break
                    
                item = entry.get('item', {})
                
                # 提取数据
                movie_info = {
                    "title": item.get('title'),
                    "poster": item.get('cover_image_url'),
                    "rating": entry.get('rating') or 0,      # 打分数据
                    "comment": entry.get('comment') or "",   # 你的评价
                    "date": entry.get('created_time')[:10], # 标记日期
                    "link": f"https://neodb.social{item.get('url')}"
                }
                results.append(movie_info)
            
            print(f"已获取第 {page} 页，当前共 {len(results)} 条记录")
            page += 1 # 翻页
            
        except Exception as e:
            print(f"同步第 {page} 页失败: {e}")
            break
    
    # 保存数据
    if results:
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"任务完成：成功同步最新的 {len(results)} 部电影")

if __name__ == "__main__":
    get_movies()
