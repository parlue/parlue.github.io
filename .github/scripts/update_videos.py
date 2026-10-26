"""Keeps echesstactics/videos.json up to date from the YouTube playlist feed.

The feed only lists the newest 15 entries of a playlist, so the script MERGES it into the existing file: videos that
are already stored are kept (older ones never disappear), new ones are added, titles and descriptions are refreshed.
Thumbnails are downloaded into assets/echesstactics/videos/ so the page itself loads nothing from YouTube.

Run:  python .github/scripts/update_videos.py
"""
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

PLAYLIST = "PLDH3rU5dsNmA"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
JSON_PATH = os.path.join(ROOT, "echesstactics", "videos.json")
THUMB_DIR = os.path.join(ROOT, "assets", "echesstactics", "videos")
FEED = "https://www.youtube.com/feeds/videos.xml?playlist_id=" + PLAYLIST
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "m": "http://search.yahoo.com/mrss/"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (video list updater)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    feed = ET.fromstring(fetch(FEED))
    old = {}
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, encoding="utf-8") as f:
            for v in json.load(f).get("videos", []):
                old[v["id"]] = v
    os.makedirs(THUMB_DIR, exist_ok=True)
    changed = False
    for e in feed.findall("a:entry", NS):
        vid = e.find("yt:videoId", NS).text
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", vid):
            continue
        group = e.find("m:group", NS)
        entry = {
            "id": vid,
            "title": e.find("a:title", NS).text or "",
            "published": (e.find("a:published", NS).text or "")[:10],
            "description": (group.find("m:description", NS).text or "").strip() if group is not None and group.find("m:description", NS) is not None else "",
        }
        thumb = os.path.join(THUMB_DIR, vid + ".jpg")
        if not os.path.exists(thumb):
            try:
                with open(thumb, "wb") as f:
                    f.write(fetch("https://i.ytimg.com/vi/%s/hqdefault.jpg" % vid))
                changed = True
            except Exception as ex:
                print("thumbnail failed for", vid, ex, file=sys.stderr)
        if old.get(vid) != entry:
            old[vid] = entry
            changed = True
    videos = sorted(old.values(), key=lambda v: (v["published"], v["id"]), reverse=True)
    out = {"playlist": PLAYLIST, "playlistUrl": "https://www.youtube.com/playlist?list=" + PLAYLIST, "videos": videos}
    text = json.dumps(out, indent=1, ensure_ascii=False) + "\n"
    if not os.path.exists(JSON_PATH) or open(JSON_PATH, encoding="utf-8").read() != text:
        with open(JSON_PATH, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        changed = True
    print("videos:", len(videos), "changed" if changed else "unchanged")


if __name__ == "__main__":
    main()
