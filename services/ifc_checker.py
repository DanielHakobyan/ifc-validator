MOCK_ISSUES = [
    {
        "guid": "2HvX4921",
        "type": "Коллизия",
        "severity": "ERROR",
        "description": "Жёсткое пересечение: стальная балка и воздуховод ОВКВ",
        "location": "Этаж 3 / Ось B-4",
    },
    {
        "guid": "3KpZ7744",
        "type": "Коллизия",
        "severity": "WARNING",
        "description": "Мягкое пересечение: зазор трубы < 50мм от стены",
        "location": "Этаж 2 / Ось C-7",
    },
    {
        "guid": "9Rt12209",
        "type": "Нормативы",
        "severity": "ERROR",
        "description": "Отсутствует обязательное свойство 'FireRating' на элементах IfcWall",
        "location": "Несколько (47 элементов)",
    },
    {
        "guid": "7Mp25531",
        "type": "Нормативы",
        "severity": "WARNING",
        "description": "Имя элемента не соответствует конвенции: 'Стена_001' → ожидается 'КС-СТ-001'",
        "location": "Этаж 1 (23 элемента)",
    },
    {
        "guid": "5Lq98823",
        "type": "IDS",
        "severity": "ERROR",
        "description": "Требование IDS 'LoadBearing' не выполнено для IfcColumn",
        "location": "Секция A / Колонны (8 элементов)",
    },
    {
        "guid": "1Nm73390",
        "type": "IDS",
        "severity": "OK",
        "description": "Проверка наличия GlobalId пройдена успешно",
        "location": "Все элементы (1 247)",
    },
    {
        "guid": "4Px81102",
        "type": "Нормативы",
        "severity": "OK",
        "description": "Пространственная структура соответствует ГОСТ Р 57906",
        "location": "Вся модель",
    },
    {
        "guid": "8Qw34567",
        "type": "Коллизия",
        "severity": "ERROR",
        "description": "Пересечение несущей колонны и канализационной трубы DN150",
        "location": "Этаж 1 / Ось A-2",
    },
    {
        "guid": "6Tr56789",
        "type": "Нормативы",
        "severity": "WARNING",
        "description": "Высота помещения ниже нормативной: 2.4м < 2.7м (СП 54.13330)",
        "location": "Комната 104 / Этаж 1",
    },
    {
        "guid": "0Su11223",
        "type": "IDS",
        "severity": "OK",
        "description": "Атрибуты материалов стен заполнены корректно",
        "location": "Этаж 1-5 (120 элементов)",
    },
]


def run_checks(selected_checks: list) -> dict:
    issues = []
    for i, issue in enumerate(MOCK_ISSUES):
        issue_copy = issue.copy()
        issue_copy["id"] = i + 1
        if "ids" not in selected_checks and issue_copy["type"] == "IDS":
            continue
        if "norms" not in selected_checks and issue_copy["type"] == "Нормативы":
            continue
        if "clashes" not in selected_checks and issue_copy["type"] == "Коллизия":
            continue
        issues.append(issue_copy)

    errors = sum(1 for i in issues if i["severity"] == "ERROR")
    warnings = sum(1 for i in issues if i["severity"] == "WARNING")

    return {
        "summary": {
            "total": 1247,
            "errors": errors,
            "warnings": warnings,
            "passed": 1247 - errors - warnings,
        },
        "issues": issues,
    }
