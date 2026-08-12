import rss from "@astrojs/rss";
import { getSortedPosts } from "@utils/content-utils";
import { url } from "@utils/url-utils";
import type { APIContext } from "astro";
import MarkdownIt from "markdown-it";
import sanitizeHtml from "sanitize-html";
import { siteConfig } from "@/config";

const parser = new MarkdownIt();

// 过滤掉 XML 不支持的非法控制字符，防止 RSS 解析失败
function stripInvalidXmlChars(str: string): string {
	return str.replace(
		// biome-ignore lint/suspicious/noControlCharactersInRegex: https://www.w3.org/TR/xml/#charsets
		/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F\uFDD0-\uFDEF\uFFFE\uFFFF]/g,
		"",
	);
}

export async function GET(context: APIContext) {
	const blog = await getSortedPosts();

	// 直接返回 rss() 函数的结果，Astro 会自动处理 Content-Type 和 XML 头部
	return rss({
		title: siteConfig.title,
		description: siteConfig.subtitle || "No description",
		// 使用 context.site 获取 astro.config.mjs 中配置的 site 域名
		site: context.site ?? "https://blog.feimind.xyz",
		items: blog.map((post) => {
			const content =
				typeof post.body === "string" ? post.body : String(post.body || "");
			const cleanedContent = stripInvalidXmlChars(content);
			return {
				title: post.data.title,
				pubDate: post.data.published,
				description: post.data.description || "",
				// 生成绝对路径 URL
				link: url(`/posts/${post.slug}/`),
				// 渲染 Markdown 为 HTML 供 RSS 阅读器直接展示
				content: sanitizeHtml(parser.render(cleanedContent), {
					allowedTags: sanitizeHtml.defaults.allowedTags.concat(["img"]),
				}),
			};
		}),
		customData: `<language>${siteConfig.lang}</language>`,
	});
}
