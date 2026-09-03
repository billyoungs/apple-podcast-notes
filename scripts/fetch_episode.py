#!/usr/bin/env python3
"""
fetch_episode.py — 解析 Apple Podcasts 单集页面。

用法:
    python fetch_episode.py "<Apple Podcasts 链接>" --out ./_work [--download]

产物 (写入 --out 目录):
    meta.json               元数据 (title / podcast_title / pub_date / duration_sec / audio_url / eid / platform)
    shownotes.md            shownotes 正文 (HTML -> Markdown, 保留图片链接)
    audio.m4a               音频 (仅当 --download)

数据来源: iTunes Lookup API + RSS feed（均公开、无需认证）
仅支持公开单集; 付费/需登录内容拿不到直链。纯标准库, 无第三方依赖。
"""
import argparse, json, os, re, sys, html, urllib.request, urllib.error
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, parse_qs

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


# ============================================================
#  工具函数
# ============================================================

def fetch_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return {}


def download(url: str, path: str):
    print(f"[下载] {url}\n    -> {path}")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        total = int(r.headers.get("Content-Length", 0))
        done = 0
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                pct = done * 100 // total
                print(f"\r    {pct:3d}%  {done>>20}/{total>>20} MB",
                      end="", flush=True)
        print()
    print("[完成] 音频已保存")


def html_to_md(raw: str) -> str:
    """极简 HTML -> Markdown, 保留段落、列表、图片、链接。"""
    if not raw:
        return ""
    s = raw
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    s = re.sub(r'</p>', '\n\n', s, flags=re.I)
    s = re.sub(r'<p[^>]*>', '', s, flags=re.I)
    s = re.sub(r'<li[^>]*>', '- ', s, flags=re.I)
    s = re.sub(r'</li>', '\n', s, flags=re.I)
    s = re.sub(r'<img[^>]*?alt=["\'](.*?)["\'][^>]*?src=["\'](.*?)["\'][^>]*?>',
               r'\n![\1](\2)\n', s, flags=re.I)
    s = re.sub(r'<img[^>]*?src=["\'](.*?)["\'][^>]*?>',
               r'\n![](\1)\n', s, flags=re.I)
    s = re.sub(r'<a[^>]*?href=["\'](.*?)["\'][^>]*?>(.*?)</a>',
               r'[\2](\1)', s, flags=re.I | re.S)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    s = re.sub(r'\n{3,}', '\n\n', s).strip()
    return s


# ============================================================
#  Apple Podcasts 解析
# ============================================================

APPLE_EPISODE_RE = re.compile(r'/id(\d+)(?:\?.*?i=(\d+))?')


def parse_apple_url(url: str):
    """从 Apple Podcasts URL 提取 podcast_id 和 episode_id。"""
    m = APPLE_EPISODE_RE.search(url)
    if not m:
        return None, None
    podcast_id = m.group(1)
    episode_id = m.group(2)
    if not episode_id:
        parsed = urlparse(url)
        q = parse_qs(parsed.query)
        episode_id = (q.get("i") or [None])[0]
    return podcast_id, episode_id


def apple_lookup_episode(podcast_id: str, episode_id: str) -> dict:
    """通过 iTunes Lookup API 查询单集详情。"""
    url = f"https://itunes.apple.com/lookup?id={podcast_id}&entity=podcastEpisode&limit=300"
    data = fetch_json(url)
    results = data.get("results", [])
    if not results:
        return {}

    podcast = results[0]
    feed_url = podcast.get("feedUrl", "")
    podcast_title = podcast.get("collectionName", "")

    target = None
    for r in results[1:]:
        if str(r.get("trackId")) == str(episode_id):
            target = r
            break
    if not target:
        return {}

    return {
        "feed_url": feed_url,
        "podcast_title": podcast_title,
        "title": target.get("trackName", ""),
        "description": target.get("description", ""),
        "duration_ms": target.get("trackTimeMillis") or 0,
        "release_date": target.get("releaseDate", ""),
        "episode_guid": target.get("episodeGuid", ""),
    }


def find_episode_in_rss(rss_xml: str, episode_guid: str) -> dict:
    """在 RSS feed 中按 GUID 查找单集，返回 {audio_url, title, duration_sec, description}"""
    result = {}
    if not rss_xml.strip():
        return result
    try:
        root = ET.fromstring(rss_xml)
    except ET.ParseError:
        return result

    ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
          "content": "http://purl.org/rss/1.0/modules/content/"}
    channel = root.find("channel")
    if channel is None:
        return result

    target_item = None
    if episode_guid:
        for item in channel.findall("item"):
            guid_el = item.find("guid")
            if guid_el is not None and guid_el.text:
                if guid_el.text.strip() == episode_guid:
                    target_item = item
                    break
    if target_item is None:
        return result

    title_el = target_item.find("title")
    if title_el is not None and title_el.text:
        result["title"] = title_el.text.strip()

    enclosure = target_item.find("enclosure")
    if enclosure is not None:
        result["audio_url"] = enclosure.get("url", "")

    dur_el = target_item.find("itunes:duration", ns)
    if dur_el is not None and dur_el.text:
        d = dur_el.text.strip().split(":")
        if len(d) == 3:
            result["duration_sec"] = int(d[0]) * 3600 + int(d[1]) * 60 + int(d[2])
        elif len(d) == 2:
            result["duration_sec"] = int(d[0]) * 60 + int(d[1])
        else:
            try:
                result["duration_sec"] = int(dur_el.text.strip())
            except ValueError:
                pass

    desc_el = target_item.find("description")
    if desc_el is not None and desc_el.text:
        result["description"] = desc_el.text.strip()

    content_el = target_item.find("content:encoded", ns)
    if content_el is not None and content_el.text:
        result["content_encoded"] = content_el.text.strip()

    return result


def fetch_rss_feed(url: str) -> str:
    """获取 RSS feed 原始 XML。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return ""


def fetch_apple_episode(url: str):
    """
    解析 Apple Podcasts 单集：
    1. 从 URL 提取 podcast_id 和 episode_id
    2. 通过 iTunes Lookup API 获取单集数据和 RSS feed URL
    3. 通过 RSS feed 获取音频直链
    """
    podcast_id, episode_id = parse_apple_url(url)
    if not podcast_id:
        sys.exit("[错误] 无法从 Apple Podcasts URL 中提取播客 ID")
    if not episode_id:
        sys.exit("[错误] Apple Podcasts 链接必须包含单集 ID (?i=...)，仅播客首页链接无法确定具体单集。")

    print(f"[Apple Podcasts] 查询 API (podcast_id={podcast_id}, episode_id={episode_id})...")
    lookup = apple_lookup_episode(podcast_id, episode_id)
    if not lookup:
        sys.exit("[错误] 未能在 iTunes 目录中找到该单集。请检查链接是否正确。")

    title = lookup.get("title") or "(未取到标题)"
    podcast = lookup.get("podcast_title") or ""
    shownotes_md = html_to_md(lookup.get("description") or "")
    duration_sec = (lookup.get("duration_ms") or 0) // 1000
    pub_date = (lookup.get("release_date") or "")[:10]
    episode_guid = lookup.get("episode_guid") or ""
    feed_url = lookup.get("feed_url") or ""

    audio_url = ""
    if feed_url:
        print(f"[Apple Podcasts] RSS feed: {feed_url}")
        rss_xml = fetch_rss_feed(feed_url)
        if rss_xml and episode_guid:
            rss_result = find_episode_in_rss(rss_xml, episode_guid)
            audio_url = rss_result.get("audio_url", "")
            if audio_url:
                print(f"[Apple Podcasts] 成功获取音频直链 ✅")
            else:
                print(f"[Apple Podcasts] 在 RSS 中未找到匹配单集的音频直链")
    else:
        print(f"[Apple Podcasts] 未找到 RSS feed（可能需在 iTunes 上架播客才可获取）")

    guest_hints = re.findall(
        r"(?:对话|对谈|专访|访谈|聊聊|嘉宾|with|feat|与)[：:\s]*([一-龥A-Za-z·]{2,12})",
        title)

    meta = {
        "eid": episode_id,
        "url": url,
        "title": title,
        "podcast_title": podcast,
        "hosts": [],
        "guest_hints": guest_hints,
        "pub_date": pub_date,
        "duration_sec": duration_sec,
        "audio_url": audio_url,
        "has_official_transcript": False,
        "platform": "apple",
    }

    return meta, shownotes_md, []


# ============================================================
#  主入口
# ============================================================

def main():
    ap = argparse.ArgumentParser(description="解析 Apple Podcasts 单集链接")
    ap.add_argument("target", help="Apple Podcasts 链接（如 https://podcasts.apple.com/.../id123?i=456）")
    ap.add_argument("--out", default="./_work", help="输出目录")
    ap.add_argument("--download", action="store_true", help="同时下载音频")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    url = args.target.strip()
    print(f"[解析] {url}")
    meta, shownotes_md, chapters = fetch_apple_episode(url)

    with open(os.path.join(args.out, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "shownotes.md"), "w", encoding="utf-8") as f:
        f.write(shownotes_md or "(无 shownotes)")

    print("\n=== 解析结果 ===")
    print(f"  节目   : {meta['podcast_title'] or '(未取到)'}")
    print(f"  单集   : {meta['title'] or '(未取到)'}")
    print(f"  发布   : {meta['pub_date'] or '(未取到)'}")
    print(f"  时长   : {meta['duration_sec'] and round(meta['duration_sec']/60,1)} 分钟")
    print(f"  音频   : {'有 ✅' if meta.get('audio_url') else '(未取到)'}")
    print(f"  产物   : {os.path.abspath(args.out)}")

    if args.download:
        if not meta.get("audio_url"):
            sys.exit("[错误] 未取到音频直链, 无法下载。")
        download(meta["audio_url"], os.path.join(args.out, "audio.m4a"))


if __name__ == "__main__":
    main()