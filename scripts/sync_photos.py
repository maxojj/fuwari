import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

import pillow_heif
import requests
from PIL import Image


# 注册 HEIC/HEIF 图片读取支持
pillow_heif.register_heif_opener()


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
    """请求 Notion API，并统一处理错误。"""
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
    """查询数据库中的全部页面，支持分页。"""
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    pages = []
    payload = {}

    while True:
        data = notion_request("POST", url, json=payload)
        pages.extend(data.get("results", []))

        if not data.get("has_more"):
            break

        next_cursor = data.get("next_cursor")

        if not next_cursor:
            break

        payload["start_cursor"] = next_cursor

    return pages


def get_page_blocks(page_id):
    """获取页面正文中的全部 Block，支持分页。"""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"

    blocks = []
    params = {
        "page_size": 100,
    }

    while True:
        data = notion_request("GET", url, params=params)
        blocks.extend(data.get("results", []))

        if not data.get("has_more"):
            break

        next_cursor = data.get("next_cursor")

        if not next_cursor:
            break

        params["start_cursor"] = next_cursor

    return blocks


def get_title(properties):
    """读取 Name 标题属性。"""
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
    """读取 Created 日期属性。"""
    date_property = properties.get("Created", {})
    date_data = date_property.get("date")

    if date_data:
        return date_data.get("start", "")

    return ""


def get_location(properties):
    """读取 Location 地点属性。"""
    location_property = properties.get("Location", {})
    location_data = location_property.get("select")

    if location_data:
        return location_data.get("name", "")

    return ""


def get_image_url(image_data):
    """读取 Notion 图片 Block 的 URL。"""
    image_type = image_data.get("type")

    if image_type == "file":
        return image_data.get("file", {}).get("url", "")

    if image_type == "external":
        return image_data.get("external", {}).get("url", "")

    return ""


def find_images_in_blocks(blocks):
    """提取当前页面正文中的图片。"""
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
    """根据 Content-Type 或 URL 获取图片扩展名。"""
    content_type = response.headers.get(
        "Content-Type",
        "",
    ).split(";")[0].lower()

    extension = mimetypes.guess_extension(content_type)

    if extension in [".jpe", ".jpeg"]:
        return ".jpg"

    if extension:
        return extension

    url_path = urlparse(url).path.lower()
    url_extension = Path(url_path).suffix

    supported_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".avif",
    ]

    if url_extension in supported_extensions:
        if url_extension == ".jpeg":
            return ".jpg"

        return url_extension

    return ".jpg"


def clear_image_directory():
    """清理旧图片，避免残留旧的 HEIC 或无效文件。"""
    if IMAGE_DIR.exists():
        for file in IMAGE_DIR.iterdir():
            if file.is_file():
                file.unlink()

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def download_image(image_url, image_number):
    """
    下载图片到 public/images/photos/。

    HEIC/HEIF 会自动转换为 JPG，
    以确保浏览器能够正常显示。
    """
    response = requests.get(
        image_url,
        timeout=60,
        allow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0",
        },
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type",
        "",
    ).split(";")[0].lower()

    if not content_type.startswith("image/"):
        raise RuntimeError(
            f"返回内容不是图片：Content-Type={content_type}"
        )

    if not response.content:
        raise RuntimeError("图片内容为空")

    # 先写入临时文件，避免下载失败时留下不完整文件
    temp_path = IMAGE_DIR / f".tmp_{image_number}"

    with temp_path.open("wb") as file:
        file.write(response.content)

    # HEIC / HEIF 转换为 JPG
    if content_type in {
        "image/heic",
        "image/heif",
        "image/heic-sequence",
        "image/heif-sequence",
    }:
        filename = f"{image_number:04d}.jpg"
        output_path = IMAGE_DIR / filename

        try:
            with Image.open(temp_path) as image:
                rgb_image = image.convert("RGB")
                rgb_image.save(
                    output_path,
                    "JPEG",
                    quality=92,
                    optimize=True,
                )
        finally:
            temp_path.unlink(missing_ok=True)

        if output_path.stat().st_size < 100:
            output_path.unlink(missing_ok=True)
            raise RuntimeError("HEIC 转换后的 JPG 文件无效")

        print(f"已下载并转换：{output_path}")

        return f"/images/photos/{filename}"

    # 其他常见图片格式
    extension_map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/avif": ".avif",
    }

    extension = extension_map.get(content_type)

    if not extension:
        extension = get_file_extension(image_url, response)

    filename = f"{image_number:04d}{extension}"
    output_path = IMAGE_DIR / filename

    temp_path.rename(output_path)

    # 基本文件大小检查
    if output_path.stat().st_size < 100:
        output_path.unlink(missing_ok=True)
        raise RuntimeError(
            "下载后的文件过小，可能不是有效图片"
        )

    print(f"已下载：{output_path}")

    return f"/images/photos/{filename}"


def main():
    pages = query_all_pages()

    print(f"数据库返回 {len(pages)} 个页面")

    # 每次完整同步前清除旧图片
    clear_image_directory()

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
            print(
                f"读取页面失败：{title}，"
                f"原因：{error}"
            )
            continue

        if not image_urls:
            print(
                f"[{index}/{len(pages)}] "
                f"没有找到图片：{title}"
            )
            continue

        downloaded_count = 0

        for image_url in image_urls:
            try:
                local_url = download_image(
                    image_url,
                    image_number,
                )

                photos.append({
                    "title": title,
                    "url": local_url,
                    "date": date,
                    "location": location,
                })

                image_number += 1
                downloaded_count += 1

            except Exception as error:
                print(
                    f"下载图片失败：{title}，"
                    f"原因：{error}"
                )

        print(
            f"[{index}/{len(pages)}] "
            f"{title}：下载 {downloaded_count} 张图片"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            photos,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"✅ 成功！下载了 {len(photos)} 张照片")
    print(f"✅ JSON 已保存到：{OUTPUT_PATH}")
    print(f"✅ 图片已保存到：{IMAGE_DIR}")


if __name__ == "__main__":
    main()
