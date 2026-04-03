import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

import requests

URL = "https://www.cbr-xml-daily.ru/daily_json.js"
RESOURSE_DIR = Path(__file__).resolve().parent.parent / "resourse"
DB_PATH = RESOURSE_DIR / "currency.db"

data = None
groups: dict[str, list[str]] = {}


def get_db():
    RESOURSE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS groups (
            name TEXT PRIMARY KEY
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS group_currency (
            group_name TEXT NOT NULL,
            currency_code TEXT NOT NULL,
            PRIMARY KEY (group_name, currency_code)
        )
        """
    )
    conn.commit()
    return conn


def load_groups():
    global groups
    groups = {}
    with get_db() as conn:
        for (name,) in conn.execute("SELECT name FROM groups ORDER BY name"):
            groups[name] = []
        for row in conn.execute("SELECT group_name, currency_code FROM group_currency"):
            g, code = row[0], row[1]
            if g not in groups:
                groups[g] = []
            groups[g].append(code)


def save_group_create(name: str):
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO groups (name) VALUES (?)", (name,))
        conn.commit()


def save_currency_add(group: str, code: str):
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO group_currency (group_name, currency_code) VALUES (?, ?)",
            (group, code),
        )
        conn.commit()


def save_currency_remove(group: str, code: str):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM group_currency WHERE group_name = ? AND currency_code = ?",
            (group, code),
        )
        conn.commit()


def fetch_currency_data():
    global data
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        return True
    except requests.RequestException as e:
        print(f"Ошибка при получении данных: {e}")
        return False


class CurrencyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Курсы валют (Tkinter)")
        self.root.geometry("980x620")

        self.code_var = tk.StringVar()
        self.group_name_var = tk.StringVar()
        self.currency_code_var = tk.StringVar()
        self.selected_group_var = tk.StringVar()

        self._build_ui()
        load_groups()
        self._refresh_groups()

    def _build_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(top, text="Обновить данные", command=self.fetch_data).pack(side=tk.LEFT, padx=5)
        tk.Button(top, text="Показать все валюты", command=self.show_all).pack(side=tk.LEFT, padx=5)
        tk.Label(top, text="Код:").pack(side=tk.LEFT, padx=(16, 5))
        tk.Entry(top, textvariable=self.code_var, width=10).pack(side=tk.LEFT)
        tk.Button(top, text="Найти валюту", command=self.show_by_code).pack(side=tk.LEFT, padx=5)

        groups_row = tk.Frame(self.root)
        groups_row.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Label(groups_row, text="Новая группа:").pack(side=tk.LEFT)
        tk.Entry(groups_row, textvariable=self.group_name_var, width=18).pack(side=tk.LEFT, padx=5)
        tk.Button(groups_row, text="Создать", command=self.create_group).pack(side=tk.LEFT, padx=5)
        tk.Button(groups_row, text="Показать группы", command=self.show_groups).pack(side=tk.LEFT, padx=5)

        tk.Label(groups_row, text="Группа:").pack(side=tk.LEFT, padx=(20, 5))
        self.group_combo = ttk.Combobox(groups_row, textvariable=self.selected_group_var, state="readonly", width=20)
        self.group_combo.pack(side=tk.LEFT, padx=5)
        tk.Label(groups_row, text="Код валюты:").pack(side=tk.LEFT, padx=(10, 5))
        tk.Entry(groups_row, textvariable=self.currency_code_var, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(groups_row, text="Добавить", command=self.add_currency).pack(side=tk.LEFT, padx=5)
        tk.Button(groups_row, text="Удалить", command=self.remove_currency).pack(side=tk.LEFT, padx=5)
        tk.Button(groups_row, text="Курсы группы", command=self.show_group_rates).pack(side=tk.LEFT, padx=5)

        self.output = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, font=("Consolas", 10))
        self.output.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def _write(self, text):
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)

    def _refresh_groups(self):
        names = list(groups.keys())
        self.group_combo["values"] = names
        if names and self.selected_group_var.get() not in names:
            self.selected_group_var.set(names[0])

    def fetch_data(self):
        global data
        if fetch_currency_data():
            self._write("Данные успешно обновлены.")
            self._write(f"Дата: {data.get('Date', '-')}")
        else:
            self._write("Не удалось обновить данные.")

    def show_all(self):
        if not data:
            self._write("Нет данных. Нажмите 'Обновить данные'.")
            return
        self._write("=" * 80)
        self._write(f"Курсы валют на {data.get('Date', 'Неизвестно')}")
        self._write(f"{'Код':<8} {'Валюта':<35} {'Курс (RUB)':<15} {'Номинал'}")
        for code, info in data.get("Valute", {}).items():
            self._write(f"{code:<8} {info['Name']:<35} {info['Value']:<15.4f} {info['Nominal']}")

    def show_by_code(self):
        if not data:
            self._write("Нет данных. Нажмите 'Обновить данные'.")
            return
        code = self.code_var.get().strip().upper()
        if not code:
            messagebox.showwarning("Ошибка", "Введите код валюты.")
            return
        info = data.get("Valute", {}).get(code)
        if not info:
            self._write(f"Валюта {code} не найдена.")
            return
        self._write(f"{code}: {info['Name']} | Курс: {info['Value']:.4f} RUB | Номинал: {info['Nominal']}")

    def create_group(self):
        name = self.group_name_var.get().strip()
        if not name:
            messagebox.showwarning("Ошибка", "Введите название группы.")
            return
        if name in groups:
            messagebox.showwarning("Ошибка", "Группа уже существует.")
            return
        save_group_create(name)
        groups[name] = []
        self._refresh_groups()
        self._write(f"Группа '{name}' создана.")
        self.group_name_var.set("")

    def show_groups(self):
        if not groups:
            self._write("Нет созданных групп.")
            return
        self._write("Группы:")
        for name, currencies in groups.items():
            line = ", ".join(currencies) if currencies else "(пусто)"
            self._write(f"- {name}: {line}")

    def add_currency(self):
        if not data:
            self._write("Сначала обновите данные о курсах.")
            return
        group = self.selected_group_var.get().strip()
        code = self.currency_code_var.get().strip().upper()
        if not group or group not in groups:
            messagebox.showwarning("Ошибка", "Выберите группу.")
            return
        if code not in data.get("Valute", {}):
            self._write(f"Валюта {code} не найдена.")
            return
        if code in groups[group]:
            self._write(f"Валюта {code} уже есть в группе '{group}'.")
            return
        save_currency_add(group, code)
        groups[group].append(code)
        self._write(f"Добавлено: {code} -> {group}")

    def remove_currency(self):
        group = self.selected_group_var.get().strip()
        code = self.currency_code_var.get().strip().upper()
        if not group or group not in groups:
            messagebox.showwarning("Ошибка", "Выберите группу.")
            return
        if code not in groups[group]:
            self._write(f"Валюты {code} нет в группе '{group}'.")
            return
        save_currency_remove(group, code)
        groups[group].remove(code)
        self._write(f"Удалено: {code} из {group}")

    def show_group_rates(self):
        if not data:
            self._write("Сначала обновите данные о курсах.")
            return
        group = self.selected_group_var.get().strip()
        if not group or group not in groups:
            messagebox.showwarning("Ошибка", "Выберите группу.")
            return
        currencies = groups[group]
        if not currencies:
            self._write(f"Группа '{group}' пустая.")
            return
        self._write(f"Курсы группы '{group}':")
        self._write(f"{'Код':<8} {'Валюта':<35} {'Курс (RUB)':<15}")
        valute = data.get("Valute", {})
        for code in currencies:
            if code in valute:
                info = valute[code]
                self._write(f"{code:<8} {info['Name']:<35} {info['Value']:<15.4f}")
            else:
                self._write(f"{code:<8} {'Не найдена':<35} {'-':<15}")


if __name__ == "__main__":
    app_root = tk.Tk()
    CurrencyApp(app_root)
    app_root.mainloop()
