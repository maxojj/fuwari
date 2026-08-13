import requests
import json
import os

# 从 GitHub Secrets 读取 Token，保护隐私
TOKEN = os.getenv('NEODB_TOKEN')
# TODO: 填入你的 NeoDB 用户名
USER_ID = "Van_Debiao" 
OUTPUT_PATH = "src/content/movies.json"

def get_movies():
    # 抓取分类为 movie 且状态为 complete (看过) 的条目
    url = f"https://neodb.social/api/me/shelf/complete?category=movie"
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Accept': 'application/json'
    }
    
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        data = res.json()
        
        results = []
        for entry in data.get('data', []):
            item = entry.get('item', {})
            results.append({
                "title": item.get('title'),
                "poster": item.get('cover_image_url'),
                "rating": entry.get('rating') or "未打分",
                "date": entry.get('created_time')[:10],
                "link": f"https://neodb.social{item.get('url')}"
            })
        
        # 确保目录存在
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        print(f"成功更新 {len(results)} 部电影数据")
    except Exception as e:
        print(f"同步失败: {e}")

if __name__ == "__main__":
    get_movies()
