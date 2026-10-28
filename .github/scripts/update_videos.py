"""Keeps the video lists (eChessTactics: echesstactics/videos.json, eChessGw: videos-echessgw.json) up to date from the YouTube playlist feeds.

The feed only lists the newest 15 entries of a playlist, so the script MERGES it into the existing file: videos that
are already stored are kept (older ones never disappear), new ones are added, titles and descriptions are refreshed.
Thumbnails are downloaded into assets/echesstactics/videos/ so the page itself loads nothing from YouTube.

Run:  python .github/scripts/update_videos.py
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# (playlist id, json file, thumbnail folder)
LISTS = [
    ("PLDH3rU5dsNmA", os.path.join(ROOT, "echesstactics", "videos.json"), os.path.join(ROOT, "assets", "echesstactics", "videos")),
    ("PLZBfpnCj3l20", os.path.join(ROOT, "videos-echessgw.json"), os.path.join(ROOT, "assets", "echessgw-videos")),
]
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "m": "http://search.yahoo.com/mrss/"}


def fetch(url, tries=3):
    """GET with up to 3 attempts; every failure is printed with its HTTP status so the workflow log shows the real cause."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (video list updater)"})
    for attempt in range(1, tries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as ex:
            print("attempt %d/%d failed: HTTP %s %s for %s" % (attempt, tries, ex.code, ex.reason, url), file=sys.stderr)
            if attempt == tries:
                raise
        except Exception as ex:
            print("attempt %d/%d failed: %s: %s for %s" % (attempt, tries, type(ex).__name__, ex, url), file=sys.stderr)
            if attempt == tries:
                raise
        time.sleep(5 * attempt)


def update(PLAYLIST, JSON_PATH, THUMB_DIR):
    feed = ET.fromstring(fetch("https://www.youtube.com/feeds/videos.xml?playlist_id=" + PLAYLIST))
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


def main():
    failed = 0
    for playlist, json_path, thumb_dir in LISTS:
        try:
            update(playlist, json_path, thumb_dir)
        except Exception as ex:
            # a failed fetch (for example YouTube refusing the runner) must not turn the whole job red; the old list stays
            failed += 1
            print("WARNING: list %s not updated: %s: %s" % (playlist, type(ex).__name__, ex), file=sys.stderr)
    if failed == len(LISTS):
        print("WARNING: no list could be updated, keeping the stored lists", file=sys.stderr)


if __name__ == "__main__":
    main()
