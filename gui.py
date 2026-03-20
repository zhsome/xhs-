# encoding: utf-8
"""
小红书数据采集工具 - GUI版
基于 Spider_XHS 项目，提供图形化操作界面
"""

import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from loguru import logger

from main import Data_Spider
from xhs_utils.common_util import init


class LogHandler:
    """将 loguru 日志重定向到 tkinter Text 组件"""

    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.after(0, self._append, message)

    def _append(self, message):
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")

    def flush(self):
        pass


class XHSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("小红书数据采集工具")
        self.root.geometry("960x720")
        self.root.minsize(800, 600)

        # 初始化后端
        self.data_spider = Data_Spider()
        self._init_paths()

        # 运行状态
        self.running = False

        # 构建界面
        self._build_ui()

        # 配置日志输出到文本框
        logger.remove()
        log_handler = LogHandler(self.log_text)
        logger.add(log_handler, format="{time:HH:mm:ss} | {level} | {message}")
        logger.add(sys.stderr, format="{time:HH:mm:ss} | {level} | {message}")

        logger.info("小红书数据采集工具已启动，请先配置 Cookies")

    def _init_paths(self):
        """初始化保存路径"""
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "datas"))
        self.media_path = os.path.join(base, "media_datas")
        self.excel_path = os.path.join(base, "excel_datas")
        for p in [self.media_path, self.excel_path]:
            os.makedirs(p, exist_ok=True)

    def _base_path(self):
        return {"media": self.media_path, "excel": self.excel_path}

    # ── 界面构建 ──────────────────────────────────────────────

    def _build_ui(self):
        # 主容器
        main = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 上半部分：操作区
        top_frame = ttk.Frame(main)
        main.add(top_frame, weight=3)

        # 下半部分：日志区
        bottom_frame = ttk.LabelFrame(main, text="运行日志")
        main.add(bottom_frame, weight=2)

        self._build_top(top_frame)
        self._build_log(bottom_frame)

    def _build_top(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Cookies 配置
        self._build_cookie_tab(notebook)
        # Tab 2: 采集笔记
        self._build_note_tab(notebook)
        # Tab 3: 采集用户笔记
        self._build_user_tab(notebook)
        # Tab 4: 搜索采集
        self._build_search_tab(notebook)

    # ── Cookies 配置 ──

    def _build_cookie_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="  Cookies 配置  ")

        ttk.Label(frame, text="请将浏览器中的小红书 Cookies 粘贴到下方：").pack(anchor=tk.W)
        ttk.Label(frame, text="（获取方式：浏览器 F12 → Network → 任意请求 → Request Headers → Cookie）",
                  foreground="gray").pack(anchor=tk.W, pady=(0, 5))

        self.cookies_text = scrolledtext.ScrolledText(frame, height=8, wrap=tk.WORD)
        self.cookies_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # 尝试从 .env 加载
        try:
            from dotenv import load_dotenv
            load_dotenv()
            env_cookies = os.getenv("COOKIES", "")
            if env_cookies:
                self.cookies_text.insert(tk.END, env_cookies)
        except Exception:
            pass

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="保存到 .env", command=self._save_cookies).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空", command=lambda: self.cookies_text.delete("1.0", tk.END)).pack(side=tk.LEFT)

        # 代理设置
        proxy_frame = ttk.LabelFrame(frame, text="代理设置（可选）", padding=5)
        proxy_frame.pack(fill=tk.X, pady=5)
        ttk.Label(proxy_frame, text="HTTP 代理：").pack(side=tk.LEFT)
        self.proxy_entry = ttk.Entry(proxy_frame, width=40)
        self.proxy_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(proxy_frame, text="例: http://127.0.0.1:7890", foreground="gray").pack(side=tk.LEFT)

    def _save_cookies(self):
        cookies = self.cookies_text.get("1.0", tk.END).strip()
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"COOKIES='{cookies}'\n")
        logger.info("Cookies 已保存到 .env 文件")

    def _get_cookies(self):
        return self.cookies_text.get("1.0", tk.END).strip()

    def _get_proxies(self):
        proxy = self.proxy_entry.get().strip()
        if proxy:
            return {"http": proxy, "https": proxy}
        return None

    # ── 采集笔记 ──

    def _build_note_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="  采集笔记  ")

        ttk.Label(frame, text="笔记链接（每行一个）：").pack(anchor=tk.W)
        ttk.Label(frame, text="支持 xiaohongshu.com/explore/... 格式的链接",
                  foreground="gray").pack(anchor=tk.W, pady=(0, 5))

        self.note_urls_text = scrolledtext.ScrolledText(frame, height=8, wrap=tk.WORD)
        self.note_urls_text.pack(fill=tk.BOTH, expand=True, pady=5)

        opt_frame = ttk.Frame(frame)
        opt_frame.pack(fill=tk.X, pady=5)

        ttk.Label(opt_frame, text="保存方式：").pack(side=tk.LEFT)
        self.note_save_var = tk.StringVar(value="all")
        save_options = [("全部保存", "all"), ("仅媒体", "media"), ("仅图片", "media-image"),
                        ("仅视频", "media-video"), ("仅Excel", "excel")]
        for text, val in save_options:
            ttk.Radiobutton(opt_frame, text=text, variable=self.note_save_var, value=val).pack(side=tk.LEFT, padx=4)

        name_frame = ttk.Frame(frame)
        name_frame.pack(fill=tk.X, pady=2)
        ttk.Label(name_frame, text="Excel 文件名：").pack(side=tk.LEFT)
        self.note_excel_name = ttk.Entry(name_frame, width=30)
        self.note_excel_name.insert(0, "笔记数据")
        self.note_excel_name.pack(side=tk.LEFT, padx=5)

        ttk.Button(frame, text="开始采集", command=self._start_note_spider).pack(pady=8)

    def _start_note_spider(self):
        urls_raw = self.note_urls_text.get("1.0", tk.END).strip()
        if not urls_raw:
            messagebox.showwarning("提示", "请输入笔记链接")
            return
        urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]
        cookies = self._get_cookies()
        if not cookies:
            messagebox.showwarning("提示", "请先配置 Cookies")
            return
        save_choice = self.note_save_var.get()
        excel_name = self.note_excel_name.get().strip() or "笔记数据"

        self._run_task(
            lambda: self.data_spider.spider_some_note(
                urls, cookies, self._base_path(), save_choice, excel_name, self._get_proxies()
            ),
            f"采集 {len(urls)} 篇笔记"
        )

    # ── 采集用户笔记 ──

    def _build_user_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="  用户笔记采集  ")

        ttk.Label(frame, text="用户主页链接：").pack(anchor=tk.W)
        ttk.Label(frame, text="格式: https://www.xiaohongshu.com/user/profile/...",
                  foreground="gray").pack(anchor=tk.W, pady=(0, 5))

        url_frame = ttk.Frame(frame)
        url_frame.pack(fill=tk.X, pady=5)
        self.user_url_entry = ttk.Entry(url_frame)
        self.user_url_entry.pack(fill=tk.X)

        opt_frame = ttk.Frame(frame)
        opt_frame.pack(fill=tk.X, pady=5)
        ttk.Label(opt_frame, text="保存方式：").pack(side=tk.LEFT)
        self.user_save_var = tk.StringVar(value="all")
        for text, val in [("全部保存", "all"), ("仅媒体", "media"), ("仅图片", "media-image"),
                          ("仅视频", "media-video"), ("仅Excel", "excel")]:
            ttk.Radiobutton(opt_frame, text=text, variable=self.user_save_var, value=val).pack(side=tk.LEFT, padx=4)

        ttk.Button(frame, text="开始采集该用户全部笔记", command=self._start_user_spider).pack(pady=8)

    def _start_user_spider(self):
        user_url = self.user_url_entry.get().strip()
        if not user_url:
            messagebox.showwarning("提示", "请输入用户主页链接")
            return
        cookies = self._get_cookies()
        if not cookies:
            messagebox.showwarning("提示", "请先配置 Cookies")
            return
        save_choice = self.user_save_var.get()

        self._run_task(
            lambda: self.data_spider.spider_user_all_note(
                user_url, cookies, self._base_path(), save_choice, proxies=self._get_proxies()
            ),
            f"采集用户笔记"
        )

    # ── 搜索采集 ──

    def _build_search_tab(self, notebook):
        frame = ttk.Frame(notebook, padding=10)
        notebook.add(frame, text="  搜索采集  ")

        # 搜索关键词
        row1 = ttk.Frame(frame)
        row1.pack(fill=tk.X, pady=3)
        ttk.Label(row1, text="搜索关键词：").pack(side=tk.LEFT)
        self.search_query_entry = ttk.Entry(row1, width=30)
        self.search_query_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text="采集数量：").pack(side=tk.LEFT, padx=(15, 0))
        self.search_num_var = tk.StringVar(value="10")
        ttk.Spinbox(row1, from_=1, to=1000, textvariable=self.search_num_var, width=8).pack(side=tk.LEFT, padx=5)

        # 筛选条件
        filter_frame = ttk.LabelFrame(frame, text="筛选条件", padding=8)
        filter_frame.pack(fill=tk.X, pady=8)

        # 排序方式
        r1 = ttk.Frame(filter_frame)
        r1.pack(fill=tk.X, pady=2)
        ttk.Label(r1, text="排序方式：").pack(side=tk.LEFT)
        self.sort_var = tk.StringVar(value="0")
        for text, val in [("综合", "0"), ("最新", "1"), ("最多点赞", "2"), ("最多评论", "3"), ("最多收藏", "4")]:
            ttk.Radiobutton(r1, text=text, variable=self.sort_var, value=val).pack(side=tk.LEFT, padx=3)

        # 笔记类型
        r2 = ttk.Frame(filter_frame)
        r2.pack(fill=tk.X, pady=2)
        ttk.Label(r2, text="笔记类型：").pack(side=tk.LEFT)
        self.note_type_var = tk.StringVar(value="0")
        for text, val in [("不限", "0"), ("视频", "1"), ("图文", "2")]:
            ttk.Radiobutton(r2, text=text, variable=self.note_type_var, value=val).pack(side=tk.LEFT, padx=3)

        # 时间范围
        ttk.Label(r2, text="    时间：").pack(side=tk.LEFT)
        self.note_time_var = tk.StringVar(value="0")
        for text, val in [("不限", "0"), ("一天内", "1"), ("一周内", "2"), ("半年内", "3")]:
            ttk.Radiobutton(r2, text=text, variable=self.note_time_var, value=val).pack(side=tk.LEFT, padx=3)

        # 保存方式
        opt_frame = ttk.Frame(frame)
        opt_frame.pack(fill=tk.X, pady=5)
        ttk.Label(opt_frame, text="保存方式：").pack(side=tk.LEFT)
        self.search_save_var = tk.StringVar(value="all")
        for text, val in [("全部保存", "all"), ("仅媒体", "media"), ("仅图片", "media-image"),
                          ("仅视频", "media-video"), ("仅Excel", "excel")]:
            ttk.Radiobutton(opt_frame, text=text, variable=self.search_save_var, value=val).pack(side=tk.LEFT, padx=4)

        ttk.Button(frame, text="开始搜索采集", command=self._start_search_spider).pack(pady=8)

    def _start_search_spider(self):
        query = self.search_query_entry.get().strip()
        if not query:
            messagebox.showwarning("提示", "请输入搜索关键词")
            return
        cookies = self._get_cookies()
        if not cookies:
            messagebox.showwarning("提示", "请先配置 Cookies")
            return
        try:
            num = int(self.search_num_var.get())
        except ValueError:
            messagebox.showwarning("提示", "采集数量必须是数字")
            return

        save_choice = self.search_save_var.get()
        sort_type = int(self.sort_var.get())
        note_type = int(self.note_type_var.get())
        note_time = int(self.note_time_var.get())

        self._run_task(
            lambda: self.data_spider.spider_some_search_note(
                query, num, cookies, self._base_path(), save_choice,
                sort_type, note_type, note_time,
                proxies=self._get_proxies()
            ),
            f"搜索「{query}」采集 {num} 篇笔记"
        )

    # ── 日志区 ──

    def _build_log(self, parent):
        self.log_text = scrolledtext.ScrolledText(parent, state="disabled", wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Button(btn_frame, text="清空日志", command=self._clear_log).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="打开数据目录", command=self._open_data_dir).pack(side=tk.LEFT, padx=5)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(btn_frame, textvariable=self.status_var, foreground="blue").pack(side=tk.RIGHT)

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    def _open_data_dir(self):
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "datas"))
        os.makedirs(data_dir, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(data_dir)
        elif sys.platform == "darwin":
            os.system(f'open "{data_dir}"')
        else:
            os.system(f'xdg-open "{data_dir}"')

    # ── 任务执行 ──

    def _run_task(self, task_func, description):
        if self.running:
            messagebox.showinfo("提示", "有任务正在运行，请等待完成")
            return
        self.running = True
        self.status_var.set(f"运行中：{description}")
        logger.info(f"开始任务：{description}")

        def wrapper():
            try:
                task_func()
                logger.info(f"任务完成：{description}")
                self.status_var.set("就绪 - 任务完成")
            except Exception as e:
                logger.error(f"任务失败：{e}")
                self.status_var.set("就绪 - 任务失败")
            finally:
                self.running = False

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()


def main():
    root = tk.Tk()
    app = XHSApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
