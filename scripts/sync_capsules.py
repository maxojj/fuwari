import hashlib
import json
import mimetypes
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import requests


# --------------------------------------------------
# 基础配置
# --------------------------------------------------

NOTION_TOKEN = os.getenv("NOTION_CAPSULES_TOKEN")

CAPSULE_DATABASE_ID = os.getenv(
    "CAPSULE_DATABASE_ID",
    "908644799ee341759a3fc9eb73ecff1b",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_PATH = (
    PROJECT_ROOT
    / "src"
    / "content"
    / "capsules.json"
)

IMAGE_DIR = (
    PROJECT_ROOT
    / "public"
    / "images"
    / "capsules"
)

NOTION_VERSION = "2022-06-28"


if not NOTION_TOKEN:
    raise RuntimeError(
        "没有找到 NOTION_CAPSULES_TOKEN 环境变量"
    )


NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0",
}


# --------------------------------------------------
# 通用请求
# --------------------------------------------------

def notion_request(method, url, **kwargs):
    response = requests.request(
        method,
        url,
        headers=NOTION_HEADERS,
        timeout=60,
        **kwargs,
    )

    if not response.ok:
        print(f"Notion API 请求失败：{response.status_code}")
        print(response.text[:3000])

    response.raise_for_status()
    return response.json()


# --------------------------------------------------
# 查询数据库页面
# --------------------------------------------------

def query_all_pages():
    """
    查询数据库中的全部页面。

    你的接口返回中 has_more 为 true 时，
    使用 next_cursor 自动请求下一页。
    """
    url = (
        "https://api.notion.com/v1/databases/"
        f"{CAPSULE_DATABASE_ID}/query"
    )

    pages = []
    payload = {
        "page_size": 100,
    }

    while True:
        data = notion_request(
            "POST",
            url,
            json=payload,
        )

        pages.extend(data.get("results", []))

        if not data.get("has_more"):
            break

        next_cursor = data.get("next_cursor")

        if not next_cursor:
            break

        payload["start_cursor"] = next_cursor

    return pages


# --------------------------------------------------
# 获取页面正文 Blocks
# --------------------------------------------------

def get_all_blocks(block_id):
    """
    获取页面下的全部一级子 Block。
    """
    url = (
        f"https://api.notion.com/v1/blocks/"
        f"{block_id}/children"
    )

    blocks = []
    params = {
        "page_size": 100,
    }

    while True:
        data = notion_request(
            "GET",
            url,
            params=params,
        )

        blocks.extend(data.get("results", []))

        if not data.get("has_more"):
            break

        next_cursor = data.get("next_cursor")

        if not next_cursor:
            break

        params["start_cursor"] = next_cursor

    return blocks


# --------------------------------------------------
# Rich text 处理
# --------------------------------------------------

def parse_rich_text(rich_text):
    """
    将 Notion rich_text 转换为 children。

    普通文本：

    {
      "type": "text",
      "text": "内容"
    }

    文字链接：

    {
      "type": "link",
      "text": "链接文字",
      "url": "https://example.com"
    }
    """
    children = []

    for item in rich_text or []:
        item_type = item.get("type")
        plain_text = item.get("plain_text", "")

        if not plain_text:
            continue

        if item_type == "text":
            text_data = item.get("text", {})
            link_data = text_data.get("link")

            if link_data and link_data.get("url"):
                children.append({
                    "type": "link",
                    "text": plain_text,
                    "url": link_data["url"],
                })
            else:
                children.append({
                    "type": "text",
                    "text": plain_text,
                })

        elif item_type == "equation":
            expression = item.get(
                "equation",
                {},
            ).get("expression", "")

            if expression:
                children.append({
                    "type": "text",
                    "text": expression,
                })

        else:
            children.append({
                "type": "text",
                "text": plain_text,
            })

    return children


def rich_text_to_plain_text(rich_text):
    return "".join(
        item.get("plain_text", "")
        for item in rich_text or []
    )


# --------------------------------------------------
# 数据库属性
# --------------------------------------------------

def get_page_date(page):
    """
    你的 Created 属性类型是 created_time，
    不是 date。
    """
    properties = page.get("properties", {})
    created_property = properties.get("Created", {})

    if created_property.get("type") == "created_time":
        created_time = created_property.get(
            "created_time",
            "",
        )

        if created_time:
            return created_time[:10]

    page_created_time = page.get("created_time", "")

    if page_created_time:
        return page_created_time[:10]

    return ""


def get_page_tags(page):
    properties = page.get("properties", {})
    tags_property = properties.get("Tags", {})

    if tags_property.get("type") != "multi_select":
        return []

    return [
        item.get("name", "")
        for item in tags_property.get("multi_select", [])
        if item.get("name")
    ]


# --------------------------------------------------
# 图片处理
# --------------------------------------------------

def get_image_url(image_data):
    image_type = image_data.get("type")

    if image_type == "file":
        return image_data.get(
            "file",
            {},
        ).get("url", "")

    if image_type == "external":
        return image_data.get(
            "external",
            {},
        ).get("url", "")

    return ""


def safe_filename(value):
    """
    清理文件名，只保留安全字符。
    """
    value = re.sub(
        r"[^a-zA-Z0-9._-]+",
        "-",
        value,
    )

    return value.strip("-") or "image"


def get_file_extension(url, response):
    content_type = response.headers.get(
        "Content-Type",
        "",
    ).split(";")[0].lower()

    content_type_extensions = {
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

    if content_type in content_type_extensions:
        return content_type_extensions[content_type]

    guessed_extension = mimetypes.guess_extension(
        content_type
    )

    if guessed_extension:
        if guessed_extension == ".jpe":
            return ".jpg"

        return guessed_extension

    url_extension = Path(
        urlparse(url).path
    ).suffix.lower()

    if url_extension:
        return url_extension

    return ".jpg"


def download_image(image_url, page_id, block_id):
    """
    下载图片，并根据 page_id + block_id 生成稳定文件名。

    这样每次同步不会因为排序变化而导致图片编号变化。
    """
    IMAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    response = requests.get(
        image_url,
        headers=DOWNLOAD_HEADERS,
        timeout=120,
        allow_redirects=True,
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type",
        "",
    ).split(";")[0].lower()

    if content_type and not content_type.startswith("image/"):
        raise RuntimeError(
            "下载内容不是图片，"
            f"Content-Type={content_type}"
        )

    extension = get_file_extension(
        image_url,
        response,
    )

    identity = f"{page_id}-{block_id}"
    short_hash = hashlib.sha1(
        identity.encode("utf-8")
    ).hexdigest()[:16]

    filename = (
        f"{safe_filename(page_id)}-"
        f"{short_hash}{extension}"
    )

    output_path = IMAGE_DIR / filename

    with output_path.open("wb") as file:
        file.write(response.content)

    print(f"已下载图片：{output_path}")

    return f"/images/capsules/{filename}"


# --------------------------------------------------
# Block 解析
# --------------------------------------------------

TEXT_BLOCK_TYPES = {
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


def parse_text_block(block):
    block_type = block.get("type", "")
    block_data = block.get(block_type, {})

    rich_text = block_data.get(
        "rich_text",
        [],
    )

    children = parse_rich_text(rich_text)

    # 忽略空段落
    if not children:
        return None

    return {
        "type": block_type,
        "children": children,
    }


def parse_image_block(block, page_id):
    block_data = block.get("image", {})
    image_url = get_image_url(block_data)

    if not image_url:
        return None

    try:
        local_url = download_image(
            image_url,
            page_id,
            block.get("id", "unknown"),
        )
    except Exception as error:
        print(f"图片下载失败：{error}")
        return None

    caption = rich_text_to_plain_text(
        block_data.get("caption", [])
    ).strip()

    return {
        "type": "image",
        "url": local_url,
        "alt": caption,
    }


def parse_link_block(block):
    block_type = block.get("type", "")
    block_data = block.get(block_type, {})

    url = block_data.get("url", "")

    if not url:
        return None

    caption = rich_text_to_plain_text(
        block_data.get("caption", [])
    ).strip()

    return {
        "type": "link",
        "text": caption or url,
        "url": url,
    }


def parse_block(block, page_id):
    block_type = block.get("type", "")

    if block_type in TEXT_BLOCK_TYPES:
        return parse_text_block(block)

    if block_type == "image":
        return parse_image_block(
            block,
            page_id,
        )

    if block_type in {
        "bookmark",
        "embed",
        "link_preview",
    }:
        return parse_link_block(block)

    if block_type == "divider":
        return {
            "type": "divider",
        }

    return None


# --------------------------------------------------
# 页面解析
# --------------------------------------------------

def parse_page(page):
    page_id = page.get("id", "")
    date = get_page_date(page)
    tags = get_page_tags(page)

    raw_blocks = get_all_blocks(page_id)
    parsed_blocks = []

    for block in raw_blocks:
        parsed_block = parse_block(
            block,
            page_id,
        )

        if parsed_block:
            parsed_blocks.append(parsed_block)

    return {
        "id": page_id,
        "date": date,
        "tags": tags,
        "blocks": parsed_blocks,
    }


# --------------------------------------------------
# 主程序
# --------------------------------------------------

def main():
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    IMAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    pages = query_all_pages()

    print(f"数据库中找到 {len(pages)} 个页面")

    capsules = []

    for index, page in enumerate(pages, start=1):
        page_id = page.get("id", "")

        try:
            capsule = parse_page(page)
            capsules.append(capsule)

            print(
                f"[{index}/{len(pages)}] "
                f"已同步：{page_id}"
            )

        except Exception as error:
            print(
                f"[{index}/{len(pages)}] "
                f"同步失败：{page_id}"
            )
            print(f"错误：{error}")

    # Notion API 默认通常按更新时间排序。
    # 这里按动态创建日期倒序排列，最新动态在前。
    capsules.sort(
        key=lambda item: item.get("date", ""),
        reverse=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            capsules,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(f"✅ 成功写入 {len(capsules)} 条动态")
    print(f"✅ JSON：{OUTPUT_PATH}")
    print(f"✅ 图片目录：{IMAGE_DIR}")


if __name__ == "__main__":
    main()
