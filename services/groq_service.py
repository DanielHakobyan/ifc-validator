import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """Ты — эксперт по BIM/ТИМ моделированию и нормативной документации России.
Специализация: IFC, ГОСТ, СП, СНиП, ISO 19650, buildingSMART, IDS.

Когда анализируешь ошибку из модели:
1. Объясни ПОЧЕМУ возникла эта ошибка (технически и нормативно)
2. Дай пошаговую инструкцию КАК исправить
3. Укажи конкретные нормативные документы: [ГОСТ Р 57906-2017 §5.2]

Когда элемент прошёл проверку:
1. Подтверди соответствие
2. Дай рекомендации по улучшению качества модели
3. Ссылки на лучшие практики

Отвечай на русском языке. Будь точным, профессиональным, конкретным."""


def stream_chat(messages: list):
    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        stream=True,
        max_tokens=1500,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def analyze_issue(issue: dict):
    """Called when user clicks 🤖 Анализ on a table row"""
    is_error = issue.get("severity") == "ERROR"
    prompt = f"""Проанализируй следующую проблему из IFC модели:

Тип проверки: {issue.get('type', '')}
Статус: {issue.get('severity', '')}
Описание: {issue.get('description', '')}
Местоположение: {issue.get('location', '')}
GUID элемента: {issue.get('guid', '')}

{'Объясни причину ошибки и дай пошаговый план исправления.' if is_error else 'Элемент прошёл проверку. Дай рекомендации по улучшению.'}"""

    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        stream=True,
        max_tokens=800,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
