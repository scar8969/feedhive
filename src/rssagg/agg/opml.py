import xml.etree.ElementTree as ET

def parse_opml(xml):
    root = ET.fromstring(xml)
    out = []
    for outline in root.iter("outline"):
        url = outline.get("xmlUrl")
        if url:
            out.append((outline.get("title", ""), url))
    return out

def export_opml(feeds):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<opml version="2.0"><body>']
    for f in feeds:
        lines.append(f'  <outline text="{f.title}" title="{f.title}" type="rss" xmlUrl="{f.url}"/>')
    lines.append("</body></opml>")
    return "\n".join(lines)
