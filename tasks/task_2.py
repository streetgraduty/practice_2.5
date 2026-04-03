import sqlite3
from pathlib import Path

RESOURSE_DIR = Path(__file__).resolve().parent.parent / "resourse"
DB_PATH = RESOURSE_DIR / "drinks.db"


def conn() -> sqlite3.Connection:
    RESOURSE_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH))
    c.execute("PRAGMA foreign_keys = ON")
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with conn() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS alcohol (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                abv REAL NOT NULL,
                stock_ml REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS ingredient (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                stock_ml REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS cocktail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                price REAL NOT NULL,
                strength REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cocktail_alcohol (
                cocktail_id INTEGER NOT NULL,
                alcohol_id INTEGER NOT NULL,
                ml REAL NOT NULL,
                PRIMARY KEY (cocktail_id, alcohol_id),
                FOREIGN KEY (cocktail_id) REFERENCES cocktail(id) ON DELETE CASCADE,
                FOREIGN KEY (alcohol_id) REFERENCES alcohol(id)
            );
            CREATE TABLE IF NOT EXISTS cocktail_ingredient (
                cocktail_id INTEGER NOT NULL,
                ingredient_id INTEGER NOT NULL,
                ml REAL NOT NULL,
                PRIMARY KEY (cocktail_id, ingredient_id),
                FOREIGN KEY (cocktail_id) REFERENCES cocktail(id) ON DELETE CASCADE,
                FOREIGN KEY (ingredient_id) REFERENCES ingredient(id)
            );
            """
        )
        db.commit()


def calc_cocktail_strength(db: sqlite3.Connection, cocktail_id: int) -> float:
    rows_a = db.execute(
        """
        SELECT a.abv, c.ml FROM cocktail_alcohol c
        JOIN alcohol a ON a.id = c.alcohol_id WHERE c.cocktail_id = ?
        """,
        (cocktail_id,),
    ).fetchall()
    rows_i = db.execute(
        "SELECT ml FROM cocktail_ingredient WHERE cocktail_id = ?", (cocktail_id,)
    ).fetchall()
    num = sum(r["abv"] * r["ml"] for r in rows_a)
    den = sum(r["ml"] for r in rows_a) + sum(r["ml"] for r in rows_i)
    if den <= 0:
        return 0.0
    return num / den


def recalc_and_save_strength(db: sqlite3.Connection, cocktail_id: int) -> float:
    s = calc_cocktail_strength(db, cocktail_id)
    db.execute("UPDATE cocktail SET strength = ? WHERE id = ?", (s, cocktail_id))
    return s


def list_alcohol():
    with conn() as db:
        for r in db.execute("SELECT * FROM alcohol ORDER BY name"):
            print(f"  [{r['id']}] {r['name']} | крепость {r['abv']}% | на складе {r['stock_ml']:.0f} мл")


def list_ingredients():
    with conn() as db:
        for r in db.execute("SELECT * FROM ingredient ORDER BY name"):
            print(f"  [{r['id']}] {r['name']} | на складе {r['stock_ml']:.0f} мл")


def list_cocktails():
    with conn() as db:
        for r in db.execute("SELECT * FROM cocktail ORDER BY name"):
            print(
                f"  [{r['id']}] {r['name']} | крепость ~{r['strength']:.1f}% | цена {r['price']:.2f} руб."
            )


def add_alcohol():
    name = input("Название: ").strip()
    abv = float(input("Крепость % (об.): ").replace(",", "."))
    stock = float(input("Остаток, мл: ").replace(",", "."))
    with conn() as db:
        db.execute("INSERT INTO alcohol (name, abv, stock_ml) VALUES (?, ?, ?)", (name, abv, stock))
        db.commit()
    print("Сохранено.")


def add_ingredient():
    name = input("Название ингредиента: ").strip()
    stock = float(input("Остаток, мл: ").replace(",", "."))
    with conn() as db:
        db.execute("INSERT INTO ingredient (name, stock_ml) VALUES (?, ?)", (name, stock))
        db.commit()
    print("Сохранено.")


def add_cocktail():
    name = input("Название коктейля: ").strip()
    price = float(input("Цена, руб.: ").replace(",", "."))
    with conn() as db:
        db.execute("INSERT INTO cocktail (name, price, strength) VALUES (?, ?, 0)", (name, price))
        cid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        print("Добавьте состав (пустое имя алкоголя — конец части с алкоголем).")
        while True:
            aname = input("  Алкоголь (название или Enter чтобы перейти к ингредиентам): ").strip()
            if not aname:
                break
            row = db.execute("SELECT id, abv FROM alcohol WHERE name = ?", (aname,)).fetchone()
            if not row:
                print("  Нет такого напитка, сначала добавьте в справочник.")
                continue
            ml = float(input("  мл: ").replace(",", "."))
            db.execute(
                "INSERT OR REPLACE INTO cocktail_alcohol (cocktail_id, alcohol_id, ml) VALUES (?, ?, ?)",
                (cid, row["id"], ml),
            )
        print("Ингредиенты (пустое имя — конец).")
        while True:
            iname = input("  Ингредиент: ").strip()
            if not iname:
                break
            row = db.execute("SELECT id FROM ingredient WHERE name = ?", (iname,)).fetchone()
            if not row:
                print("  Нет в справочнике.")
                continue
            ml = float(input("  мл: ").replace(",", "."))
            db.execute(
                "INSERT OR REPLACE INTO cocktail_ingredient (cocktail_id, ingredient_id, ml) VALUES (?, ?, ?)",
                (cid, row["id"], ml),
            )
        s = recalc_and_save_strength(db, cid)
        db.commit()
    print(f"Коктейль добавлен. Расчётная крепость: {s:.2f}%.")


def restock():
    kind = input("Что пополняем? (1 — алкоголь, 2 — ингредиент): ").strip()
    iid = int(input("ID: "))
    add_ml = float(input("Сколько мл добавить: ").replace(",", "."))
    table = "alcohol" if kind == "1" else "ingredient"
    with conn() as db:
        db.execute(f"UPDATE {table} SET stock_ml = stock_ml + ? WHERE id = ?", (add_ml, iid))
        db.commit()
    print("Склад обновлён.")


def sell_drink():
    iid = int(input("ID алкогольного напитка: "))
    ml = float(input("Сколько мл продать: ").replace(",", "."))
    with conn() as db:
        row = db.execute("SELECT stock_ml FROM alcohol WHERE id = ?", (iid,)).fetchone()
        if not row:
            print("Нет такого ID.")
            return
        if row["stock_ml"] < ml:
            print("Недостаточно на складе.")
            return
        db.execute("UPDATE alcohol SET stock_ml = stock_ml - ? WHERE id = ?", (ml, iid))
        db.commit()
    print("Продажа оформлена.")


def sell_cocktail():
    cid = int(input("ID коктейля: "))
    with conn() as db:
        c = db.execute("SELECT * FROM cocktail WHERE id = ?", (cid,)).fetchone()
        if not c:
            print("Нет такого коктейля.")
            return
        alc = db.execute(
            "SELECT alcohol_id, ml FROM cocktail_alcohol WHERE cocktail_id = ?", (cid,)
        ).fetchall()
        ing = db.execute(
            "SELECT ingredient_id, ml FROM cocktail_ingredient WHERE cocktail_id = ?", (cid,)
        ).fetchall()
        for a in alc:
            stock = db.execute("SELECT stock_ml FROM alcohol WHERE id = ?", (a["alcohol_id"],)).fetchone()
            if not stock or stock["stock_ml"] < a["ml"]:
                print("Недостаточно алкоголя на складе.")
                return
        for a in ing:
            stock = db.execute(
                "SELECT stock_ml FROM ingredient WHERE id = ?", (a["ingredient_id"],)
            ).fetchone()
            if not stock or stock["stock_ml"] < a["ml"]:
                print("Недостаточно ингредиентов.")
                return
        for a in alc:
            db.execute(
                "UPDATE alcohol SET stock_ml = stock_ml - ? WHERE id = ?",
                (a["ml"], a["alcohol_id"]),
            )
        for a in ing:
            db.execute(
                "UPDATE ingredient SET stock_ml = stock_ml - ? WHERE id = ?",
                (a["ml"], a["ingredient_id"]),
            )
        db.commit()
    print(f"Продан коктейль «{c['name']}» за {c['price']:.2f} руб. (учёт на складе обновлён).")


def show_cocktail_detail():
    cid = int(input("ID коктейля: "))
    with conn() as db:
        c = db.execute("SELECT * FROM cocktail WHERE id = ?", (cid,)).fetchone()
        if not c:
            print("Не найден.")
            return
        print(f"{c['name']} | цена {c['price']:.2f} | крепость ~{c['strength']:.2f}%")
        print("  Алкоголь:")
        for r in db.execute(
            """
            SELECT a.name, a.abv, ca.ml FROM cocktail_alcohol ca
            JOIN alcohol a ON a.id = ca.alcohol_id WHERE ca.cocktail_id = ?
            """,
            (cid,),
        ):
            print(f"    {r['name']} ({r['abv']}%) — {r['ml']} мл")
        print("  Ингредиенты:")
        for r in db.execute(
            """
            SELECT i.name, ci.ml FROM cocktail_ingredient ci
            JOIN ingredient i ON i.id = ci.ingredient_id WHERE ci.cocktail_id = ?
            """,
            (cid,),
        ):
            print(f"    {r['name']} — {r['ml']} мл")


def main():
    init_db()
    while True:
        print(
            """
=== I love drink ===
[Учёт]
 1 — список алкоголя    2 — список ингредиентов
 3 — добавить алкоголь  4 — добавить ингредиент
[Коктейли]
 5 — список коктейлей   6 — создать коктейль (состав + авто-крепость)
 7 — подробно о коктейле
[Операции]
 8 — пополнить склад    9 — продать алкоголь   10 — продать коктейль
 0 — выход
"""
        )
        ch = input("Выбор: ").strip()
        if ch == "1":
            list_alcohol()
        elif ch == "2":
            list_ingredients()
        elif ch == "3":
            add_alcohol()
        elif ch == "4":
            add_ingredient()
        elif ch == "5":
            list_cocktails()
        elif ch == "6":
            add_cocktail()
        elif ch == "7":
            show_cocktail_detail()
        elif ch == "8":
            restock()
        elif ch == "9":
            sell_drink()
        elif ch == "10":
            sell_cocktail()
        elif ch == "0":
            break
        else:
            print("Неизвестный пункт.")


if __name__ == "__main__":
    main()
