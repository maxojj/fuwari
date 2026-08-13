import requests
import json
import os

# 从 GitHub Secrets 获取 Token
TOKEN = os.getenv("NEODB_TOKEN")
API_BASE = "https://neodb.social/api/v1"

def fetch_movies():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    # 这里的 category=movie 表示电影，shelf=complete 表示看过
    url = f"{API_BASE}/me/shelf/item?category=movie&shelf=complete"
    
    print("正在从 NeoDB 获取数据...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"无法获取数据，错误码: {response.status_code}")
        print(f"响应内容: {response.text}")
        return

    data = response.json().get("data", [])
    movie_list = []

    for item in data:
        movie = item.get("item", {})
        movie_list.append({
            "title": movie.get("title"),
            "poster": movie.get("cover_image_url"),
            "rating": item.get("rating"),
            "comment": item.get("comment"),
            "date": item.get("created_time")[:10],
            "link": f"https://neodb.social{movie.get('url')}"
        })

    # 确保目录存在
    os.makedirs("src/content", exist_ok=True)
    
    # 写入文件
    with open("src/content/movies.json", "w", encoding="utf-8") as f:
        json.dump(movie_list, f, ensure_ascii=False, indent=2)
    
    print(f"成功抓取 {len(movie_list)} 部电影并保存到 src/content/movies.json")

if __name__ == "__main__":
    fetch_movies()
