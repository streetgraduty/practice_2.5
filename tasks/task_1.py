import sqlite3
from pathlib import Path
from typing import List, Optional

RESOURSE_DIR = Path(__file__).resolve().parent.parent / "resourse"
DB_PATH = RESOURSE_DIR / "task_1.db"


class Student:
    def __init__(
        self,
        id: Optional[int],
        first_name: str,
        last_name: str,
        patronymic: str,
        group_name: str,
        grades: List[float],
    ):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.patronymic = patronymic
        self.group_name = group_name
        self.grades = grades


def average_grade(grades: List[float]) -> float:
    if not grades:
        return 0.0
    return sum(grades) / len(grades)


def student_as_text(s: Student) -> str:
    g = ", ".join(str(x) for x in s.grades)
    return f"{s.last_name} {s.first_name} {s.patronymic} | группа {s.group_name} | оценки: [{g}]"


def get_connection() -> sqlite3.Connection:
    RESOURSE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                patronymic TEXT NOT NULL,
                group_name TEXT NOT NULL,
                grade1 REAL NOT NULL,
                grade2 REAL NOT NULL,
                grade3 REAL NOT NULL,
                grade4 REAL NOT NULL
            )
            """
        )


def row_to_student(row: sqlite3.Row) -> Student:
    return Student(
        id=row["id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        patronymic=row["patronymic"],
        group_name=row["group_name"],
        grades=[row["grade1"], row["grade2"], row["grade3"], row["grade4"]],
    )


def add_student(s: Student) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO students (first_name, last_name, patronymic, group_name, grade1, grade2, grade3, grade4)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                s.first_name,
                s.last_name,
                s.patronymic,
                s.group_name,
                s.grades[0],
                s.grades[1],
                s.grades[2],
                s.grades[3],
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_students() -> List[Student]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM students ORDER BY last_name, first_name").fetchall()
    return [row_to_student(r) for r in rows]


def get_student(student_id: int) -> Optional[Student]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    return row_to_student(row) if row else None


def update_student(s: Student) -> None:
    if s.id is None:
        raise ValueError("id обязателен для обновления")
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE students SET
                first_name = ?, last_name = ?, patronymic = ?, group_name = ?,
                grade1 = ?, grade2 = ?, grade3 = ?, grade4 = ?
            WHERE id = ?
            """,
            (
                s.first_name,
                s.last_name,
                s.patronymic,
                s.group_name,
                s.grades[0],
                s.grades[1],
                s.grades[2],
                s.grades[3],
                s.id,
            ),
        )
        conn.commit()


def delete_student(student_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()


def average_for_group(group_name: str) -> Optional[float]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT AVG((grade1 + grade2 + grade3 + grade4) / 4.0) AS avg_mark
            FROM students WHERE group_name = ?
            """,
            (group_name,),
        ).fetchone()
    if not row or row["avg_mark"] is None:
        return None
    return float(row["avg_mark"])


def read_grades() -> List[float]:
    grades = []
    for i in range(4):
        while True:
            try:
                g = float(input(f"  Оценка {i + 1}: ").replace(",", "."))
                grades.append(g)
                break
            except ValueError:
                print("  Введите число.")
    return grades


def read_student_fields() -> Student:
    last_name = input("Фамилия: ").strip()
    first_name = input("Имя: ").strip()
    patronymic = input("Отчество: ").strip()
    group_name = input("Группа: ").strip()
    print("Четыре оценки:")
    grades = read_grades()
    return Student(None, first_name, last_name, patronymic, group_name, grades)


def main() -> None:
    init_db()
    while True:
        print(
            """
--- Студенты ---
1) Добавить студента
2) Показать всех студентов
3) Показать одного студента (и средний балл)
4) Редактировать студента
5) Удалить студента
6) Средний балл по группе
0) Выход
"""
        )
        choice = input("Выбор: ").strip()
        if choice == "1":
            s = read_student_fields()
            new_id = add_student(s)
            print(f"Добавлен студент с id={new_id}.")
        elif choice == "2":
            for s in list_students():
                print(f"  [{s.id}] {student_as_text(s)}")
        elif choice == "3":
            try:
                sid = int(input("ID: "))
            except ValueError:
                print("Нужен числовой id.")
                continue
            s = get_student(sid)
            if not s:
                print("Не найден.")
            else:
                print(student_as_text(s))
                print(f"Средний балл: {average_grade(s.grades):.2f}")
        elif choice == "4":
            try:
                sid = int(input("ID студента для правки: "))
            except ValueError:
                print("Нужен числовой id.")
                continue
            if not get_student(sid):
                print("Не найден.")
                continue
            last_name = input("Фамилия: ").strip()
            first_name = input("Имя: ").strip()
            patronymic = input("Отчество: ").strip()
            group_name = input("Группа: ").strip()
            print("Четыре оценки:")
            grades = read_grades()
            update_student(Student(sid, first_name, last_name, patronymic, group_name, grades))
            print("Сохранено.")
        elif choice == "5":
            try:
                sid = int(input("ID для удаления: "))
            except ValueError:
                print("Нужен числовой id.")
                continue
            delete_student(sid)
            print("Удалено (если id был в базе).")
        elif choice == "6":
            gname = input("Название группы: ").strip()
            avg = average_for_group(gname)
            if avg is None:
                print("В этой группе нет студентов.")
            else:
                print(f"Средний балл по группе «{gname}»: {avg:.2f}")
        elif choice == "0":
            break
        else:
            print("Неизвестный пункт.")


if __name__ == "__main__":
    main()
