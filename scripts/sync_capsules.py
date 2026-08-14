import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

import requests


NOTION_TOKEN = os.getenv("NOTION_TOKEN")
CAPSULE_DATABASE_ID = "908644799ee341759a3fc9eb73ecff1b"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "src" / "content" / "capsules.json"
IMAGE_DIR = PROJECT_ROOT / "public" / "images" / "capsules"


if not NOTION_TOKEN:
    raise RuntimeError("没有找到环境变量 NOTION_TOKEN")


NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0",
}


def notion_request(method, url, **kwargs):
    """请求 Notion API。"""
    response = requests.request(
        method,
        url,
        headers=NOTION_HEADERS,
        timeout=30,
        **kwargs,
    )

    if not response.ok:
        print(f"Notion API 请求失败：{response.status_code}")
        print(response.text[:2000])

    response.raise_for_status()
    return response.json()


def query_all_pages():
    """查询数据库中的全部页面，不进行 Published 筛选。"""
    url = (
        "https://api.notion.com/v1/databases/"
        f"{CAPSULE_DATABASE_ID}/query"
    )

    pages = []
    payload = {
        "page_size": 100,
    }

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


def get_all_blocks(block_id):
    """获取页面或 Block 下的全部子 Block，支持分页。"""
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"

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


def get_rich_text_text(rich_text):
    """获取 Notion rich_text 的纯文本内容。"""
    return "".join(
        item.get("plain_text", "")
        for item in rich_text
    )


def get_rich_text_children(rich_text):
    """
    将 Notion rich_text 转换为页面可展示的 children。

    普通文字：
    {
        "type": "text",
        "text": "内容"
    }

    链接文字：
    {
        "type": "link",
        "text": "链接文字",
        "url": "https://example.com"
    }
    """
    children = []

    for item in rich_text:
        plain_text = item.get("plain_text", "")
        item_type = item.get("type")

        if item_type == "text":
            text_data = item.get("text", {})
            link_data = text_data.get("link")

            if link_data and link_data.get("url"):
                children.append({
                    "type": "link",
                    "text": plain_text,
                    "url": link_data["url"],
                })
            elif plain_text:
                children.append({
                    "type": "text",
                    "text": plain_text,
                })

        elif item_type == "equation":
            expression = item.get("equation", {}).get(
                "expression",
                "",
            )

            if expression:
                children.append({
                    "type": "text",
                    "text": expression,
                })

        elif plain_text:
            children.append({
                "type": "text",
                "text": plain_text,
            })

    return children


def get_image_url(image_data):
    """获取 Notion 图片的实际 URL。"""
    image_type = image_data.get("type")

    if image_type == "file":
        return image_data.get("file", {}).get("url", "")

    if image_type == "external":
        return image_data.get("external", {}).get("url", "")

    return ""


def get_image_extension(url, response):
    """根据响应头或 URL 获取图片扩展名。"""
    content_type = response.headers.get(
        "Content-Type",
        "",
    ).split(";")[0].lower()

    extension_map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/avif": ".avif",
        "image/svg+xml": ".svg",
        "image/heic": ".heic",
        "image/heif": ".heif",
    }

    if content_type in extension_map:
        return extension_map[content_type]

    extension = mimetypes.guess_extension(content_type)

    if extension in [".jpe", ".jpeg"]:
        return ".jpg"

    if extension:
        return extension

    url_extension = Path(urlparse(url).path).suffix.lower()

    if url_extension:
        return url_extension

    return ".jpg"


def download_image(image_url, image_number):
    """下载图片到 public/images/capsules/。"""
    response = requests.get(
        image_url,
        headers=DOWNLOAD_HEADERS,
        timeout=60,
        allow_redirects=True,
    )
    response.raise_for_status()

    if not response.content:
        raise RuntimeError("图片内容为空")

    content_type = response.headers.get(
        "Content-Type",
        "",
    ).split(";")[0].lower()

    if content_type and not content_type.startswith("image/"):
        raise RuntimeError(
            f"返回内容不是图片：Content-Type={content_type}"
        )

    extension = get_image_extension(image_url, response)
    filename = f"{image_number:04d}{extension}"
    output_path = IMAGE_DIR / filename

    with output_path.open("wb") as file:
        file.write(response.content)

    if output_path.stat().st_size < 100:
        output_path.unlink(missing_ok=True)
        raise RuntimeError("下载后的文件过小，可能不是有效图片")

    print(f"已下载图片：{output_path}")

    return f"/images/capsules/{filename}"


def clear_image_directory():
    """删除上一次同步生成的图片。"""
    if IMAGE_DIR.exists():
        for file in IMAGE_DIR.iterdir():
            if file.is_file():
                file.unlink()

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_page_title(properties):
    """读取页面标题。"""
    for property_data in properties.values():
        if property_data.get("type") != "title":
            continue

        title_items = property_data.get("title", [])
        title = get_rich_text_text(title_items).strip()

        if title:
            return title

    return ""


def get_page_date(page, properties):
    """
    优先读取名为 Created 的日期属性。

    如果没有 Created 属性，则使用页面创建时间。
    """
    created_property = properties.get("Created", {})

    if created_property.get("type") == "date":
        date_data = created_property.get("date")

        if date_data and date_data.get("start"):
            return date_data["start"]

    created_time = page.get("created_time", "")

    if created_time:
        return created_time[:10]

    return ""


def make_text_block(block_type, rich_text):
    """生成文字类 Block。"""
    children = get_rich_text_children(rich_text)

    if not children:
        return None

    return {
        "type": block_type,
        "children": children,
    }


def parse_block(block, image_number):
    """
    解析一个 Notion Block。

    返回：
    - 解析后的内容 Block；
    - 当前图片编号。
    """
    block_type = block.get("type", "")
    block_data = block.get(block_type, {})

    text_block_types = {
        "paragraph",
        "heading_1",
        "heading_2",
        "heading_3",
        "quote",
        "callout",
        "bulleted_list_item",
        "numbered_list_item",
        "to_do",
    }

    if block_type in text_block_types:
        rich_text = block_data.get("rich_text", [])
        parsed_block = make_text_block(
            block_type,
            rich_text,
        )

        return parsed_block, image_number

    if block_type == "image":
        image_url = get_image_url(block_data)

        if not image_url:
            return None, image_number

        try:
            local_url = download_image(
                image_url,
                image_number,
            )
        except Exception as error:
            print(f"下载闪念图片失败：{error}")
            return None, image_number

        caption = block_data.get("caption", [])
        caption_text = get_rich_text_text(caption).strip()

        parsed_block = {
            "type": "image",
            "url": local_url,
            "alt": caption_text,
        }

        return parsed_block, image_number + 1

    if block_type in {
        "bookmark",
        "embed",
        "link_preview",
    }:
        url = block_data.get("url", "")

        if not url:
            return None, image_number

        caption = block_data.get("caption", [])
        caption_text = get_rich_text_text(caption).strip()

        return {
            "type": "link",
            "text": caption_text or url,
            "url": url,
        }, image_number

    if block_type == "divider":
        return {
            "type": "divider",
        }, image_number

    return None, image_number


def parse_page(page, image_number):
    """解析一个 Notion 页面。"""
    page_id = page.get("id")
    properties = page.get("properties", {})

    title = get_page_title(properties)
    date = get_page_date(page, properties)
    blocks = get_all_blocks(page_id)

    parsed_blocks = []

    for block in blocks:
        parsed_block, image_number = parse_block(
            block,
            image_number,
        )

        if parsed_block:
            parsed_blocks.append(parsed_block)

    capsule = {
        "title": title,
        "date": date,
        "blocks": parsed_blocks,
    }

    return capsule, image_number


def main():
    pages = query_all_pages()

    print(f"数据库返回 {len(pages)} 个页面")

    clear_image_directory()

    capsules = []
    image_number = 1

    for index, page in enumerate(pages, start=1):
        try:
            capsule, image_number = parse_page(
                page,
                image_number,
            )

            # 只要页面存在就保留，即使正文暂时为空
            capsules.append(capsule)

            print(
                f"[{index}/{len(pages)}] "
                f"已同步：{capsule['title'] or '未命名动态'}"
            )

        except Exception as error:
            print(
                f"[{index}/{len(pages)}] "
                f"同步页面失败：{error}"
            )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(
            capsules,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"✅ 成功同步 {len(capsules)} 条闪念")
    print(f"✅ JSON 已保存到：{OUTPUT_PATH}")
    print(f"✅ 图片已保存到：{IMAGE_DIR}")


if __name__ == "__main__":
    main()
