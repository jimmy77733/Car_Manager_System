# database.py
import sqlite3
import sys, os
from pathlib import Path

# 判斷是否由 PyInstaller 打包（frozen）
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(os.path.abspath(sys.executable))
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
# external_data_folder：與 exe 同層的「data_folder」資料夾
external_data_folder = os.path.join(base_dir, 'data_folder')
Path(external_data_folder).mkdir(exist_ok=True)
#使用動態計算後的資料夾路徑
DB_FILE = Path(external_data_folder) / "car_repair.db"

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    #資料庫檔案不存在或損毀時會跳出錯誤視窗並停止執行，避免後續空值導致崩潰
    except sqlite3.Error as e:
        from tkinter import messagebox
        messagebox.showerror("資料庫連線錯誤", f"無法連線到資料庫：\n{e}")
        raise

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS customers
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           name
                           TEXT
                           NOT
                           NULL,
                           car_model
                           TEXT
                           NOT
                           NULL,
                           contact_info
                           TEXT
                           NOT
                           NULL,
                           created_at
                           TIMESTAMP
                           DEFAULT
                           CURRENT_TIMESTAMP
                       )
                       """)
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS repairs
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           customer_id
                           INTEGER
                           NOT
                           NULL,
                           repair_date
                           TEXT
                           NOT
                           NULL,
                           items
                           TEXT
                           NOT
                           NULL,
                           amount
                           REAL
                           NOT
                           NULL,
                           mileage
                           INTEGER,
                           FOREIGN
                           KEY
                       (
                           customer_id
                       ) REFERENCES customers
                       (
                           id
                       ) ON DELETE CASCADE
                           )
                       """)
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS common_repair_items
                       (
                           item_name
                           TEXT
                           PRIMARY
                           KEY
                           NOT
                           NULL
                       )
                       """)
        conn.commit()


# --- 客戶相關操作 ---
def add_customer(name, car_model, contact_info):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO customers (name, car_model, contact_info) VALUES (?, ?, ?)",
                       (name, car_model, contact_info))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        import customtkinter as ctk
        ctk.CTkMessageBox(title="新增客戶失敗", message=f"錯誤原因：{e}")
        return None



def get_all_customers():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, car_model FROM customers ORDER BY name")
        return cursor.fetchall()


def get_customer_by_id(customer_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        return cursor.fetchone()


def update_customer(customer_id, name, car_model, contact_info):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE customers SET name = ?, car_model = ?, contact_info = ? WHERE id = ?",
                       (name, car_model, contact_info, customer_id))
        conn.commit()


def delete_customer(customer_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        conn.commit()


# --- 維修紀錄相關操作 ---
def add_repair(customer_id, repair_date, items, amount, mileage):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO repairs (customer_id, repair_date, items, amount, mileage) VALUES (?, ?, ?, ?, ?)",
                       (customer_id, repair_date, items, amount, mileage))
        conn.commit()


def get_repairs_by_customer(customer_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM repairs WHERE customer_id = ? ORDER BY repair_date DESC, id DESC", (customer_id,))
        return cursor.fetchall()


def update_repair(repair_id, repair_date, items, amount, mileage):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE repairs SET repair_date = ?, items = ?, amount = ?, mileage = ? WHERE id = ?",
                       (repair_date, items, amount, mileage, repair_id))
        conn.commit()


def delete_repair(repair_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM repairs WHERE id = ?", (repair_id,))
        conn.commit()


def get_latest_mileage(customer_id):
    """獲取指定客戶最近一次的維修里程數"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT mileage
                       FROM repairs
                       WHERE customer_id = ?
                         AND mileage IS NOT NULL
                       ORDER BY repair_date DESC, id DESC LIMIT 1
                       """, (customer_id,))
        result = cursor.fetchone()
        return result['mileage'] if result else None


# --- 新增：公告欄查詢功能 ---
def get_customers_visited_within(days=181):
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=days)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.name, c.car_model, c.contact_info,
                   MAX(r.repair_date) AS last_visit_date,
                   julianday('now') - julianday(MAX(r.repair_date)) AS days_since_visit
            FROM customers c
            JOIN repairs r ON c.id = r.customer_id
            GROUP BY c.id
            HAVING last_visit_date >= ?
            ORDER BY last_visit_date DESC
        """, (cutoff.strftime('%Y-%m-%d'),))
        return cursor.fetchall()

def get_customers_not_visited_since(days=181):
    """獲取指定月數內未來訪的客戶，按未來時間長短排序"""
    from datetime import datetime, timedelta

    cutoff_date = datetime.now() - timedelta(days=days)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT c.id,
                              c.name,
                              c.car_model,
                              c.contact_info,
                              MAX(r.repair_date)                               as last_visit_date,
                              julianday('now') - julianday(MAX(r.repair_date)) as days_since_visit
                       FROM customers c
                                LEFT JOIN repairs r ON c.id = r.customer_id
                       GROUP BY c.id, c.name, c.car_model, c.contact_info
                       HAVING MAX(r.repair_date) IS NOT NULL
                           AND MAX(r.repair_date) < ?
                       ORDER BY days_since_visit DESC NULLS FIRST
                       """, (cutoff_date.strftime('%Y-%m-%d'),))
        return cursor.fetchall()


def get_recent_visited_customers():
    """獲取最近來訪的客戶，按最近時間排序"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT c.id,
                              c.name,
                              c.car_model,
                              c.contact_info,
                              MAX(r.repair_date)                               as last_visit_date,
                              julianday('now') - julianday(MAX(r.repair_date)) as days_since_visit
                       FROM customers c
                                LEFT JOIN repairs r ON c.id = r.customer_id
                       GROUP BY c.id, c.name, c.car_model, c.contact_info
                       HAVING MAX(r.repair_date) IS NOT NULL
                       ORDER BY last_visit_date DESC
                       """)
        return cursor.fetchall()


def get_latest_repair_by_customer(customer_id):
    """獲取客戶最新的維修紀錄"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT id, repair_date, items, amount, mileage
                       FROM repairs
                       WHERE customer_id = ?
                       ORDER BY repair_date DESC, id DESC LIMIT 1
                       """, (customer_id,))
        return cursor.fetchone()


# --- 常用維修項目操作 ---
def get_all_repair_items():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT item_name FROM common_repair_items ORDER BY item_name")
        return [row['item_name'] for row in cursor.fetchall()]


def add_repair_item_if_not_exists(item_name):
    cleaned_name = item_name.strip()
    if not cleaned_name:
        return
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO common_repair_items (item_name) VALUES (?)", (cleaned_name,))
        conn.commit()

def has_repair_on_date(customer_id, repair_date):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM repairs
            WHERE customer_id = ? AND repair_date = ?
        """, (customer_id, repair_date))
        return cursor.fetchone()['count'] > 0

# 新增更新維修項目方法
def update_repair_items(items_list):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # 清空現有項目
        cursor.execute("DELETE FROM common_repair_items")
        # 新增新項目
        for item in items_list:
            cursor.execute("INSERT INTO common_repair_items (item_name) VALUES (?)", (item,))
        conn.commit()

# 修改獲取維修項目方法
def get_all_repair_items():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT item_name FROM common_repair_items ORDER BY item_name")
        return [row['item_name'] for row in cursor.fetchall()]


if __name__ == '__main__':
    init_db()
    print("資料庫已成功初始化。")
