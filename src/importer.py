import csv
import io
from pathlib import Path


REQUIRED_FIELDS = ("word", "translation", "context")


def parse_csv(file_path: str | Path, language: str = "en") -> tuple[list[dict], list[str]]:
    """
    Parse CSV/TXT file with columns: word [TAB] translation [TAB] context
    Returns (words_list, errors_list)
    """
    path = Path(file_path)
    errors = []
    words = []

    if not path.exists():
        return [], [f"Файл не найден: {path}"]

    # Detect encoding
    raw = path.read_bytes()
    encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"

    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError:
        try:
            text = raw.decode("cp1251")
        except UnicodeDecodeError:
            return [], ["Не удалось определить кодировку файла. Сохраните в UTF-8."]

    reader = csv.reader(io.StringIO(text), delimiter="\t")

    for line_num, row in enumerate(reader, start=1):
        # Skip empty lines and comment lines
        if not row or row[0].startswith("#"):
            continue

        if len(row) < 3:
            errors.append(f"Строка {line_num}: нужно 3 поля (слово, перевод, контекст) — найдено {len(row)}")
            continue

        word, translation, context = row[0], row[1], row[2]

        if not word.strip():
            errors.append(f"Строка {line_num}: пустое поле «слово»")
            continue
        if not translation.strip():
            errors.append(f"Строка {line_num}: пустой перевод для «{word}»")
            continue
        if not context.strip():
            errors.append(
                f"Строка {line_num}: отсутствует контекст для «{word}». "
                f"Пример: *She managed to negotiate a better salary.*"
            )
            continue

        words.append({
            "language": language,
            "word": word.strip(),
            "translation": translation.strip(),
            "context": context.strip(),
        })

    return words, errors


def validate_preview(file_path: str | Path, n: int = 10) -> tuple[list[dict], list[str]]:
    """Return first n parsed rows and any errors for preview in UI."""
    words, errors = parse_csv(file_path)
    return words[:n], errors
