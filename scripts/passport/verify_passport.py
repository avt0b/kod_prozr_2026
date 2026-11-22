"""Проверка собранного паспорта: валидность OOXML, полнота 10 блоков, состав команды."""

from __future__ import annotations

import pathlib
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT = pathlib.Path(__file__).resolve().parents[2]
DOCX = PROJECT / "docs/passport/Паспорт_проекта_battalion_404.docx"
MD = PROJECT / "docs/passport/passport.md"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

fail: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK' if ok else 'FAIL'}] {label}{(': ' + detail) if detail else ''}")
    if not ok:
        fail.append(label)


print("=== 1. Структура файла ===")
with zipfile.ZipFile(DOCX) as z:
    names = z.namelist()
    check("в архиве есть обязательные части",
          all(n in names for n in ("[Content_Types].xml", "_rels/.rels", "word/document.xml", "word/styles.xml")))
    bad = z.testzip()
    check("zip не повреждён", bad is None)
    for n in names:
        if n.endswith(".xml") or n.endswith(".rels"):
            try:
                ET.fromstring(z.read(n))
            except ET.ParseError as e:
                check(f"XML валиден: {n}", False, str(e))
                break
    else:
        check("все XML-части разбираются", True)
    doc = ET.fromstring(z.read("word/document.xml"))

paras = doc.findall(".//w:p", NS)
tables = doc.findall(".//w:tbl", NS)
text = "".join(t.text or "" for t in doc.findall(".//w:t", NS))
print(f"  абзацев: {len(paras)}, таблиц: {len(tables)}, знаков: {len(text)}")

print("\n=== 2. Полнота 10 блоков паспорта ===")
required = [
    "1. Карточка проекта", "2. Проблема и целевая аудитория", "3. Цель и результаты",
    "4. Решение", "5. Данные и аналитика", "6. Архитектура и технологии",
    "7. Безопасность, право и этика", "8. Внедрение и эффект", "9. Команда", "10. Приложения",
]
for h in required:
    check(f"блок «{h}»", h in text)

print("\n=== 3. Обязательные поля карточки ===")
for field in ("battalion_404", "Академия ФСО России", "Пиминов Михаил Артёмович",
              "mokopoko321@gmail.com", "+7 910 356-82-52", "github.com/avt0b/kod_prozr_2026",
              "04"):
    check(f"поле «{field}»", field in text)

print("\n=== 4. Обязательные аспекты по брифингу ===")
aspects = {
    "новизна сравнением": "Посейдон",
    "метрики и способ измерения": "precision",
    "оговорка про синтетику": "оценка верхняя",
    "детерминированность": "Детерминированность",
    "обоснование стека": "Обоснование стека",
    "ключевые маркеры данных": "Маркеры проблемы",
    "путь данных": "Технологическая схема",
    "ПДн и основание": "152-ФЗ",
    "FP/FN": "FP:",
    "человек в контуре": "Что остаётся за человеком",
    "ограничения": "Ограничения прототипа",
    "меры ИБ": "Требования информационной безопасности",
    "этапы внедрения": "Масштабирование",
    "критерий перехода": "Условие перехода",
    "способ измерения эффекта": "способ измерения",
    "ожидаемое качество": "Ожидаемое качество",
    "релевантный опыт": "Релевантный опыт",
    "презентация в приложениях": "kod-prozrachnosti-review.pptx",
    "инструкция запуска": "run-instructions.md",
}
for label, needle in aspects.items():
    check(label, needle in text)

print("\n=== 5. Состав команды ===")
members = ["Паршиков Роман Евгеньевич", "Пиминов Михаил Артёмович",
           "Атаманчук Егор Игоревич", "Остриков Владислав Витальевич",
           "Шварц Кирилл Денисович"]
for m in members:
    check(f"участник {m}", m in text)
forbidden = ["Гуселетов", "Soerxq", "Влад Г."]
for f in forbidden:
    check(f"нет 6-го участника ({f})", f not in text)
check("заявлено 5 участников", "5 участников" in text)

print("\n=== 6. Объём ===")
md_chars = len(re.sub(r"\s+", " ", MD.read_text(encoding="utf-8").replace("|", " ").replace("**", "").replace("`", "")).strip())
print(f"  знаков в md (без разметки): {md_chars}")
print(f"  знаков в docx: {len(text)}")
check("текст docx соответствует md (расхождение < 5 %)", abs(len(text) - md_chars) / md_chars < 0.05)

print("\n=== ИТОГ ===")
print("провалено проверок:", len(fail))
if fail:
    print("; ".join(fail))
sys.exit(1 if fail else 0)