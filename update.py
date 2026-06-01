#!/usr/bin/env python3
"""
SuperMemory -> GitHub Pages 每日更新脚本
从 SuperMemory 拉取所有记忆，生成 index.html，推送到 GitHub Pages。
"""

import json
import os
import subprocess
import sys
from datetime import datetime

HERMES_HOME = os.path.expanduser("~/.hermes")
SITE_DIR = "/tmp/wxcadk.github.io"
CONTAINERS = ["hermes", "projects", "areas", "resources", "archives"]
CONTAINER_LABELS = {
    "hermes": "Hermes",
    "projects": "Projects",
    "areas": "Areas",
    "resources": "Resources",
    "archives": "Archives",
}
CONTAINER_COLORS = {
    "hermes": "#58a6ff",
    "projects": "#3fb950",
    "areas": "#f0883e",
    "resources": "#bc8cff",
    "archives": "#8b949e",
}


def fetch_memories():
    """通过 hermes CLI 从 SuperMemory 拉取所有记忆"""
    all_memories = []
    
    for container in CONTAINERS:
        queries = [
            "skills", "Hermes", "configuration", "GitHub", "飞书", "cron",
            "research", "memory", "website", "Agent", "project", "task",
            "preference", "workflow", "learning", "note", "idea", "todo",
            "feishu", "supermemory", "PARA", "daily", "update"
        ]
        seen_ids = set()
        
        for query in queries:
            try:
                result = subprocess.run(
                    ["hermes", "chat", "-q", "-Q",
                     f"Use supermemory_search to search container '{container}' with query '{query}', limit 20. Return ONLY a JSON array of objects with id, content, similarity fields. No explanation, just the JSON."],
                    capture_output=True, text=True, timeout=30,
                    env={**os.environ, "HERMES_HOME": HERMES_HOME}
                )
                
                # Parse JSON from output
                output = result.stdout.strip()
                # Find JSON array in output
                start = output.find('[')
                end = output.rfind(']')
                if start != -1 and end != -1:
                    try:
                        items = json.loads(output[start:end+1])
                        for item in items:
                            if item.get("id") not in seen_ids and item.get("content"):
                                seen_ids.add(item["id"])
                                item["container"] = container
                                all_memories.append(item)
                    except json.JSONDecodeError:
                        pass
            except subprocess.TimeoutExpired:
                pass
            except Exception as e:
                print(f"Error fetching {container}/{query}: {e}", file=sys.stderr)
    
    return all_memories


def fetch_via_profile():
    """通过 supermemory_profile 获取近期上下文作为补充"""
    try:
        result = subprocess.run(
            ["hermes", "chat", "-q", "-Q",
             "Use supermemory_profile to get all recent context. Return ONLY a JSON array of strings, each string is one memory item. No explanation, just the JSON array."],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "HERMES_HOME": HERMES_HOME}
        )
        output = result.stdout.strip()
        start = output.find('[')
        end = output.rfind(']')
        if start != -1 and end != -1:
            return json.loads(output[start:end+1])
    except:
        pass
    return []


def generate_html(memories, profile_items):
    """生成 index.html"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Group by container
    by_container = {}
    for m in memories:
        c = m.get("container", "hermes")
        by_container.setdefault(c, []).append(m)
    
    active_containers = len([c for c in CONTAINERS if by_container.get(c)])
    total_count = len(memories) + len(profile_items)
    max_sim = max([m.get("similarity", 0) for m in memories], default=0)
    
    # Build memory cards HTML
    cards_html = ""
    
    # Profile items first (if any extra not in memories)
    existing_contents = {m.get("content", "") for m in memories}
    for item in profile_items:
        if item and item not in existing_contents:
            cards_html += f'''
    <div class="memory-card" data-container="hermes">
      <div class="meta">
        <span class="container-tag tag-hermes">hermes</span>
        <span class="timestamp">{now.split()[0]}</span>
        <span style="color: var(--purple); font-size: 0.75rem;">profile</span>
      </div>
      <div class="content">{item}</div>
    </div>'''
    
    for container in CONTAINERS:
        items = by_container.get(container, [])
        for m in items:
            content = m.get("content", "").replace("<", "&lt;").replace(">", "&gt;")
            # Simple code detection
            if "`" in content:
                content = content.replace("`", "<code>").replace("`", "</code>")
                # Fix double-wrapped
                content = content.replace("<code><code>", "<code>").replace("</code></code>", "</code>")
            
            sim = m.get("similarity", 0)
            tag_class = f"tag-{container}"
            
            cards_html += f'''
    <div class="memory-card" data-container="{container}">
      <div class="meta">
        <span class="container-tag {tag_class}">{container}</span>
        <span class="timestamp">{now.split()[0]}</span>
      </div>
      <div class="content">{content}</div>
      {"<div class='similarity'>相关度: " + str(sim) + "%</div>" if sim else ""}
    </div>'''
    
    if not cards_html.strip():
        cards_html = '<div class="empty-state"><p>暂无记忆 📭</p></div>'
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Memory Journal - wxcadk</title>
<style>
  :root {{
    --bg: #0d1117;
    --card: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --purple: #bc8cff;
    --orange: #f0883e;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.6; min-height: 100vh;
  }}
  .container {{ max-width: 900px; margin: 0 auto; padding: 2rem 1.5rem; }}
  header {{ text-align: center; padding: 3rem 0 2rem; border-bottom: 1px solid var(--border); margin-bottom: 2rem; }}
  header h1 {{ font-size: 2rem; font-weight: 700; background: linear-gradient(135deg, var(--accent), var(--purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem; }}
  header .subtitle {{ color: var(--muted); font-size: 0.95rem; }}
  .update-badge {{ display: inline-block; margin-top: 1rem; padding: 0.3rem 0.8rem; background: rgba(63, 185, 80, 0.15); border: 1px solid rgba(63, 185, 80, 0.3); border-radius: 20px; color: var(--green); font-size: 0.8rem; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
  .stat-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1.2rem; text-align: center; }}
  .stat-card .number {{ font-size: 1.8rem; font-weight: 700; color: var(--accent); }}
  .stat-card .label {{ font-size: 0.8rem; color: var(--muted); margin-top: 0.3rem; }}
  .filter-bar {{ display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }}
  .filter-btn {{ padding: 0.4rem 1rem; border-radius: 20px; border: 1px solid var(--border); background: transparent; color: var(--muted); cursor: pointer; font-size: 0.85rem; transition: all 0.2s; }}
  .filter-btn:hover, .filter-btn.active {{ border-color: var(--accent); color: var(--accent); background: rgba(88, 166, 255, 0.1); }}
  .memory-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1.2rem 1.5rem; margin-bottom: 1rem; transition: border-color 0.2s; }}
  .memory-card:hover {{ border-color: var(--accent); }}
  .memory-card .meta {{ display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.6rem; font-size: 0.8rem; }}
  .memory-card .container-tag {{ padding: 0.15rem 0.6rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
  .tag-hermes {{ background: rgba(88, 166, 255, 0.15); color: var(--accent); }}
  .tag-projects {{ background: rgba(63, 185, 80, 0.15); color: var(--green); }}
  .tag-areas {{ background: rgba(240, 136, 62, 0.15); color: var(--orange); }}
  .tag-resources {{ background: rgba(188, 140, 255, 0.15); color: var(--purple); }}
  .tag-archives {{ background: rgba(139, 148, 158, 0.15); color: var(--muted); }}
  .memory-card .timestamp {{ color: var(--muted); }}
  .memory-card .content {{ font-size: 0.95rem; line-height: 1.7; }}
  .memory-card .content code {{ background: rgba(110, 118, 129, 0.2); padding: 0.15rem 0.4rem; border-radius: 4px; font-size: 0.85rem; }}
  .memory-card .similarity {{ display: inline-block; margin-top: 0.6rem; font-size: 0.75rem; color: var(--muted); }}
  .empty-state {{ text-align: center; padding: 3rem; color: var(--muted); }}
  footer {{ text-align: center; padding: 2rem 0; color: var(--muted); font-size: 0.8rem; border-top: 1px solid var(--border); margin-top: 2rem; }}
  @media (max-width: 600px) {{ .container {{ padding: 1rem; }} header h1 {{ font-size: 1.5rem; }} .stats {{ grid-template-columns: repeat(2, 1fr); }} }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🧠 Memory Journal</h1>
    <div class="subtitle">SuperMemory 每日记忆存档 · wxcadk</div>
    <div class="update-badge">📅 更新时间: {now}</div>
  </header>
  <div class="stats">
    <div class="stat-card"><div class="number" id="total-count">{total_count}</div><div class="label">总记忆数</div></div>
    <div class="stat-card"><div class="number">5</div><div class="label">PARA 容器</div></div>
    <div class="stat-card"><div class="number">{active_containers}</div><div class="label">活跃容器</div></div>
    <div class="stat-card"><div class="number">{max_sim}%</div><div class="label">最高相似度</div></div>
  </div>
  <div class="filter-bar">
    <button class="filter-btn active" onclick="filterCards('all',this)">全部</button>
    <button class="filter-btn" onclick="filterCards('hermes',this)">Hermes</button>
    <button class="filter-btn" onclick="filterCards('projects',this)">Projects</button>
    <button class="filter-btn" onclick="filterCards('areas',this)">Areas</button>
    <button class="filter-btn" onclick="filterCards('resources',this)">Resources</button>
    <button class="filter-btn" onclick="filterCards('archives',this)">Archives</button>
  </div>
  <div id="memories">{cards_html}
  </div>
  <footer>
    Powered by SuperMemory + Hermes Agent · Auto-updated daily<br>
    <span style="color: var(--accent);">wxcadk.github.io</span>
  </footer>
</div>
<script>
function filterCards(c,btn) {{
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  let v=0;
  document.querySelectorAll('.memory-card').forEach(card=>{{
    if(c==='all'||card.dataset.container===c){{card.style.display='block';v++}}else{{card.style.display='none'}}
  }});
  document.getElementById('total-count').textContent=v;
}}
</script>
</body>
</html>'''
    
    return html


def push_to_github():
    """提交并推送到 GitHub"""
    os.chdir(SITE_DIR)
    subprocess.run(["git", "config", "user.email", "wxcadk@users.noreply.github.com"], check=True)
    subprocess.run(["git", "config", "user.name", "wxcadk"], check=True)
    subprocess.run(["git", "add", "-A"], check=True)
    
    # Check if there are changes
    result = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
    if result.returncode == 0:
        print("No changes to commit.")
        return False
    
    subprocess.run(["git", "commit", "-m", f"auto: update memories {datetime.now().strftime('%Y-%m-%d %H:%M')}"], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)
    print("Pushed successfully!")
    return True


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting memory update...")
    
    # Fetch memories
    print("Fetching memories from SuperMemory...")
    memories = fetch_memories()
    print(f"Found {len(memories)} memories across containers.")
    
    # Fetch profile as supplement
    print("Fetching profile context...")
    profile_items = fetch_via_profile()
    print(f"Found {len(profile_items)} profile items.")
    
    # Generate HTML
    print("Generating HTML...")
    html = generate_html(memories, profile_items)
    with open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML written.")
    
    # Push to GitHub
    print("Pushing to GitHub...")
    try:
        push_to_github()
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Done! Site: https://wxcadk.github.io")


if __name__ == "__main__":
    main()