# encoding: utf-8
"""
小红书数据采集工具 - Web GUI 版
双击运行后自动打开浏览器，无需安装任何额外工具
"""

import json
import os
import sys
import threading
import time
import webbrowser
from collections import deque

from flask import Flask, render_template_string, request, jsonify
from loguru import logger

from main import Data_Spider
from xhs_utils.path_util import resource_path

# ── Flask App ──────────────────────────────────────────────

app = Flask(__name__)
spider = Data_Spider()

# 日志缓冲
log_buffer = deque(maxlen=500)
task_status = {"running": False, "message": "就绪"}


def log_sink(message):
    record = message.record
    text = f'{record["time"].strftime("%H:%M:%S")} | {record["level"].name} | {record["message"]}'
    log_buffer.append(text)


logger.remove()
logger.add(log_sink, format="{message}")
logger.add(sys.stderr, format="{time:HH:mm:ss} | {level} | {message}")


def get_base_path():
    if hasattr(sys, '_MEIPASS'):
        base = os.path.join(os.path.dirname(sys.executable), "datas")
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "datas"))
    media = os.path.join(base, "media_datas")
    excel = os.path.join(base, "excel_datas")
    os.makedirs(media, exist_ok=True)
    os.makedirs(excel, exist_ok=True)
    return {"media": media, "excel": excel}


def run_task(func, desc):
    if task_status["running"]:
        return False, "有任务正在运行，请等待完成"
    task_status["running"] = True
    task_status["message"] = f"运行中：{desc}"
    logger.info(f"开始任务：{desc}")

    def wrapper():
        try:
            func()
            logger.info(f"任务完成：{desc}")
            task_status["message"] = "就绪 - 任务完成"
        except Exception as e:
            logger.error(f"任务失败：{e}")
            task_status["message"] = f"任务失败：{e}"
        finally:
            task_status["running"] = False

    threading.Thread(target=wrapper, daemon=True).start()
    return True, "任务已启动"


# ── 页面模板 ──────────────────────────────────────────────

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>小红书数据采集工具</title>
<style>
  :root { --primary: #ff4757; --bg: #f8f9fa; --card: #fff; --text: #333; --border: #e0e0e0; --radius: 10px; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }

  .header { background: linear-gradient(135deg, #ff4757, #ff6b81); color: #fff; padding: 20px 30px; text-align: center; box-shadow: 0 2px 10px rgba(255,71,87,0.3); }
  .header h1 { font-size: 24px; font-weight: 600; }
  .header p { font-size: 13px; opacity: 0.85; margin-top: 4px; }

  .container { max-width: 960px; margin: 20px auto; padding: 0 16px; }

  .tabs { display: flex; gap: 4px; margin-bottom: 0; }
  .tab { padding: 10px 22px; background: #e8e8e8; border: none; border-radius: var(--radius) var(--radius) 0 0; cursor: pointer; font-size: 14px; color: #666; transition: all 0.2s; }
  .tab:hover { background: #ddd; }
  .tab.active { background: var(--card); color: var(--primary); font-weight: 600; box-shadow: 0 -2px 6px rgba(0,0,0,0.05); }

  .panel { display: none; background: var(--card); border-radius: 0 var(--radius) var(--radius) var(--radius); padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
  .panel.active { display: block; }

  label { font-weight: 500; font-size: 14px; display: block; margin-bottom: 6px; }
  .hint { font-size: 12px; color: #999; margin-bottom: 8px; }
  textarea, input[type="text"], input[type="number"], select {
    width: 100%; padding: 10px 12px; border: 1.5px solid var(--border); border-radius: 8px;
    font-size: 14px; font-family: inherit; transition: border 0.2s; outline: none; resize: vertical;
  }
  textarea:focus, input:focus, select:focus { border-color: var(--primary); }

  .row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-top: 12px; }
  .row label { margin: 0; white-space: nowrap; }

  .radio-group { display: flex; gap: 10px; flex-wrap: wrap; }
  .radio-group label { display: flex; align-items: center; gap: 4px; font-weight: 400; cursor: pointer; padding: 5px 10px; border-radius: 6px; border: 1.5px solid var(--border); transition: all 0.15s; font-size: 13px; }
  .radio-group label:hover { border-color: var(--primary); }
  .radio-group input[type="radio"]:checked + span { color: var(--primary); font-weight: 600; }
  .radio-group label:has(input:checked) { border-color: var(--primary); background: #fff5f5; }
  .radio-group input[type="radio"] { accent-color: var(--primary); }

  .btn { padding: 10px 32px; background: var(--primary); color: #fff; border: none; border-radius: 8px; font-size: 15px; cursor: pointer; font-weight: 600; transition: all 0.2s; }
  .btn:hover { background: #e8414f; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(255,71,87,0.3); }
  .btn:disabled { background: #ccc; cursor: not-allowed; transform: none; box-shadow: none; }

  .log-box { background: var(--card); border-radius: var(--radius); padding: 16px; margin-top: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
  .log-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .log-header h3 { font-size: 15px; }
  .status { font-size: 13px; padding: 4px 12px; border-radius: 20px; }
  .status.idle { background: #e8f5e9; color: #2e7d32; }
  .status.running { background: #fff3e0; color: #e65100; animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }

  #log { background: #1e1e2e; color: #cdd6f4; padding: 14px; border-radius: 8px; height: 220px; overflow-y: auto; font-family: 'Consolas', 'Courier New', monospace; font-size: 12.5px; line-height: 1.6; white-space: pre-wrap; word-break: break-all; }
  .log-actions { margin-top: 8px; display: flex; gap: 8px; }
  .btn-sm { padding: 6px 14px; font-size: 12px; border-radius: 6px; border: 1.5px solid var(--border); background: var(--card); cursor: pointer; transition: all 0.15s; }
  .btn-sm:hover { border-color: var(--primary); color: var(--primary); }

  .section { margin-top: 16px; }
  .field-group { background: #fafafa; border-radius: 8px; padding: 14px; margin-top: 12px; border: 1px solid #f0f0f0; }
  .field-group legend, .field-group > label:first-child { font-size: 13px; color: #888; margin-bottom: 8px; }
</style>
</head>
<body>

<div class="header">
  <h1>小红书数据采集工具</h1>
  <p>Spider XHS - 笔记 / 用户 / 搜索 全功能采集</p>
</div>

<div class="container">
  <!-- Tabs -->
  <div class="tabs">
    <button class="tab active" onclick="switchTab(0)">Cookies 配置</button>
    <button class="tab" onclick="switchTab(1)">采集笔记</button>
    <button class="tab" onclick="switchTab(2)">用户笔记</button>
    <button class="tab" onclick="switchTab(3)">搜索采集</button>
  </div>

  <!-- Panel 0: Cookies -->
  <div class="panel active" id="panel-0">
    <label>小红书 Cookies</label>
    <div class="hint">获取方式：浏览器 F12 → Network → 任意请求 → Request Headers → Cookie，复制完整内容粘贴到下方</div>
    <textarea id="cookies" rows="5" placeholder="在此粘贴你的 Cookies..."></textarea>
    <div class="row" style="margin-top:12px">
      <button class="btn" onclick="saveCookies()">保存 Cookies</button>
    </div>
    <div class="field-group" style="margin-top:16px">
      <label>HTTP 代理（可选）</label>
      <input type="text" id="proxy" placeholder="例: http://127.0.0.1:7890">
    </div>
  </div>

  <!-- Panel 1: Notes -->
  <div class="panel" id="panel-1">
    <label>笔记链接</label>
    <div class="hint">每行一个链接，支持 xiaohongshu.com/explore/... 格式</div>
    <textarea id="note-urls" rows="6" placeholder="https://www.xiaohongshu.com/explore/xxx?xsec_token=xxx"></textarea>

    <div class="section">
      <label>保存方式</label>
      <div class="radio-group" id="note-save">
        <label><input type="radio" name="note-save" value="all" checked><span>全部保存</span></label>
        <label><input type="radio" name="note-save" value="media"><span>仅媒体</span></label>
        <label><input type="radio" name="note-save" value="media-image"><span>仅图片</span></label>
        <label><input type="radio" name="note-save" value="media-video"><span>仅视频</span></label>
        <label><input type="radio" name="note-save" value="excel"><span>仅Excel</span></label>
      </div>
    </div>
    <div class="row">
      <label>Excel 文件名：</label>
      <input type="text" id="note-excel" value="笔记数据" style="width:200px">
    </div>
    <div class="row" style="margin-top:16px">
      <button class="btn" onclick="startNote()">开始采集</button>
    </div>
  </div>

  <!-- Panel 2: User -->
  <div class="panel" id="panel-2">
    <label>用户主页链接</label>
    <div class="hint">格式: https://www.xiaohongshu.com/user/profile/...</div>
    <input type="text" id="user-url" placeholder="https://www.xiaohongshu.com/user/profile/xxx?xsec_token=xxx">

    <div class="section">
      <label>保存方式</label>
      <div class="radio-group">
        <label><input type="radio" name="user-save" value="all" checked><span>全部保存</span></label>
        <label><input type="radio" name="user-save" value="media"><span>仅媒体</span></label>
        <label><input type="radio" name="user-save" value="media-image"><span>仅图片</span></label>
        <label><input type="radio" name="user-save" value="media-video"><span>仅视频</span></label>
        <label><input type="radio" name="user-save" value="excel"><span>仅Excel</span></label>
      </div>
    </div>
    <div class="row" style="margin-top:16px">
      <button class="btn" onclick="startUser()">采集该用户全部笔记</button>
    </div>
  </div>

  <!-- Panel 3: Search -->
  <div class="panel" id="panel-3">
    <div class="row">
      <label>搜索关键词：</label>
      <input type="text" id="search-query" placeholder="输入关键词" style="width:220px">
      <label>采集数量：</label>
      <input type="number" id="search-num" value="10" min="1" max="1000" style="width:100px">
    </div>

    <div class="field-group">
      <label style="color:#888;font-size:13px">筛选条件</label>
      <div class="section">
        <label>排序方式</label>
        <div class="radio-group">
          <label><input type="radio" name="sort" value="0" checked><span>综合</span></label>
          <label><input type="radio" name="sort" value="1"><span>最新</span></label>
          <label><input type="radio" name="sort" value="2"><span>最多点赞</span></label>
          <label><input type="radio" name="sort" value="3"><span>最多评论</span></label>
          <label><input type="radio" name="sort" value="4"><span>最多收藏</span></label>
        </div>
      </div>
      <div class="row" style="gap:24px">
        <div>
          <label>笔记类型</label>
          <div class="radio-group">
            <label><input type="radio" name="ntype" value="0" checked><span>不限</span></label>
            <label><input type="radio" name="ntype" value="1"><span>视频</span></label>
            <label><input type="radio" name="ntype" value="2"><span>图文</span></label>
          </div>
        </div>
        <div>
          <label>时间范围</label>
          <div class="radio-group">
            <label><input type="radio" name="ntime" value="0" checked><span>不限</span></label>
            <label><input type="radio" name="ntime" value="1"><span>一天内</span></label>
            <label><input type="radio" name="ntime" value="2"><span>一周内</span></label>
            <label><input type="radio" name="ntime" value="3"><span>半年内</span></label>
          </div>
        </div>
      </div>
    </div>

    <div class="section">
      <label>保存方式</label>
      <div class="radio-group">
        <label><input type="radio" name="search-save" value="all" checked><span>全部保存</span></label>
        <label><input type="radio" name="search-save" value="media"><span>仅媒体</span></label>
        <label><input type="radio" name="search-save" value="media-image"><span>仅图片</span></label>
        <label><input type="radio" name="search-save" value="media-video"><span>仅视频</span></label>
        <label><input type="radio" name="search-save" value="excel"><span>仅Excel</span></label>
      </div>
    </div>
    <div class="row" style="margin-top:16px">
      <button class="btn" onclick="startSearch()">开始搜索采集</button>
    </div>
  </div>

  <!-- Log -->
  <div class="log-box">
    <div class="log-header">
      <h3>运行日志</h3>
      <span class="status idle" id="status-badge">就绪</span>
    </div>
    <div id="log"></div>
    <div class="log-actions">
      <button class="btn-sm" onclick="clearLog()">清空日志</button>
      <button class="btn-sm" onclick="openData()">打开数据目录</button>
    </div>
  </div>
</div>

<script>
  function switchTab(idx) {
    document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', i===idx));
    document.querySelectorAll('.panel').forEach((p,i) => p.classList.toggle('active', i===idx));
  }

  function getRadio(name) { const el = document.querySelector(`input[name="${name}"]:checked`); return el ? el.value : ''; }

  function api(url, data) {
    return fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) }).then(r=>r.json());
  }

  function saveCookies() {
    api('/api/save_cookies', { cookies: document.getElementById('cookies').value }).then(r => { alert(r.msg); });
  }

  function startNote() {
    const urls = document.getElementById('note-urls').value.trim();
    if (!urls) return alert('请输入笔记链接');
    api('/api/spider_notes', {
      urls: urls, save_choice: getRadio('note-save'),
      excel_name: document.getElementById('note-excel').value || '笔记数据',
      cookies: document.getElementById('cookies').value,
      proxy: document.getElementById('proxy').value
    }).then(r => { if(!r.success) alert(r.msg); });
  }

  function startUser() {
    const url = document.getElementById('user-url').value.trim();
    if (!url) return alert('请输入用户链接');
    api('/api/spider_user', {
      url: url, save_choice: getRadio('user-save'),
      cookies: document.getElementById('cookies').value,
      proxy: document.getElementById('proxy').value
    }).then(r => { if(!r.success) alert(r.msg); });
  }

  function startSearch() {
    const query = document.getElementById('search-query').value.trim();
    if (!query) return alert('请输入搜索关键词');
    api('/api/spider_search', {
      query: query,
      num: parseInt(document.getElementById('search-num').value) || 10,
      sort: parseInt(getRadio('sort')),
      note_type: parseInt(getRadio('ntype')),
      note_time: parseInt(getRadio('ntime')),
      save_choice: getRadio('search-save'),
      cookies: document.getElementById('cookies').value,
      proxy: document.getElementById('proxy').value
    }).then(r => { if(!r.success) alert(r.msg); });
  }

  function clearLog() { document.getElementById('log').textContent = ''; }
  function openData() { fetch('/api/open_data'); }

  // 轮询日志
  let logIndex = 0;
  setInterval(() => {
    fetch(`/api/logs?since=${logIndex}`).then(r=>r.json()).then(data => {
      if (data.logs.length > 0) {
        const el = document.getElementById('log');
        el.textContent += data.logs.join('\n') + '\n';
        el.scrollTop = el.scrollHeight;
        logIndex = data.index;
      }
      const badge = document.getElementById('status-badge');
      badge.textContent = data.status;
      badge.className = 'status ' + (data.running ? 'running' : 'idle');
    });
  }, 800);

  // 加载已保存的 cookies
  fetch('/api/load_cookies').then(r=>r.json()).then(data => {
    if (data.cookies) document.getElementById('cookies').value = data.cookies;
  });
</script>
</body>
</html>
"""


# ── API Routes ──────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/load_cookies")
def load_cookies():
    try:
        from dotenv import load_dotenv
        load_dotenv(resource_path(".env"), override=True)
        cookies = os.getenv("COOKIES", "")
        return jsonify({"cookies": cookies})
    except Exception:
        return jsonify({"cookies": ""})


@app.route("/api/save_cookies", methods=["POST"])
def save_cookies():
    data = request.json
    cookies = data.get("cookies", "").strip()
    env_path = resource_path(".env")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f"COOKIES='{cookies}'\n")
    logger.info("Cookies 已保存")
    return jsonify({"success": True, "msg": "Cookies 已保存"})


@app.route("/api/spider_notes", methods=["POST"])
def spider_notes():
    data = request.json
    cookies = data.get("cookies", "").strip()
    if not cookies:
        return jsonify({"success": False, "msg": "请先配置 Cookies"})
    urls = [u.strip() for u in data["urls"].splitlines() if u.strip()]
    if not urls:
        return jsonify({"success": False, "msg": "请输入笔记链接"})
    proxy = data.get("proxy", "").strip()
    proxies = {"http": proxy, "https": proxy} if proxy else None

    ok, msg = run_task(
        lambda: spider.spider_some_note(
            urls, cookies, get_base_path(),
            data.get("save_choice", "all"),
            data.get("excel_name", "笔记数据"),
            proxies
        ),
        f"采集 {len(urls)} 篇笔记"
    )
    return jsonify({"success": ok, "msg": msg})


@app.route("/api/spider_user", methods=["POST"])
def spider_user():
    data = request.json
    cookies = data.get("cookies", "").strip()
    if not cookies:
        return jsonify({"success": False, "msg": "请先配置 Cookies"})
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"success": False, "msg": "请输入用户链接"})
    proxy = data.get("proxy", "").strip()
    proxies = {"http": proxy, "https": proxy} if proxy else None

    ok, msg = run_task(
        lambda: spider.spider_user_all_note(
            url, cookies, get_base_path(),
            data.get("save_choice", "all"),
            proxies=proxies
        ),
        "采集用户全部笔记"
    )
    return jsonify({"success": ok, "msg": msg})


@app.route("/api/spider_search", methods=["POST"])
def spider_search():
    data = request.json
    cookies = data.get("cookies", "").strip()
    if not cookies:
        return jsonify({"success": False, "msg": "请先配置 Cookies"})
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"success": False, "msg": "请输入搜索关键词"})
    proxy = data.get("proxy", "").strip()
    proxies = {"http": proxy, "https": proxy} if proxy else None

    ok, msg = run_task(
        lambda: spider.spider_some_search_note(
            query, data.get("num", 10), cookies, get_base_path(),
            data.get("save_choice", "all"),
            data.get("sort", 0),
            data.get("note_type", 0),
            data.get("note_time", 0),
            proxies=proxies
        ),
        f"搜索「{query}」采集 {data.get('num', 10)} 篇"
    )
    return jsonify({"success": ok, "msg": msg})


@app.route("/api/logs")
def get_logs():
    since = int(request.args.get("since", 0))
    logs = list(log_buffer)
    new_logs = logs[since:]
    return jsonify({
        "logs": new_logs,
        "index": len(logs),
        "status": task_status["message"],
        "running": task_status["running"]
    })


@app.route("/api/open_data")
def open_data():
    bp = get_base_path()
    data_dir = os.path.dirname(bp["media"])
    if sys.platform == "win32":
        os.startfile(data_dir)
    elif sys.platform == "darwin":
        os.system(f'open "{data_dir}"')
    else:
        os.system(f'xdg-open "{data_dir}"')
    return jsonify({"success": True})


# ── 启动 ──────────────────────────────────────────────

def main():
    port = 5000
    for p in range(5000, 5010):
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                port = p
                break

    print(f"\n{'='*50}")
    print(f"  小红书数据采集工具已启动")
    print(f"  请在浏览器中打开: http://127.0.0.1:{port}")
    print(f"  按 Ctrl+C 停止")
    print(f"{'='*50}\n")

    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()
