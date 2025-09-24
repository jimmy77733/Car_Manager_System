# main.py
import customtkinter as ctk
from datetime import datetime
import database as db
import json
import textwrap

import sqlite3
from database import DB_FILE

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter  # 日期格式化器[1]
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
#任何未被捕捉的例外都會顯示錯誤對話框，避免程式默默崩潰
import sys, traceback
def global_exception_handler(exc_type, exc_value, exc_traceback):
    err = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    from tkinter import messagebox
    messagebox.showerror("未捕捉例外", err)
sys.excepthook = global_exception_handler

import threading
import time
from tkinter import ttk


class SplashScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)  # 無邊框
        self.geometry("400x200+500+300")  # 固定大小與位置
        ctk.CTkLabel(self, text="歡迎使用\n汽車管理系統", font=("Arial", 20, "bold")).pack(pady=20)
        self.progress = ttk.Progressbar(self, mode="determinate", length=300)
        self.progress.pack(pady=20)
        self.update()

    def update_progress(self, value):
        self.progress['value'] = value
        self.update()


# 設定中文字體支援
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


def get_monthly_stats(customer_id):
    conn = sqlite3.connect(DB_FILE)
    # 直接回傳標準日期格式
    df = pd.read_sql_query(f"""             
            SELECT 
                date(substr(repair_date,1,7) || '-01') AS month_dt,
                COUNT(*)           AS count,
                SUM(amount)        AS total
            FROM repairs
            WHERE customer_id={customer_id}
            GROUP BY month_dt
            ORDER BY month_dt ASC
    """, conn)
    # 解析時指定格式，加快速度並避免警告
    df['month_dt'] = pd.to_datetime(df['month_dt'], format='%Y-%m-%d')
    return df

class CustomInputDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, text, font):
        super().__init__(parent)
        self.title(title)
        self.geometry("500x250")
        self.transient(parent)
        self.grab_set()
        self._user_input = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        self._label = ctk.CTkLabel(main_frame, text=text, font=font, wraplength=450)
        self._label.pack(pady=10, padx=10, expand=True)
        self._entry = ctk.CTkEntry(main_frame, font=font)
        self._entry.pack(pady=10, padx=10, fill="x")
        self._entry.focus()
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(pady=10)
        self._ok_button = ctk.CTkButton(button_frame, text="確認", command=self._ok_event)
        self._ok_button.pack(side="left", padx=10)
        self._cancel_button = ctk.CTkButton(button_frame, text="取消", command=self._cancel_event)
        self._cancel_button.pack(side="left", padx=10)
        self.bind("<Return>", self._ok_event)

    def _ok_event(self, event=None):
        self._user_input = self._entry.get()
        self.destroy()

    def _cancel_event(self):
        self._user_input = None
        self.destroy()

    def get_input(self):
        self.wait_window()
        return self._user_input


class SuccessDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="成功", message="操作已成功完成。"):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        ctk.CTkLabel(self, text=message, font=("Microsoft JhengHei UI", 18)).pack(pady=20, padx=20)
        ctk.CTkButton(self, text="確認", command=self.destroy, font=("Microsoft JhengHei UI", 16)).pack(pady=10)


class CalculatorDialog(ctk.CTkToplevel):
    def __init__(self, parent, target_entry):
        super().__init__(parent)
        self.target_entry = target_entry
        self.title("簡易計算機")
        self.geometry("300x400")
        self.transient(parent)
        self.grab_set()
        self.expression = ""
        self.display_var = ctk.StringVar()
        display_label = ctk.CTkEntry(self, textvariable=self.display_var, font=("Arial", 24), justify="right",
                                     state="readonly")
        display_label.pack(fill="x", padx=10, pady=10, ipady=10)
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="both", expand=True, padx=10, pady=10)
        buttons = ['7', '8', '9', '/', '4', '5', '6', '*', '1', '2', '3', '-', 'C', '0', '=', '+']
        for i, text in enumerate(buttons):
            row, col = divmod(i, 4)
            button_frame.grid_rowconfigure(row, weight=1)
            button_frame.grid_columnconfigure(col, weight=1)
            ctk.CTkButton(button_frame, text=text, font=("Arial", 18),
                          command=lambda t=text: self.on_button_click(t)).grid(row=row, column=col, sticky="nsew",
                                                                               padx=2, pady=2)

    def on_button_click(self, char):
        if char == 'C':
            self.expression = ""
        elif char == '=':
            try:
                if len(self.expression) > 40:
                    self.expression = "錯誤"
                else:
                    self.expression = str(round(eval(self.expression), 4))
            except:
                self.expression = "錯誤"
        else:
            if self.expression == "錯誤":
                self.expression = ""
            self.expression += str(char)
        self.display_var.set(self.expression)
        if char == '=' and self.expression != "錯誤":
            self.target_entry.delete(0, 'end')
            self.target_entry.insert(0, self.expression)
            self.after(200, self.destroy)


class CustomerWindow(ctk.CTkToplevel):
    def __init__(self, parent, customer_id, base_font_size, app):
        super().__init__(parent)
        self.parent = parent
        self.customer_id = customer_id
        self.base_font_size = base_font_size
        self.app = app
        self.update_font_definitions()
        self.title("客戶資料與維修紀錄")
        # 立即進入全螢幕模式
        self.attributes('-fullscreen', True)
        self.transient(parent)
        self.grab_set()
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        try:
            self.customer_data = db.get_customer_by_id(self.customer_id)
            if not self.customer_data:
                raise ValueError("找不到該客戶資料")
        except Exception as e:
            ctk.CTkMessageBox(title="讀取客戶資料失敗", message=str(e))
            self.destroy()
            return

        self.title(f"{self.customer_data['name']} 的資料頁面")
        self.static_font_widgets = []

        info_frame = ctk.CTkFrame(self)
        info_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        info_frame.grid_columnconfigure(0, weight=1)

        self.info_label_header = ctk.CTkLabel(info_frame, text="客戶基本資料")
        self.info_label_header.pack(anchor="w", padx=10, pady=(5, 0))
        self.static_font_widgets.append(self.info_label_header)
        self.name_label = ctk.CTkLabel(info_frame, text=f"姓名: {self.customer_data['name']}")
        self.name_label.pack(anchor="w", padx=10)
        self.static_font_widgets.append(self.name_label)
        self.model_label = ctk.CTkLabel(info_frame, text=f"車型: {self.customer_data['car_model']}")
        self.model_label.pack(anchor="w", padx=10)
        self.static_font_widgets.append(self.model_label)
        self.contact_label = ctk.CTkLabel(info_frame, text=f"聯絡資訊: {self.customer_data['contact_info']}")
        self.contact_label.pack(anchor="w", padx=10, pady=(0, 5))
        self.static_font_widgets.append(self.contact_label)

        #編輯客戶資料與刪除客戶資料按鈕
        self.edit_customer_btn = ctk.CTkButton(info_frame, text="編輯客戶資料", command=self.edit_customer_info)
        self.edit_customer_btn.pack(side="left", padx=10, pady=5)
        self.static_font_widgets.append(self.edit_customer_btn)
        self.delete_customer_btn = ctk.CTkButton(info_frame, text="刪除此客戶", fg_color="red", hover_color="darkred",
                                                 command=self.delete_customer)
        self.delete_customer_btn.pack(side="left", padx=10, pady=5)
        self.static_font_widgets.append(self.delete_customer_btn)
        #顯示圖表按鈕
        self.show_chart_btn = ctk.CTkButton(
            info_frame,
            text="顯示圖表",
            font=self.font_normal,
            fg_color="#4CAF50",  # 綠色背景區別
            hover_color="#45A049",
            command=self.open_chart_window
        )
        self.show_chart_btn.pack(side="left", padx=10, pady=5)
        self.static_font_widgets.append(self.show_chart_btn)
        # 圖表樣式參數初始化
        self.marker_var = ctk.StringVar(value='圓點')
        self.linestyle_var = ctk.StringVar(value='實線')

        #顯示下拉式選單
        self.chart_type_var = ctk.StringVar(value='長條圖')  # 預設長柱圖
        chart_type_menu = ctk.CTkOptionMenu(
            info_frame,
            values=['長條圖', '圓餅圖', '折線圖'],  # 三種圖表類型
            variable=self.chart_type_var
        )
        chart_type_menu.pack(side="left", padx=5, pady=5)
        self.static_font_widgets.append(chart_type_menu)

        # 年分下拉式選單
        stats = get_monthly_stats(self.customer_id)
        raw_months = stats['month_dt'].dropna()
        years = sorted(raw_months.dt.year.unique().tolist())

        if not years:
            # 無任何維修紀錄，使用當前年份並停用圖表按鈕
            years = [datetime.now().year]
            self.show_chart_btn.configure(state="disabled")

        self.year_var = ctk.StringVar(value=str(years[0]))
        year_menu = ctk.CTkOptionMenu(
            info_frame,
            values=[str(y) for y in years],
            variable=self.year_var
        )
        year_menu.pack(side="left", padx=5, pady=5)
        self.static_font_widgets.append(year_menu)

        # 僅在當前年份且無任何資料時停用年份選單
        if len(years) == 1 and years[0] == datetime.now().year and stats.empty:
            year_menu.configure(state="disabled")

        repair_frame = ctk.CTkFrame(self)
        repair_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        repair_frame.grid_rowconfigure(1, weight=1)
        repair_frame.grid_columnconfigure(0, weight=1)
        repair_header_frame = ctk.CTkFrame(repair_frame, fg_color="transparent")
        repair_header_frame.grid(row=0, column=0, sticky="ew", pady=5, padx=10)
        self.repair_label_header = ctk.CTkLabel(repair_header_frame, text="維修歷史紀錄")
        self.repair_label_header.pack(side="left")
        self.static_font_widgets.append(self.repair_label_header)
        self.add_repair_btn = ctk.CTkButton(repair_header_frame, text="新增維修紀錄", command=self.open_repair_dialog)
        self.add_repair_btn.pack(side="right")
        self.static_font_widgets.append(self.add_repair_btn)

        self.scrollable_frame = ctk.CTkScrollableFrame(repair_frame)
        self.scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        # 設定區域框架
        settings_frame = ctk.CTkFrame(self, height=60)
        settings_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        settings_frame.grid_columnconfigure(0, weight=1)
        settings_frame.grid_rowconfigure(0, weight=1)
        settings_frame.pack_propagate(False)
        settings_frame.grid_columnconfigure(0, weight=1)
        settings_frame.grid_rowconfigure(0, weight=1)

        # 字體調整框架（左側）
        font_frame = ctk.CTkFrame(settings_frame)
        font_frame.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        self.font_size_label = ctk.CTkLabel(font_frame, text="調整整體字體大小: ")
        self.font_size_label.pack(side="left", padx=5)
        decrease_font_button = ctk.CTkButton(font_frame, text="-", width=40, height=40,
                                             command=self.decrease_font_size)
        decrease_font_button.pack(side="left")
        increase_font_button = ctk.CTkButton(font_frame, text="+", width=40, height=40,
                                             command=self.increase_font_size)
        increase_font_button.pack(side="left", padx=(5, 0))
        self.static_font_widgets.append(self.font_size_label)
        self.static_font_widgets.append(decrease_font_button)
        self.static_font_widgets.append(increase_font_button)
        self.load_repairs()
        self.update_all_widget_fonts()

        # 按鈕框架（右側）
        button_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        button_frame.grid(row=0, column=1, sticky="e", padx=10)  # 使用 grid 佈局

        #退出全螢幕按鈕
        exit_full_btn = ctk.CTkButton(
             button_frame,
             text="退出全螢幕",
             command=self.exit_fullscreen,
              width=120,  # 加大寬度
              height=50,  # 加大高度
               font=self.font_bold,  # 使用粗體字
              fg_color="#FF5555",  # 醒目的紅色
               hover_color="#FF0000"
                 )
         # 放置在右上角 (距離右邊10像素，頂部10像素)
        exit_full_btn.pack(side="left", padx=5)  # 在按鈕框架內使用 pack

        # 新增開啟全螢幕按鈕
        enter_full_btn = ctk.CTkButton(
            button_frame,
            text="開啟全螢幕",
            command=self.enter_fullscreen,  # 綁定新方法
            width=120,
            height=50,
            font=self.font_bold,
            fg_color="#5555FF",  # 藍色區分功能
            hover_color="#0000FF"
        )
        enter_full_btn.pack(side="left", padx=5)

        # 將按鈕加入字體調整列表
        self.static_font_widgets.append(exit_full_btn)
        self.static_font_widgets.append(enter_full_btn)
        # 添加視窗大小變化時的響應
        self.bind("<Configure>", self.on_resize)
        # 綁定按鍵事件
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)
        #圖示視窗

    def open_chart_window(self):
        # 建立視窗
        self.chart_win = ctk.CTkToplevel(self)
        # self.chart_win.geometry("1300x700")
        self.chart_win.resizable(True, True)
        self.chart_win.attributes('-topmost', True)

        # 年分解析
        year_str = self.year_var.get()
        try:
            year = int(year_str)
        except ValueError:
            ctk.CTkMessageBox(title="錯誤", message="年份格式錯誤，請重新選擇")
            return

        # 取得並篩選該年資料
        df = get_monthly_stats(self.customer_id)
        df = df[df['month_dt'].dt.year == year]

        # 補齊該年所有月份
        months = pd.date_range(f"{year}-01-01", f"{year}-12-01", freq='MS')
        self.df_full = pd.DataFrame({'month_dt': months}).merge(df, on='month_dt', how='left').fillna(0)

        # 建立畫布與主軸
        # 根據圖表類型繪圖
        # 獲取圖表類型並轉換為英文
        chart_type_chinese = self.chart_type_var.get()
        chart_type_mapping = {
            '長條圖': 'bar',
            '圓餅圖': 'pie',
            '折線圖': 'line'
        }
        chart_type = chart_type_mapping.get(chart_type_chinese, 'bar')

        # 根據圖表類型建立不同的子圖佈局
        if chart_type in ['bar', 'line', 'pie']:  # 圓餅圖也使用雙子圖
            # 對於圓餅圖，使用水平排列 (1, 2)
            if chart_type == 'pie':
                self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(12, 6), dpi=100)
            else:
                # 其他線圖使用垂直排列 (2, 1)
                self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 8), dpi=100)

        # 格式化X軸（僅針對長條圖和折線圖）
        if chart_type in ['bar', 'line']:
            for ax in [self.ax1, self.ax2]:
                ax.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
                ax.grid(True)
            self.fig.autofmt_xdate(rotation=45)

        if chart_type == 'bar':
            # 次數圖 (上方)
            self.ax1.bar(self.df_full['month_dt'], self.df_full['count'], color='tab:blue', label='次數')
            self.ax1.set_title('每月維修次數')
            self.ax1.legend()

            # 金額圖 (下方)
            self.ax2.bar(self.df_full['month_dt'], self.df_full['total'], color='tab:orange', label='金額')
            self.ax2.set_title('每月維修金額')
            self.ax2.legend()

        elif chart_type == 'line':
            # 次數折線
            self.ax1.plot(self.df_full['month_dt'], self.df_full['count'],
                          marker=self.marker_conversion(),
                          linestyle=self.linestyle_conversion(),
                          color='tab:blue', label='次數')
            self.ax1.set_title('每月維修次數')

            # 金額折線
            self.ax2.plot(self.df_full['month_dt'], self.df_full['total'],
                          marker=self.marker_conversion(),
                          linestyle=self.linestyle_conversion(),
                          color='tab:orange', label='金額')
            self.ax2.set_title('每月維修金額')


        elif chart_type == 'pie':
            threshold = 3.0  # 小於3%隱藏標籤
            self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=100)
            # 使用水平兩子圖佈局
            # 左側顯示「次數」，右側顯示「金額」
            # 次數圓餅圖
            labels = self.df_full['month_dt'].dt.strftime('%m') # 月份標籤，只取月份數字
            sizes_count = self.df_full['count']
            non_zero_mask_count = sizes_count > 0
            if non_zero_mask_count.any():
                wedges1, texts1, autotexts1 = self.ax1.pie(
                    sizes_count[non_zero_mask_count],
                    autopct=lambda pct: f'{pct:.1f}%' if pct > threshold else '',
                    startangle=90,
                    labels=None  # 移除標籤
                )
                self.ax1.set_title('每月維修次數分布')
                # 添加圖例，放置在圓餅圖右側
                self.ax1.legend(wedges1,
                                labels[non_zero_mask_count],
                                title="月份",
                                loc="center left",
                                bbox_to_anchor=(1.05, 0.5),
                                borderaxespad=0.5,
                                fontsize=10
                                )
            else:
                    self.ax1.text(0.5, 0.5, '無資料可顯示', ha='center', va='center',
                              transform=self.ax1.transAxes, fontsize=16)
            # 金額圓餅圖
            sizes_amount = self.df_full['total']
            non_zero_mask_amount = sizes_amount > 0
            if non_zero_mask_amount.any():
                wedges2, texts2, autotexts2 = self.ax2.pie(
                    sizes_amount[non_zero_mask_amount],
                    autopct=lambda pct: f'{pct:.1f}%' if pct > threshold else '',
                    startangle=90,
                    labels=None  # 移除標籤
                )
                self.ax2.set_title('每月維修金額分布')
                # 添加圖例，放置在圓餅圖右側
                self.ax2.legend(wedges2, labels[non_zero_mask_amount],
                                title="月份",
                                loc="center left",
                                bbox_to_anchor=(1.05, 0.5),
                                borderaxespad=0.5,
                                fontsize=10
                                )
            else:
                    self.ax1.text(0.5, 0.5, '無資料可顯示', ha='center', va='center',
                              transform=self.ax1.transAxes, fontsize=16)
            # 調整子圖與圖例的間距，避免文字截切
            self.fig.subplots_adjust(
                left=0.05,  # 左側邊距
                right=0.8,  # 右側縮些空間給圖例
                wspace=0.4,  # 子圖間距
                top=0.9,
                bottom=0.1
            )
        # 格式化X軸（僅針對雙子圖）
        if chart_type in ['bar', 'line']:
            for ax in [self.ax1, self.ax2]:
                ax.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
                ax.grid(True)
            self.fig.autofmt_xdate(rotation=45)

        self.fig.tight_layout()

        # 嵌入 Canvas
        self.chart_canvas = FigureCanvasTkAgg(self.fig, master=self.chart_win)
        canvas_widget = self.chart_canvas.get_tk_widget()
        canvas_widget.pack(fill="both", expand=True, padx=10, pady=10)

        # 僅在折線圖時顯示樣式控制項
        if chart_type == 'line':
            style_frame = ctk.CTkFrame(self.chart_win)
            style_frame.pack(fill="x", padx=10, pady=5)

            # 標記樣式下拉選單
            marker_menu = ctk.CTkOptionMenu(style_frame, values=['圓點', '方形', '三角形', '菱形', '星形'],
                                            variable=self.marker_var)
            marker_menu.pack(side="left", padx=5)

            # 線條樣式下拉選單
            line_menu = ctk.CTkOptionMenu(style_frame, values=['實線', '虛線', '點虛線', '點線'],
                                          variable=self.linestyle_var)
            line_menu.pack(side="left", padx=5)

            # 套用按鈕
            apply_btn = ctk.CTkButton(style_frame, text="套用樣式", command=self.update_chart_style)
            apply_btn.pack(side="left", padx=10)


        style_frame = ctk.CTkFrame(self.chart_win)

        # 更新 layout 並讀取所需大小
        self.chart_win.update_idletasks()
        w = canvas_widget.winfo_reqwidth()
        h = canvas_widget.winfo_reqheight()
        h += style_frame.winfo_reqheight()  # 加上樣式控制區高度
        margin = 30  # 多留些空間
        # 最後設定視窗 geometry
        self.chart_win.geometry(f"{w + margin}x{h + margin}")

        # self.chart_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        self.chart_canvas.draw()

    def marker_conversion(self):
        return {
            '圓點': 'o',
            '方形': 's',
            '三角形': '^',
            '菱形': 'D',
            '星形': '*'
        }[self.marker_var.get()]

    def linestyle_conversion(self):
        return {
            '實線': '-',
            '虛線': '--',
            '點虛線': '-.',
            '點線': ':'
        }[self.linestyle_var.get()]

    def update_chart_style(self):
        # 獲取當前圖表類型（中文轉英文）
        chart_type_chinese = self.chart_type_var.get()
        chart_type_mapping = {
            '長條圖': 'bar',
            '圓餅圖': 'pie',
            '折線圖': 'line'
        }
        chart_type = chart_type_mapping.get(chart_type_chinese, 'bar')

        if chart_type != 'line':
            return  # 非折線圖不處理

        # 清除並重繪折線圖
        self.ax1.clear()
        self.ax2.clear()

        # 次數折線
        self.ax1.plot(self.df_full['month_dt'], self.df_full['count'],
                      marker=self.marker_conversion(),
                      linestyle=self.linestyle_conversion(),
                      color='tab:blue', label='次數')
        self.ax1.set_title('每月維修次數')
        self.ax1.legend()

        # 金額折線
        self.ax2.plot(self.df_full['month_dt'], self.df_full['total'],
                      marker=self.marker_conversion(),
                      linestyle=self.linestyle_conversion(),
                      color='tab:orange', label='金額')
        self.ax2.set_title('每月維修金額')
        self.ax2.legend()

        # 格式化X軸
        for ax in [self.ax1, self.ax2]:
            ax.xaxis.set_major_formatter(DateFormatter('%Y-%m'))
            ax.grid(True)
        self.fig.autofmt_xdate(rotation=45)
        self.fig.tight_layout()

        self.chart_canvas.draw()

    def enter_fullscreen(self, event=None):
        self.is_fullscreen = True
        self.attributes('-fullscreen', True)
        self.focus_set()  # 確保視窗獲得焦點

        #全螢幕狀態時禁用「開啟」按鈕
    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.attributes('-fullscreen')
        self.attributes('-fullscreen', self.is_fullscreen)
        # 更新按鈕狀態
        enter_full_btn.configure(state="disabled" if self.is_fullscreen else "normal")

    def on_resize(self, event):
        if hasattr(self, 'exit_full_btn'):
        # 保持按鈕在右上角
            self.exit_full_btn.place(relx=1.0, rely=0.0, anchor='ne', x=-10, y=10)

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes('-fullscreen', self.is_fullscreen)

    def exit_fullscreen(self, event=None):
        self.is_fullscreen = False
        self.attributes('-fullscreen', False)

    def load_repairs(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.dynamic_font_widgets = []

        repairs = db.get_repairs_by_customer(self.customer_id)
        # 依 repair_date 欄位轉為 datetime，再以降冪排序
        repairs = sorted(
            repairs,
            key=lambda r: datetime.strptime(r['repair_date'], "%Y-%m-%d"),
            reverse=True
        )
        if not repairs:
            no_record_label = ctk.CTkLabel(self.scrollable_frame, text="尚無維修紀錄")
            no_record_label.pack(pady=20)
            self.dynamic_font_widgets.append(no_record_label)
        else:
            for repair in repairs:
                item_frame = ctk.CTkFrame(self.scrollable_frame, border_width=1)
                item_frame.pack(fill="x", pady=5, padx=5)
                try:
                    items_data = json.loads(repair['items'])
                    items_text = "\n".join([f"  - {item['item']}: ${item['amount']:,}" for item in items_data])
                except (json.JSONDecodeError, TypeError):
                    items_text = f"  - {repair['items']}"
                mileage_text = f"{repair['mileage']:,} km" if repair['mileage'] is not None else "未記錄"
                details = (
                    f"日期: {repair['repair_date']} | 總金額: ${repair['amount']:,} | "
                    f"維修里程數: {mileage_text}\n維修項目清單:\n{items_text}")
                details_label = ctk.CTkLabel(item_frame, text=details, justify="left")
                details_label.pack(side="left", fill="x", expand=True, padx=5, pady=5)
                edit_btn = ctk.CTkButton(item_frame, text="編輯", width=50,
                                         command=lambda r=repair: self.open_repair_dialog(r))
                edit_btn.pack(side="right", padx=(0, 5))
                delete_btn = ctk.CTkButton(item_frame, text="刪除", width=50, fg_color="red", hover_color="darkred",
                                           command=lambda r_id=repair['id']: self.delete_repair(r_id))
                delete_btn.pack(side="right", padx=5)
                self.dynamic_font_widgets.append((details_label, edit_btn, delete_btn))

        self.update_all_widget_fonts()

    def open_repair_dialog(self, repair=None):
        dialog = RepairDialog(self, repair_data=repair, customer_id=self.customer_id,
                              base_font_size=self.base_font_size)
        self.wait_window(dialog)
        self.load_repairs()

    def delete_repair(self, repair_id):
        prompt_text = "即將刪除此筆維修紀錄！此操作無法復原。\n\n請輸入 'D' 確認:"
        dialog = CustomInputDialog(self, title="確認刪除", text=prompt_text,
                                   font=("Microsoft JhengHei UI", int(self.base_font_size * 0.8)))
        result = dialog.get_input()
        if result and result.strip().lower() == 'd':
            db.delete_repair(repair_id)
            SuccessDialog(self, message="刪除成功！")
            self.load_repairs()

    def edit_customer_info(self):
        dialog = EditCustomerDialog(self, customer_data=self.customer_data, base_font_size=self.base_font_size)
        self.wait_window(dialog)
        self.customer_data = db.get_customer_by_id(self.customer_id)
        self.title(f"{self.customer_data['name']} 的資料頁面")
        self.name_label.configure(text=f"姓名: {self.customer_data['name']}")
        self.model_label.configure(text=f"車型: {self.customer_data['car_model']}")
        self.contact_label.configure(text=f"聯絡資訊: {self.customer_data['contact_info']}")
        self.app.refresh_customer_list()

    def delete_customer(self):
        dialog = CustomInputDialog(self, title="確認刪除客戶",
                                   text=f"即將刪除客戶 '{self.customer_data['name']}' ...\n請輸入客戶姓名確認:",
                                   font=("Microsoft JhengHei UI", int(self.base_font_size * 0.8)))
        result = dialog.get_input()
        if result == self.customer_data['name']:
            db.delete_customer(self.customer_id)
            self.app.refresh_customer_list()
            self.destroy()

    def increase_font_size(self):
        self.base_font_size += 2
        self.update_font_definitions()
        self.update_all_widget_fonts()

    def decrease_font_size(self):
        if self.base_font_size > 12:
            self.base_font_size -= 2
            self.update_font_definitions()
            self.update_all_widget_fonts()

    def update_font_definitions(self):
        self.font_normal = ("Microsoft JhengHei UI", self.base_font_size)
        self.font_bold = ("Microsoft JhengHei UI", self.base_font_size, "bold")

    def update_all_widget_fonts(self):
        all_widgets = self.static_font_widgets + self.dynamic_font_widgets
        for widget in all_widgets:
            if isinstance(widget, tuple):
                details_label, edit_btn, delete_btn = widget
                details_label.configure(font=self.font_normal)
                edit_btn.configure(font=self.font_normal)
                delete_btn.configure(font=self.font_normal)
            elif isinstance(widget, ctk.CTkLabel):
                if widget in [self.info_label_header, self.repair_label_header, self.font_size_label]:
                    widget.configure(font=self.font_bold)
                else:
                    widget.configure(font=self.font_normal)
            elif isinstance(widget, ctk.CTkButton):
                widget.configure(font=self.font_normal)

class AddCustomerDialog(ctk.CTkToplevel):
    def __init__(self, parent, base_font_size):
        super().__init__(parent)
        self.new_customer_id = None
        font_normal = ("Microsoft JhengHei UI", base_font_size)
        self.title("新增客戶")
        self.geometry("600x450")
        self.transient(parent)
        self.grab_set()
        ctk.CTkLabel(self, text="客戶名稱:", font=font_normal).pack(padx=20, pady=(10, 0), anchor="w")
        self.name_entry = ctk.CTkEntry(self, height=40, font=font_normal)
        self.name_entry.pack(padx=20, fill="x")
        ctk.CTkLabel(self, text="汽車廠牌型號:", font=font_normal).pack(padx=20, pady=(10, 0), anchor="w")
        self.model_entry = ctk.CTkEntry(self, height=40, font=font_normal)
        self.model_entry.pack(padx=20, fill="x")
        ctk.CTkLabel(self, text="客戶聯絡資訊:", font=font_normal).pack(padx=20, pady=(10, 0), anchor="w")
        self.contact_entry = ctk.CTkEntry(self, height=40, font=font_normal)
        self.contact_entry.pack(padx=20, fill="x")
        ctk.CTkButton(self, text="儲存新客戶", command=self.save, font=font_normal, height=40).pack(pady=20)

    def save(self):
        # 取得使用者輸入的客戶資料
        name = self.name_entry.get().strip()
        model = self.model_entry.get().strip()
        contact = self.contact_entry.get().strip()

        # 驗證必填欄位
        if not all([name, model, contact]):
            # 顯示錯誤訊息
            error_label = ctk.CTkLabel(self, text="所有欄位都必須填寫",
                                       text_color="red",
                                       font=self.font_normal)
            error_label.pack(pady=5)
            return

        # 新增客戶資料
        self.new_customer_id = db.add_customer(name, model, contact)
        # 顯示成功訊息
        SuccessDialog(self, message="新客戶儲存成功！")
        self.destroy()


class EditCustomerDialog(ctk.CTkToplevel):
    def __init__(self, parent, customer_data, base_font_size):
        super().__init__(parent)
        self.customer_data = customer_data
        font_normal = ("Microsoft JhengHei UI", base_font_size)
        self.title("編輯客戶資料")
        self.geometry("600x450")
        self.transient(parent)
        self.grab_set()
        ctk.CTkLabel(self, text="客戶名稱:", font=font_normal).pack(padx=20, pady=(10, 0), anchor="w")
        self.name_entry = ctk.CTkEntry(self, height=40, font=font_normal)
        self.name_entry.pack(padx=20, fill="x")
        ctk.CTkLabel(self, text="汽車廠牌型號:", font=font_normal).pack(padx=20, pady=(10, 0), anchor="w")
        self.model_entry = ctk.CTkEntry(self, height=40, font=font_normal)
        self.model_entry.pack(padx=20, fill="x")
        ctk.CTkLabel(self, text="客戶聯絡資訊:", font=font_normal).pack(padx=20, pady=(10, 0), anchor="w")
        self.contact_entry = ctk.CTkEntry(self, height=40, font=font_normal)
        self.contact_entry.pack(padx=20, fill="x")
        self.name_entry.insert(0, self.customer_data['name'])
        self.model_entry.insert(0, self.customer_data['car_model'])
        self.contact_entry.insert(0, self.customer_data['contact_info'])
        ctk.CTkButton(self, text="儲存變更", command=self.save, font=font_normal, height=40).pack(pady=20)

    def save(self):
        # 取得使用者輸入的客戶資料
        name = self.name_entry.get().strip()
        model = self.model_entry.get().strip()
        contact = self.contact_entry.get().strip()

        # 驗證必填欄位
        if not all([name, model, contact]):
            ctk.CTkLabel(self, text="所有欄位都必須填寫",
                         text_color="red",
                         font=("Microsoft JhengHei UI", 16)).pack(pady=5)
            return

        # 更新客戶資料
        db.update_customer(self.customer_data['id'], name, model, contact)
        # 顯示成功訊息
        dialog = SuccessDialog(self, message="客戶資料修改成功！")
        self.wait_window(dialog)  # 等待使用者確認
        self.destroy()

class RepairDialog(ctk.CTkToplevel):
    def __init__(self, parent, customer_id, repair_data=None, base_font_size=26):
        super().__init__(parent)
        self.parent, self.customer_id, self.repair_data = parent, customer_id, repair_data
        self.font_normal = ("Microsoft JhengHei UI", base_font_size)
        self.font_small = ("Microsoft JhengHei UI", base_font_size - 6)
        self.font_bold = ("Microsoft JhengHei UI", base_font_size, "bold")
        self.title("新增/編輯維修紀錄")
        self.geometry("900x800")
        self.transient(parent)
        self.grab_set()
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=10)
        top_frame.grid_columnconfigure(1, weight=1)
        self.warning_label = ctk.CTkLabel(top_frame, text="只能輸入數字！", text_color="red", font=self.font_small)
        self.vcmd = (self.register(self.validate_numeric), '%P')
        ctk.CTkLabel(top_frame, text="維修日期:", font=self.font_normal).grid(row=0, column=0, padx=5, pady=5,
                                                                              sticky="w")
        self.date_entry = ctk.CTkEntry(top_frame, font=self.font_normal)
        self.date_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=5)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        ctk.CTkLabel(top_frame, text="維修里程數(km):", font=self.font_normal).grid(row=1, column=0, padx=5, pady=5,
                                                                                    sticky="w")
        self.mileage_entry = ctk.CTkEntry(top_frame, font=self.font_normal, validate="key", validatecommand=self.vcmd,
                                          placeholder_text="尚未輸入里程數")
        self.mileage_entry.grid(row=1, column=1, sticky="ew", padx=5)
        self.unknown_mileage_btn = ctk.CTkButton(top_frame, text="里程數未知", font=self.font_small,
                                                 command=self._fill_last_mileage)
        self.unknown_mileage_btn.grid(row=1, column=2, padx=5)
        items_main_frame = ctk.CTkFrame(self)
        items_main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.items_scroll_frame = ctk.CTkScrollableFrame(items_main_frame, label_text="維修項目與金額",
                                                         label_font=self.font_normal)
        self.items_scroll_frame.pack(fill="both", expand=True)
        self.item_rows, self.common_items = [], db.get_all_repair_items()
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.pack(fill="x", padx=10, pady=10)
        bottom_frame.grid_columnconfigure(1, weight=1)
        (ctk.CTkButton(bottom_frame, text="新增一個項目", command=self.add_item_row, font=self.font_normal).
         grid(row=0,column=0,padx=5,pady=5))
        self.total_amount_label = ctk.CTkLabel(bottom_frame, text="總金額: $0", font=self.font_bold)
        self.total_amount_label.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        self.is_edit = bool(repair_data)
        btn_text = "儲存編輯檔案" if self.is_edit else "儲存維修紀錄"
        save_button = ctk.CTkButton(self, text=btn_text, command=self.save, font=self.font_bold, height=50)
        save_button.pack(side="bottom", fill="x", padx=10, pady=10)
        save_button.pack(side="bottom", fill="x", padx=10, pady=10)

        if self.repair_data:
              self.load_existing_data()
        else:
            self.add_item_row()

    def add_item_row(self, item_data=None):
        row_frame = ctk.CTkFrame(self.items_scroll_frame)
        row_frame.pack(fill="x", pady=4, padx=4)
        row_frame.grid_columnconfigure(0, weight=1)
        item_combobox = ctk.CTkComboBox(row_frame, values=self.common_items, font=self.font_normal,
                                        dropdown_font=self.font_normal, height=40)
        item_combobox.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        amount_entry = ctk.CTkEntry(row_frame, placeholder_text="金額", font=self.font_normal, height=40,
                                    validate="key", validatecommand=self.vcmd)
        amount_entry.grid(row=0, column=1, padx=5, pady=5)
        amount_entry.bind("<KeyRelease>", lambda event: self.update_total_amount())
        calc_button = ctk.CTkButton(row_frame, text="計算機", height=40, font=self.font_small,
                                    command=lambda entry=amount_entry: self.open_calculator(entry))
        calc_button.grid(row=0, column=2, padx=5, pady=5)
        delete_button = ctk.CTkButton(row_frame, text="✕", width=40, height=40, fg_color="red", hover_color="darkred",
                                      command=lambda frame=row_frame: self.delete_item_row(frame))
        delete_button.grid(row=0, column=3, padx=5, pady=5)
        row_widgets = {"frame": row_frame, "item": item_combobox, "amount": amount_entry}
        self.item_rows.append(row_widgets)
        if item_data:
            item_combobox.set(item_data.get('item', ''))
            amount_entry.insert(0, str(item_data.get('amount', '')))
        self.update_total_amount()

    def delete_item_row(self, frame_to_delete):
        for row in self.item_rows:
            if row["frame"] == frame_to_delete:
                self.item_rows.remove(row)
                break
        frame_to_delete.destroy()
        self.update_total_amount()

    def update_total_amount(self):
        total = 0
        for row in self.item_rows:
            try:
                total += float(row["amount"].get())
            except ValueError:
                continue
        self.total_amount_label.configure(text=f"總金額: ${total:,.2f}")

    def open_calculator(self, target_entry):
        CalculatorDialog(self, target_entry)

    def validate_numeric(self, P):
        if P == "" or P.isdigit() or (P.count('.') <= 1 and all(c.isdigit() for c in P.replace('.', '', 1))):
            return True
        else:
            self.show_warning()
            return False

    def show_warning(self):
        self.warning_label.grid(row=2, column=0, columnspan=3, sticky="w", padx=5)
        self.after(3000, lambda: self.warning_label.grid_forget())

    def load_existing_data(self):
        self.date_entry.delete(0, "end")
        self.date_entry.insert(0, self.repair_data['repair_date'])
        if self.repair_data['mileage'] is not None:
            self.mileage_entry.insert(0, self.repair_data['mileage'])
        if self.repair_data['items']:
            try:
                items_list = json.loads(self.repair_data['items'])
                for item in items_list:
                    self.add_item_row(item)
            except (json.JSONDecodeError, TypeError):
                self.add_item_row({"item": self.repair_data['items'], "amount": self.repair_data['amount']})
        else:
            self.add_item_row()

    def save(self):
        # 【1】讀取並初始化所有輸入資料
        date_str = self.date_entry.get()
        mileage_str = self.mileage_entry.get()
        items_to_save, total_amount = [], 0
        mileage_to_save = int(mileage_str) if mileage_str else None
        # 【2】組裝維修項目與金額
        for row in self.item_rows:
            item_name, item_amount_str = row["item"].get().strip(), row["amount"].get()
            if item_name and item_amount_str:
                item_amount = float(item_amount_str)
                items_to_save.append({"item": item_name, "amount": item_amount})
                db.add_repair_item_if_not_exists(item_name)
                total_amount += item_amount
        items_json = json.dumps(items_to_save, ensure_ascii=False)
        # 【3】日期格式與合理性驗證
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            if not (1900 <= dt.year <= datetime.now().year):
                raise ValueError
        except ValueError:
            ctk.CTkLabel(self, text="日期格式或範圍錯誤，請重新輸入",
                         text_color="red", font=self.font_small).pack(pady=5)
            return
        # 【4】檢查重複日期（僅在新增模式）
        exists = db.has_repair_on_date(self.customer_id, date_str)
        if not self.is_edit and exists:
            dialog = ctk.CTkToplevel(self)
            dialog.title("重複紀錄提醒")
            dialog.geometry("400x150")
            dialog.transient(self)
            dialog.grab_set()
            ctk.CTkLabel(dialog,
                     text="當日已有儲存紀錄，是否再新增一筆？",
                     font=self.font_normal, wraplength=380).pack(pady=20)
            btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            btn_frame.pack()
            # 按下「是」：新增後關閉
            ctk.CTkButton(btn_frame, text="是",
                      command=lambda: [
                          db.add_repair(self.customer_id, date_str, items_json, total_amount, mileage_to_save),
                          dialog.destroy(), self.destroy()]).pack(side="left", padx=10)
        # 按下「否」：僅關閉提示
            ctk.CTkButton(btn_frame, text="否",
                      command=dialog.destroy).pack(side="left", padx=10)
            return
        # 【5】執行資料庫操作
        if self.is_edit:
             db.update_repair(
                self.repair_data['id'],
                date_str, items_json, total_amount, mileage_to_save)
        else:
            db.add_repair(
                self.customer_id,
                date_str, items_json, total_amount, mileage_to_save)
        # 【6】顯示成功視窗
        self.show_save_success_dialog()
        date_str = self.date_entry.get()

    # 無重複或編輯同日，正常執行新增或更新
    def show_save_success_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("操作成功")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure((0, 1), weight=1)
        dialog.grid_rowconfigure(0, weight=1)
        ctk.CTkLabel(dialog, text="儲存成功！\n是否要關閉維修紀錄視窗？", font=self.font_normal).grid(row=0, column=0,
                                                                                                    columnspan=2,
                                                                                                    padx=20, pady=20)
        ctk.CTkButton(dialog, text="繼續編輯", command=dialog.destroy, font=self.font_normal).grid(row=1, column=0,
                                                                                                   padx=10, pady=10,
                                                                                                   sticky="ew")
        ctk.CTkButton(dialog, text="儲存並退出", command=self.destroy, font=self.font_normal).grid(row=1, column=1,
                                                                                                   padx=10, pady=10,
                                                                                                   sticky="ew")

    def _fill_last_mileage(self):
        last_mileage = db.get_latest_mileage(self.customer_id)
        if last_mileage is not None:
            self.mileage_entry.delete(0, 'end')
            self.mileage_entry.insert(0, str(last_mileage))
        else:
            info_dialog = ctk.CTkToplevel(self)
            info_dialog.title("提示")
            info_dialog.geometry("300x100")
            ctk.CTkLabel(info_dialog, text="找不到此客戶過往的里程紀錄。", font=self.font_small).pack(expand=True)
            info_dialog.grab_set()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        #  隱藏主視窗以避免閃爍
        self.withdraw()

        #  顯示啟動畫面與初始進度
        self.splash = SplashScreen(self)
        self.splash.update_progress(20)

        # 在背景執行初始化任務
        def init_task():
            # 3.1 資料庫初始化
            db.init_db()
            self.splash.update_progress(50)

            # 3.2 建立 UI
            self.title("汽車客戶資料管理系統")
            ctk.set_appearance_mode("System")
            #初始字體大小
            self.base_font_size = 26
            self.font_adjustable_widgets = []
            # 顯示公告欄初始數量
            self.old_customers_display_count = 5
            self.recent_customers_display_count = 5
            self.update_font_definitions()
            self.setup_ui()
            self.splash.update_progress(90)

            # 3.3 稍作停頓，完整顯示進度條
            time.sleep(0.3)
            self.splash.update_progress(100)
            time.sleep(0.2)

            # 3.4 關閉 Splash 並顯示主視窗
            self.splash.destroy()
            self.deiconify()
            self.state('zoomed')

        threading.Thread(target=init_task, daemon=True).start()


    def setup_ui(self):
        """設置使用者介面"""
        main_container = ctk.CTkFrame(self)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        main_container.grid_rowconfigure(2, weight=1)
        main_container.grid_columnconfigure(0, weight=1)

        self.setup_top_section(main_container)
        self.setup_settings_section(main_container)
        self.setup_bulletin_section(main_container)

        self.refresh_customer_list()
        self.update_all_widget_fonts()

    def setup_top_section(self, parent):
        """設置頂部區域"""
        top_frame = ctk.CTkFrame(parent)
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_frame.grid_columnconfigure(0, weight=1)

        self.time_label = ctk.CTkLabel(top_frame, text="")
        self.time_label.pack(pady=40)
        self.font_adjustable_widgets.append(self.time_label)
        self.update_time()

        search_label = ctk.CTkLabel(top_frame, text="搜尋或選擇客戶以新增維修紀錄")
        search_label.pack()
        self.font_adjustable_widgets.append(search_label)

        self.customer_combobox = ctk.CTkComboBox(top_frame, width=600, height=60, command=self.on_customer_select)
        self.customer_combobox.pack(pady=20)
        self.font_adjustable_widgets.append(self.customer_combobox)

        or_label = ctk.CTkLabel(top_frame, text="或")
        or_label.pack()
        self.font_adjustable_widgets.append(or_label)

        # 新增「新增/編輯維修項目」視窗和「匯入excel資料檔案」按鈕框架
        button_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        button_frame.pack(pady=20)

        # 新增三個按鈕
        self.import_excel_btn = ctk.CTkButton(
            button_frame,
            text="匯入 Excel",
            height=60,
            command=self.import_excel  # 暫無功能
        )

        self.import_excel_btn.pack(side="left", padx=10)


        self.export_excel_btn = ctk.CTkButton(
            button_frame,
            text="匯出 Excel",
            height=60,
            command=self.export_excel
        )
        self.export_excel_btn.pack(side="left", padx=10)

        self.add_customer_btn = ctk.CTkButton(
            button_frame,
            text="新增客戶資料",
            height=60,
            command=self.open_add_customer_dialog
        )
        self.add_customer_btn.pack(side="left", padx=10)

        self.edit_items_btn = ctk.CTkButton(
            button_frame,
            text="新增/編輯維修項目",
            height=60,
            command=self.open_repair_items_window
        )
        self.edit_items_btn.pack(side="left", padx=10)

        # 將按鈕加入字體調整列表
        self.font_adjustable_widgets.extend([
            self.import_excel_btn,
            self.export_excel_btn,
            self.add_customer_btn,
            self.edit_items_btn
        ])
    #新增開啟維修項目視窗的方法
    def open_repair_items_window(self):
        """開啟維修項目編輯視窗"""
        RepairItemsWindow(self, base_font_size=self.base_font_size, app=self)

    def setup_settings_section(self, parent):
        """設置設定區域"""
        settings_frame = ctk.CTkFrame(parent, height=100)
        settings_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        settings_frame.grid_columnconfigure((0, 1), weight=1)

        theme_frame = ctk.CTkFrame(settings_frame)
        theme_frame.grid(row=0, column=0, pady=10, padx=20, sticky="e")
        theme_label = ctk.CTkLabel(theme_frame, text="顏色主題: ")
        theme_label.pack(side="left", padx=(0, 5))
        self.font_adjustable_widgets.append(theme_label)
        theme_segmented_button = ctk.CTkSegmentedButton(theme_frame, values=["白色", "黑色", "系統"],
                                                        command=self.change_appearance_mode)
        theme_segmented_button.set("系統")
        theme_segmented_button.pack(side="left")
        self.font_adjustable_widgets.append(theme_segmented_button)

        font_frame = ctk.CTkFrame(settings_frame)
        font_frame.grid(row=0, column=1, pady=10, padx=20, sticky="w")
        self.font_size_label = ctk.CTkLabel(font_frame, text="調整整體字體大小:")
        self.font_size_label.pack(side="left", padx=5)
        self.font_adjustable_widgets.append(self.font_size_label)
        decrease_font_button = ctk.CTkButton(font_frame, text="-", width=40, height=40,
                                             command=self.decrease_font_size)
        decrease_font_button.pack(side="left")
        increase_font_button = ctk.CTkButton(font_frame, text="+", width=40, height=40,
                                             command=self.increase_font_size)
        increase_font_button.pack(side="left", padx=(5, 0))
        self.font_adjustable_widgets.append(decrease_font_button)
        self.font_adjustable_widgets.append(increase_font_button)

        #退出全螢幕按鈕
        self.exit_full_btn = ctk.CTkButton(
            self,
            text="全螢幕切換",
            command=self.toggle_fullscreen,
            width=120,
            height=50,
            font=("Microsoft JhengHei UI", 28, "bold"),
            fg_color="#FF5555"
        )
        self.exit_full_btn.place(relx=1.0, rely=0.0, anchor='ne', x=-10, y=10)

    def toggle_fullscreen(self):
        if self.attributes('-fullscreen'):
            self.attributes('-fullscreen', False)
        else:
            self.attributes('-fullscreen', True)

    def setup_bulletin_section(self, parent):
        """設置公告欄區域"""
        # 建立容器
        bulletin_container = ctk.CTkFrame(parent)
        bulletin_container.grid(row=2, column=0, sticky="nsew", pady=(20, 0))

        # 新增「刷新頁面」按鈕
        refresh_btn = ctk.CTkButton(
            bulletin_container,
            text="刷新頁面",
            fg_color="transparent",
            hover_color="#cccccc",
            command=self.refresh_bulletin_boards
        )
        refresh_btn.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="e")
        self.font_adjustable_widgets.append(refresh_btn)

        # 既有公告欄設定
        bulletin_container.grid_columnconfigure((0, 1), weight=1)
        self.setup_old_customers_board(bulletin_container)
        self.setup_recent_customers_board(bulletin_container)

        bulletin_container = ctk.CTkFrame(parent)
        bulletin_container.grid(row=2, column=0, sticky="nsew", pady=(20, 0))
        bulletin_container.grid_columnconfigure((0, 1), weight=1)
        bulletin_container.grid_rowconfigure(0, weight=1)

        self.setup_old_customers_board(bulletin_container)
        self.setup_recent_customers_board(bulletin_container)

    def setup_old_customers_board(self, parent):
        """設置久未來訪客戶公告欄"""
        old_customers_frame = ctk.CTkFrame(parent)
        old_customers_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        old_customers_frame.grid_rowconfigure(1, weight=1)
        old_customers_frame.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(old_customers_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(header_frame, text="距離今天超過半年沒來訪客戶", font=self.font_bold)
        title_label.grid(row=0, column=0, sticky="w")
        self.font_adjustable_widgets.append(title_label)

        count_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        count_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))

        count_label = ctk.CTkLabel(count_frame, text="展示數量:")
        count_label.pack(side="left", padx=(0, 5))
        self.font_adjustable_widgets.append(count_label)

        count_buttons_frame = ctk.CTkFrame(count_frame, fg_color="transparent")
        count_buttons_frame.pack(side="left")

        for count in [5, 30, 50, 100]:
            btn = ctk.CTkButton(count_buttons_frame, text=str(count), width=40,
                                command=lambda c=count: self.set_old_customers_count(c))
            btn.pack(side="left", padx=2)
            self.font_adjustable_widgets.append(btn)

        manual_btn = ctk.CTkButton(count_buttons_frame, text="手動", width=50,
                                   command=self.set_old_customers_manual_count)
        manual_btn.pack(side="left", padx=2)
        self.font_adjustable_widgets.append(manual_btn)

        self.old_customers_scroll = ctk.CTkScrollableFrame(old_customers_frame)
        self.old_customers_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.old_customers_scroll.grid_columnconfigure(0, weight=1)

    def setup_recent_customers_board(self, parent):
        """設置近期來訪客戶公告欄"""
        recent_customers_frame = ctk.CTkFrame(parent)
        recent_customers_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        recent_customers_frame.grid_rowconfigure(1, weight=1)
        recent_customers_frame.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(recent_customers_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(header_frame, text="近期來訪的客戶", font=self.font_bold)
        title_label.grid(row=0, column=0, sticky="w")
        self.font_adjustable_widgets.append(title_label)

        count_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        count_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))

        count_label = ctk.CTkLabel(count_frame, text="展示數量:")
        count_label.pack(side="left", padx=(0, 5))
        self.font_adjustable_widgets.append(count_label)

        count_buttons_frame = ctk.CTkFrame(count_frame, fg_color="transparent")
        count_buttons_frame.pack(side="left")

        for count in [5, 30, 50, 100]:
            btn = ctk.CTkButton(count_buttons_frame, text=str(count), width=40,
                                command=lambda c=count: self.set_recent_customers_count(c))
            btn.pack(side="left", padx=2)
            self.font_adjustable_widgets.append(btn)

        manual_btn = ctk.CTkButton(count_buttons_frame, text="手動", width=50,
                                   command=self.set_recent_customers_manual_count)
        manual_btn.pack(side="left", padx=2)
        self.font_adjustable_widgets.append(manual_btn)

        self.recent_customers_scroll = ctk.CTkScrollableFrame(recent_customers_frame)
        self.recent_customers_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.recent_customers_scroll.grid_columnconfigure(0, weight=1)

    def truncate_text_smart(self, text, max_length=50):
        """智能文字截斷函數，支援省略號顯示"""
        if len(text) <= max_length:
            return text
        return textwrap.shorten(text, width=max_length, placeholder="...")

    def calculate_font_size_for_text(self, text, base_size, max_length=100):
        """根據文字長度動態計算字體大小"""
        if len(text) <= max_length:
            return base_size
        elif len(text) <= max_length * 1.5:
            return max(base_size - 2, 12)
        elif len(text) <= max_length * 2:
            return max(base_size - 4, 10)
        else:
            return max(base_size - 6, 8)

    def create_customer_item(self, parent, customer, is_old=True):
        """創建客戶項目顯示（包含維修詳細資料）"""
        item_frame = ctk.CTkFrame(parent, border_width=1)
        item_frame.pack(fill="x", pady=3, padx=5)
        item_frame.grid_columnconfigure(0, weight=1)

        # 客戶基本信息
        name_label = ctk.CTkLabel(item_frame,
                                  text=f"{customer['name']} - {customer['car_model']} - {customer['contact_info']}",
                                  font=self.font_normal)
        name_label.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
        self.font_adjustable_widgets.append(name_label)

        # 時間信息
        if customer['last_visit_date']:
            days_since = int(customer['days_since_visit']) if customer['days_since_visit'] else 0
            if is_old:
                time_text = f"已 {days_since} 天未來訪"
                if days_since > 365:
                    time_text += f" (約 {days_since // 365} 年)"
                time_color = "#AE0000"
            else:
                time_text = f"{days_since} 天前來訪"
                time_color = "#FF8040"

            time_label = ctk.CTkLabel(item_frame, text=time_text,
                                      font=("Microsoft JhengHei UI", self.base_font_size - 4),
                                      text_color=time_color)
        else:
            time_label = ctk.CTkLabel(item_frame, text="從未來訪",
                                      font=("Microsoft JhengHei UI", self.base_font_size - 4),
                                      text_color="red")

        time_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 2))
        self.font_adjustable_widgets.append(time_label)

        # 新增：維修紀錄詳細資料
        if customer['last_visit_date']:
            repair_data = db.get_latest_repair_by_customer(customer['id'])
            if repair_data:
                # 解析維修項目
                try:
                    items_data = json.loads(repair_data['items'])
                    items_text = ", ".join([item['item'] for item in items_data])
                except (json.JSONDecodeError, TypeError):
                    items_text = str(repair_data['items'])

                # 處理過長的維修項目文字
                if len(items_text) > 60:
                    items_display = self.truncate_text_smart(items_text, 60)
                    items_font_size = self.calculate_font_size_for_text(items_text, self.base_font_size - 6)
                else:
                    items_display = items_text
                    items_font_size = self.base_font_size - 6

                # 維修項目標籤
                items_label = ctk.CTkLabel(item_frame,
                                           text=f"維修項目: {items_display}",
                                           font=("Microsoft JhengHei UI", items_font_size),
                                           text_color="gray")
                items_label.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 2))
                self.font_adjustable_widgets.append(items_label)

                # 總金額和里程數資訊
                amount_text = f"總金額: ${repair_data['amount']:,.0f}"
                mileage_text = f"里程: {repair_data['mileage']:,} km" if repair_data['mileage'] else "里程: 未記錄"

                detail_info = f"{amount_text} | {mileage_text}"
                detail_label = ctk.CTkLabel(item_frame,
                                            text=detail_info,
                                            font=("Microsoft JhengHei UI", self.base_font_size - 6),
                                            text_color="#8CEA00")
                detail_label.grid(row=3, column=0, sticky="w", padx=10, pady=(0, 8))
                self.font_adjustable_widgets.append(detail_label)

        # 點擊事件綁定
        def bind_click_event(widget):
            widget.bind("<Button-1>", lambda e: self.open_customer_window(customer['id']))

        bind_click_event(item_frame)
        bind_click_event(name_label)
        bind_click_event(time_label)

    def set_old_customers_count(self, count):
        """設置久未來訪客戶展示數量"""
        self.old_customers_display_count = count
        self.refresh_old_customers_board()

    def set_recent_customers_count(self, count):
        """設置近期來訪客戶展示數量"""
        self.recent_customers_display_count = count
        self.refresh_recent_customers_board()

    def set_old_customers_manual_count(self):
        """手動設置久未來訪客戶展示數量"""
        dialog = CustomInputDialog(self, title="設置展示數量",
                                   text="請輸入要展示的客戶數量:",
                                   font=self.font_normal)
        result = dialog.get_input()
        if result and result.isdigit():
            count = int(result)
            if count > 0:
                self.old_customers_display_count = count
                self.refresh_old_customers_board()

    def set_recent_customers_manual_count(self):
        """手動設置近期來訪客戶展示數量"""
        dialog = CustomInputDialog(self, title="設置展示數量",
                                   text="請輸入要展示的客戶數量:",
                                   font=self.font_normal)
        result = dialog.get_input()
        if result and result.isdigit():
            count = int(result)
            if count > 0:
                self.recent_customers_display_count = count
                self.refresh_recent_customers_board()

    def refresh_bulletin_boards(self):
        """刷新所有公告欄"""
        self.refresh_old_customers_board()
        self.refresh_recent_customers_board()

    def refresh_old_customers_board(self):
        """刷新久未來訪客戶公告欄"""
        for widget in self.old_customers_scroll.winfo_children():
            widget.destroy()

        customers = db.get_customers_not_visited_since(days=181)
        display_customers = customers[:self.old_customers_display_count]

        if not display_customers:
            no_data_label = ctk.CTkLabel(self.old_customers_scroll,
                                         text="目前沒有超過半年未來訪的客戶",
                                         font=self.font_normal)
            no_data_label.pack(pady=20)
            self.font_adjustable_widgets.append(no_data_label)
        else:
            for customer in display_customers:
                self.create_customer_item(self.old_customers_scroll, customer, is_old=True)

    def refresh_recent_customers_board(self):
        """刷新近期來訪客戶公告欄"""
        for widget in self.recent_customers_scroll.winfo_children():
            widget.destroy()

        customers = db.get_customers_visited_within(181)
        display_customers = customers[:self.recent_customers_display_count]

        if not display_customers:
            no_data_label = ctk.CTkLabel(self.recent_customers_scroll,
                                         text="目前沒有來訪記錄",
                                         font=self.font_normal)
            no_data_label.pack(pady=20)
            self.font_adjustable_widgets.append(no_data_label)
        else:
            for customer in display_customers:
                self.create_customer_item(self.recent_customers_scroll, customer, is_old=False)

    def update_time(self):
        now = datetime.now()
        self.time_label.configure(text=f"{now.strftime('%Y年%m月%d日')}\n{now.strftime('%H:%M:%S')}")
        self.after(1000, self.update_time)

    def refresh_customer_list(self):
        self.customers_data = db.get_all_customers()
        customer_names = [f"{c['name']} - {c['car_model']}" for c in self.customers_data]
        unique_customer_names = list(dict.fromkeys(customer_names))
        if not unique_customer_names:
            unique_customer_names = ["尚無客戶資料"]
        self.customer_combobox.configure(values=unique_customer_names)
        self.customer_combobox.set("請選擇客戶...")
        self.refresh_bulletin_boards()

    def on_customer_select(self, selected_name):
        if selected_name == "尚無客戶資料":
            return
        for customer in self.customers_data:
            if f"{customer['name']} - {customer['car_model']}" == selected_name:
                self.open_customer_window(customer['id'])
                break

    def open_customer_window(self, customer_id):
        """開啟客戶資料視窗"""
        customer_window = CustomerWindow(
            self,
            customer_id,
            base_font_size=self.base_font_size,
            app=self
        )
        # 延遲刷新客戶列表
        self.after(100, self.refresh_customer_list)

    def open_add_customer_dialog(self):
        dialog = AddCustomerDialog(self, base_font_size=self.base_font_size)
        self.wait_window(dialog)
        self.refresh_customer_list()
        if dialog.new_customer_id:
            self.open_customer_window(dialog.new_customer_id)

    def change_appearance_mode(self, new_mode):
        """處理主題切換"""
        mode_mapping = {
            "白色": "light",
            "黑色": "dark",
            "系統": "system"
        }

        # 設定外觀模式
        ctk.set_appearance_mode(mode_mapping[new_mode])


    def increase_font_size(self):
        self.base_font_size += 2
        self.update_font_definitions()
        self.update_all_widget_fonts()

    def decrease_font_size(self):
        if self.base_font_size > 12:
            self.base_font_size -= 2
            self.update_font_definitions()
            self.update_all_widget_fonts()

    def update_font_definitions(self):
        self.font_normal = ("Microsoft JhengHei UI", self.base_font_size)
        self.font_bold = ("Microsoft JhengHei UI", self.base_font_size + 4, "bold")

    def update_all_widget_fonts(self):
        self.font_size_label.configure(text="調整整體字體大小: ")
        for widget in self.font_adjustable_widgets:
            if widget == self.time_label:
                widget.configure(font=("Arial", int(self.base_font_size * 1.5), "bold"))
            elif widget == self.customer_combobox:
                widget.configure(font=self.font_normal,
                                 dropdown_font=("Microsoft JhengHei UI", int(self.base_font_size * 1.2)))
            else:
                widget.configure(font=self.font_normal)

    def import_excel(self):
        from tkinter import filedialog
        import pandas as pd
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[("Excel 檔案", "*.xlsx;*.xls")])
            if not file_path:
                return
            df = pd.read_excel(file_path)
            for _, row in df.iterrows():
                db.add_customer(row['name'], row['car_model'], row['contact_info'])
            self.refresh_customer_list()
        except Exception as e:
            ctk.CTkMessageBox(title="匯入失敗", message=f"請確認檔案格式正確\n錯誤：{e}")


    def export_excel(self):
        from tkinter import filedialog
        import pandas as pd

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel 檔案", "*.xlsx;*.xls")])
        if not file_path:
            return
        customers = db.get_all_customers()
        df = pd.DataFrame(customers)
        df.to_excel(file_path, index=False)


#新增維修項目編輯視窗類別
class RepairItemsWindow(ctk.CTkToplevel):
    def __init__(self, parent, base_font_size, app):
        super().__init__(parent)
        # 首先初始化所有基本屬性
        self.static_font_widgets = []
        self.item_entries = []
        self.item_frames = []
        self.parent = parent
        self.app = app
        self.base_font_size = base_font_size
        self.is_fullscreen = True

        # 更新字體定義
        self.update_font_definitions()

        # 設定視窗基本屬性
        self.title("維修項目管理")
        self.attributes('-fullscreen', True)
        self.transient(parent)
        self.grab_set()
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 建立UI元件
        self.create_ui_elements()

        # 載入維修項目
        self.load_items()

        # 綁定鍵盤事件
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)



    def create_ui_elements(self):
        """建立所有UI元件"""
        # 標題框架
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        title_label = ctk.CTkLabel(header_frame, text="維修項目編輯", font=self.font_bold)
        title_label.pack(pady=10)

        # 項目列表框架
        self.items_frame = ctk.CTkScrollableFrame(self)
        self.items_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.items_frame.grid_columnconfigure(0, weight=1)

        # 設定區域框架
        self.settings_frame = ctk.CTkFrame(self, height=60)
        self.settings_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.settings_frame.grid_columnconfigure(0, weight=1)

        # 字體調整框架（左側）
        font_frame = ctk.CTkFrame(self.settings_frame)
        font_frame.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        self.font_size_label = ctk.CTkLabel(font_frame, text="調整整體字體大小: ")
        self.font_size_label.pack(side="left", padx=5)
        self.static_font_widgets.append(self.font_size_label)

        decrease_font_button = ctk.CTkButton(font_frame, text="-", width=40, height=40,
                                             command=self.decrease_font_size)
        decrease_font_button.pack(side="left")
        self.static_font_widgets.append(decrease_font_button)

        increase_font_button = ctk.CTkButton(font_frame, text="+", width=40, height=40,
                                             command=self.increase_font_size)
        increase_font_button.pack(side="left", padx=(5, 0))
        self.static_font_widgets.append(increase_font_button)

        # 按鈕框架（右側）
        self.button_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.button_frame.grid(row=0, column=1, sticky="e", padx=10)

        # 建立按鈕框架
        self.add_item_btn = ctk.CTkButton(
            self.button_frame,
            text="新增項目",
            command=self.add_new_item,
            width=120, height=50,
            font=self.font_bold,
            fg_color="#4CAF50", hover_color="#45A049"
        )
        self.add_item_btn.pack(side="left", padx=5)

        # 儲存按鈕
        self.save_btn = ctk.CTkButton(
            self.button_frame,
            text="儲存修改",
            command=self.save_items,
            width=120,
            height=50,
            font=self.font_bold,
            fg_color="#55AA55",
            hover_color="#448844"
        )
        self.save_btn.pack(side="left", padx=5)
        self.static_font_widgets.append(self.save_btn)

        # 退出全螢幕按鈕
        self.exit_full_btn = ctk.CTkButton(
            self.button_frame,
            text="退出全螢幕",
            command=self.exit_fullscreen,
            width=120,
            height=50,
            font=self.font_bold,
            fg_color="#FF5555",
            hover_color="#FF0000"
        )
        self.exit_full_btn.pack(side="left", padx=5)
        self.static_font_widgets.append(self.exit_full_btn)

        # 開啟全螢幕按鈕
        self.enter_full_btn = ctk.CTkButton(
            self.button_frame,
            text="開啟全螢幕",
            command=self.enter_fullscreen,
            width=120,
            height=50,
            font=self.font_bold,
            fg_color="#5555FF",
            hover_color="#0000FF"
        )
        self.enter_full_btn.pack(side="left", padx=5)
        self.static_font_widgets.append(self.enter_full_btn)

    def add_new_item(self):
        """動態新增一行空白輸入框"""
        self.add_item_row("")  # 建立空字串輸入框
        self.items_frame.update_idletasks()  # 更新布局
        self.items_frame._parent_canvas.yview_moveto(1.0)  # 滾動到底部
        self.update_all_widget_fonts()

    def update_font_definitions(self):
        """更新字體定義"""
        self.font_normal = ("Microsoft JhengHei UI", self.base_font_size)
        self.font_bold = ("Microsoft JhengHei UI", self.base_font_size, "bold")

    def load_items(self):
        """載入所有維修項目"""
        self.item_entries = []
        self.item_frames = []

        # 清除現有項目
        for widget in self.items_frame.winfo_children():
            widget.destroy()

        # 從資料庫獲取項目
        items = db.get_all_repair_items()
        for item in items:
            self.add_item_row(item)

    def add_item_row(self, item_text):
        """新增項目行"""
        frame = ctk.CTkFrame(self.items_frame)
        frame.pack(fill="x", pady=5, padx=5)

        # 文字輸入框
        entry = ctk.CTkEntry(
            frame,
            font=self.font_normal,
            placeholder_text="輸入維修項目"
        )
        entry.insert(0, item_text)
        entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        self.item_entries.append(entry)

        # 刪除按鈕
        delete_btn = ctk.CTkButton(
            frame,
            text="刪除品項",
            width=100,
            height=30,
            fg_color="#FF5555",
            hover_color="#AA0000",
            command=lambda f=frame: self.confirm_delete(f)
        )
        delete_btn.pack(side="right", padx=5)

        self.item_frames.append(frame)

    def confirm_delete(self, frame):
        """確認刪除對話框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("確認刪除")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("300x150")

        ctk.CTkLabel(dialog, text="確定刪除此品項嗎？", font=self.font_bold).pack(pady=20)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        yes_btn = ctk.CTkButton(btn_frame, text="是", width=80,
                                command=lambda: self.execute_delete(frame, dialog))
        yes_btn.pack(side="left", padx=10)

        no_btn = ctk.CTkButton(btn_frame, text="否", width=80,
                               command=dialog.destroy)
        no_btn.pack(side="right", padx=10)

    def execute_delete(self, frame, dialog):
        """執行刪除操作"""
        # 從列表中移除對應的entry
        for i, item_frame in enumerate(self.item_frames):
            if item_frame == frame:
                if i < len(self.item_entries):
                    self.item_entries.pop(i)
                break

        frame.destroy()
        self.item_frames.remove(frame)
        dialog.destroy()

    def save_items(self):
        """儲存所有修改"""
        new_items = []
        for entry in self.item_entries:
            if entry.winfo_exists():
                text = entry.get().strip()
                if text:
                    new_items.append(text)
        # 更新資料庫
        db.update_repair_items(new_items)
        # 顯示成功提示
        SuccessDialog(self,
                      title="儲存成功",
                      message="維修項目已成功更新！\n下拉式選單將在下次使用時刷新")
        dialog.wait_window()      # 等待使用者按「確認」
        self.destroy()

    def increase_font_size(self):
        """增大字體"""
        self.base_font_size += 2
        self.update_font_definitions()
        self.update_all_widget_fonts()

    def decrease_font_size(self):
        """減小字體"""
        if self.base_font_size > 12:
            self.base_font_size -= 2
            self.update_font_definitions()
            self.update_all_widget_fonts()

    def update_all_widget_fonts(self):
        # 更新底部控制按鈕及標籤
        for w in self.static_font_widgets:
            w.configure(font=self.font_normal)
        # 更新維修項目列表的文字輸入框
        for entry in self.item_entries:
            entry.configure(font=self.font_normal)
        # 更新列表中刪除按鈕字體
        for frame in self.item_frames:
            for child in frame.winfo_children():
                if isinstance(child, ctk.CTkButton):
                    child.configure(font=self.font_normal)

    def enter_fullscreen(self, event=None):
        """進入全螢幕"""
        self.is_fullscreen = True
        self.attributes('-fullscreen', True)

    def exit_fullscreen(self, event=None):
        """退出全螢幕"""
        self.is_fullscreen = False
        self.attributes('-fullscreen', False)

    def toggle_fullscreen(self, event=None):
        """切換全螢幕狀態"""
        self.is_fullscreen = not self.is_fullscreen
        self.attributes('-fullscreen', self.is_fullscreen)


if __name__ == "__main__":
    # 設定外觀模式（亮色/暗色）
    ctk.set_appearance_mode("System")
    # 設定預設顏色主題（使用內建主題）
    ctk.set_default_color_theme("blue")  # 使用藍色主題

    db.init_db()
    app = App()
    app.mainloop()

