import requests
import json
import os

# 基础配置
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
DATABASE_ID = "d698aeedcb9746fdaa0cde95cd87da38" 
OUTPUT_PATH = "src/content/photos.json"

def get_notion_photos():
    if not NOTION_TOKEN:
        print("❌ 错误: 未检测到环境变量 NOTION_TOKEN")
        return

    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    try:
        res = requests.post(url, headers=headers)
        res.raise_for_status()
        data = res.json()
        
        photos = []
        for row in data.get("results", []):
            props = row.get("properties", {})
            
            # 1. 获取标题
            title = "未命名照片"
            for p in props.values():
                if p.get('type') == 'title' and p.get('title'):
                    title = p['title'][0].get('plain_text', "未命名照片")
                    break
            
            # 2. 获取图片
            image_url = ""
            for p in props.values():
                if p.get('type') == 'files' and p.get('files'):
                    file_obj = p['files'][0]
                    image_url = file_obj.get("file", {}).get("url") or file_obj.get("external", {}).get("url")
                    break
            
            # 3. 获取日期
            date_val = ""
            for p in props.values():
                if p.get('type') == 'date' and p.get('date') and p['date']:
                    date_val = p['date'].get('start', "")
                    break

            if image_url:
                photos.append({
                    "title": title,
                    "url": image_url,
                    "date": date_val
                })

        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(photos, f, ensure_ascii=False, indent=2)
        print(f"✅ 成功! 抓取了 {len(photos)} 张照片到 {OUTPUT_PATH}")

    except Exception as e:
        print(f"❌ 失败: {e}")

if __name__ == "__main__":
    get_notion_photos()
