import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

import requests


NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = "d698aeed-cb97-46fd-aa0c-de95cd87da38"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "src" / "content" / "photos.json"
IMAGE_DIR = PROJECT_ROOT / "public" / "images" / "photos"

if not NOTION_TOKEN:
    raise RuntimeError("没有找到环境变量 NOTION_TOKEN")


HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def notion_request(method, url, **kwargs):
    response = requests.request(
        method,
        url,
        headers=HEADERS,
        timeout=30,
        **kwargs,
    )

    if not response.ok:
        print(f"Notion API 请求失败：{response.status_code}")
        print(response.text[:2000])

    response.raise_for_status()
    return response.json()


def query_all_pages():
    """查询数据库中的全部页面，支持分页"""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    pages = []
    payload = {}

    while True:
        data = notion_request("POST", url, json=payload)
        pages.extend(data.get("results", []))

        if not data.get("has_more"):
            break

        payload["start_cursor"] = data.get("next_cursor")

    return pages


def get_page_blocks(page_id):
    """获取页面正文中的全部 Block，支持分页"""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"

    blocks = []
    params = {"page_size": 100}

    while True:
        data = notion_request("GET", url, params=params)
        blocks.extend(data.get("results", []))

        if not data.get("has_more"):
            break

        params["start_cursor"] = data.get("next_cursor")

    return blocks


def get_title(properties):
    title_property = properties.get("Name", {})
    title_items = title_property.get("title", [])

    if not title_items:
        return "未命名照片"

    title = "".join(
        item.get("plain_text", "")
        for item in title_items
    ).strip()

    return title or "未命名照片"


def get_date(properties):
    date_property = properties.get("Created", {})
    date_data = date_property.get("date")

    if date_data:
        return date_data.get("start", "")

    return ""


def get_location(properties):
    location_property = properties.get("Location", {})
    location_data = location_property.get("select")

    if location_data:
        return location_data.get("name", "")

    return ""


def get_image_url(image_data):
    image_type = image_data.get("type")

    if image_type == "file":
        return image_data.get("file", {}).get("url", "")

    if image_type == "external":
        return image_data.get("external", {}).get("url", "")

    return ""


def find_images_in_blocks(blocks):
    """提取当前页面正文中的图片"""
    image_urls = []

    for block in blocks:
        if block.get("type") != "image":
            continue

        image_data = block.get("image", {})
        image_url = get_image_url(image_data)

        if image_url:
            image_urls.append(image_url)

    return image_urls


def get_file_extension(url, response):
    """根据响应类型或 URL 获取图片扩展名"""
    content_type = response.headers.get("Content-Type", "").split(";")[0].lower()

    extension = mimetypes.guess_extension(content_type)

    if extension in [".jpe", ".jpeg"]:
        return ".jpg"

    if extension:
        return extension

    url_path = urlparse(url).path.lower()
    url_extension = Path(url_path).suffix

    if url_extension in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"]:
        return ".jpg" if url_extension == ".jpeg" else url_extension

    return ".jpg"


def download_image(image_url, image_number):
    """下载图片到 public/images/photos/"""
    response = requests.get(image_url, timeout=60)
    response.raise_for_status()

    extension = get_file_extension(image_url, response)
    filename = f"{image_number:04d}{extension}"
    output_path = IMAGE_DIR / filename

    with output_path.open("wb") as file:
        file.write(response.content)

    print(f"已下载：{output_path}")

    return f"/images/photos/{filename}"


def main():
    pages = query_all_pages()

    print(f"数据库返回 {len(pages)} 个页面")

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    photos = []
    image_number = 1

    for index, page in enumerate(pages, start=1):
        page_id = page.get("id")
        properties = page.get("properties", {})

        title = get_title(properties)
        date = get_date(properties)
        location = get_location(properties)

        try:
            blocks = get_page_blocks(page_id)
            image_urls = find_images_in_blocks(blocks)
        except Exception as error:
            print(f"读取页面失败：{title}，原因：{error}")
            continue

        if not image_urls:
            print(f"[{index}/{len(pages)}] 没有找到图片：{title}")
            continue

        downloaded_count = 0

        for image_url in image_urls:
            try:
                local_url = download_image(image_url, image_number)

                photos.append({
                    "title": title,
                    "url": local_url,
                    "date": date,
                    "location": location,
                })

                image_number += 1
                downloaded_count += 1

            except Exception as error:
                print(f"下载图片失败：{title}，原因：{error}")

        print(
            f"[{index}/{len(pages)}] "
            f"{title}：下载 {downloaded_count} 张图片"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(photos, file, ensure_ascii=False, indent=2)

    print(f"✅ 成功！下载了 {len(photos)} 张照片")
    print(f"✅ JSON 已保存到：{OUTPUT_PATH}")
    print(f"✅ 图片已保存到：{IMAGE_DIR}")


if __name__ == "__main__":
    main()
