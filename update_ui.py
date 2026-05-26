import os

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Font & Icon replacements
html = html.replace(
    '<link\n    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"\n    rel="stylesheet" />',
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />\n  <script src="https://unpkg.com/@phosphor-icons/web"></script>'
)

# Fix possible different newline formats
html = html.replace(
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />',
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />\n  <script src="https://unpkg.com/@phosphor-icons/web"></script>'
)

replacements = {
    '🏢 ТИМ Инспектор': '<i class="ph-fill ph-buildings" style="margin-right:8px;"></i> ТИМ Инспектор',
    '📂 Загрузка модели': '<i class="ph-fill ph-folder-open" style="margin-right:6px;"></i> Загрузка модели',
    '<span class="dz-icon">📁</span>': '<span class="dz-icon"><i class="ph-fill ph-upload-simple"></i></span>',
    '<span>✓</span>': '<span><i class="ph-bold ph-check"></i></span>',
    '☑ Тип проверки': '<i class="ph-fill ph-check-square" style="margin-right:6px;"></i> Тип проверки',
    '📋 Загрузка IDS файлов': '<i class="ph-fill ph-clipboard-text" style="margin-right:6px;"></i> Загрузка IDS файлов',
    '<span class="dz-icon" style="font-size:32px">📋</span>': '<span class="dz-icon" style="font-size:32px"><i class="ph-fill ph-files"></i></span>',
    '▶ Запуск анализа': '<i class="ph-fill ph-play-circle"></i> Запуск анализа',
    '⚡ Запуск анализа': '<i class="ph-fill ph-lightning" style="margin-right:6px;"></i> Запуск анализа',
    '<span class="spin" id="progress-spin">⟳</span>': '<span class="spin" id="progress-spin"><i class="ph-bold ph-spinner-gap"></i></span>',
    'Ошибок 🔴': 'Ошибок <i class="ph-fill ph-warning-circle" style="color:#F43F5E"></i>',
    'Предупреждений 🟡': 'Предупреждений <i class="ph-fill ph-warning" style="color:#F59E0B"></i>',
    'Прошло 🟢': 'Прошло <i class="ph-fill ph-check-circle" style="color:#10B981"></i>',
    '📋 Результаты проверки': '<i class="ph-fill ph-list-checks" style="margin-right:6px;"></i> Результаты проверки',
    '<span>🔍</span>': '<span><i class="ph-bold ph-magnifying-glass"></i></span>',
    '⬇ PDF': '<i class="ph-fill ph-file-pdf"></i> PDF',
    '⬇ Excel': '<i class="ph-fill ph-file-xls"></i> Excel',
    '⬇ JSON': '<i class="ph-fill ph-file-code"></i> JSON',
    '⬇ BCF': '<i class="ph-fill ph-file-zip"></i> BCF',
    'title="ИИ-Ассистент">💬</button>': 'title="ИИ-Ассистент"><i class="ph-fill ph-sparkle"></i></button>',
    '🤖 ИИ-Ассистент': '<i class="ph-fill ph-sparkle"></i> ИИ-Ассистент',
    '🤖 Анализ': '<i class="ph-fill ph-sparkle"></i> Анализ',
    'Отправить →': 'Отправить <i class="ph-bold ph-paper-plane-right"></i>',
    
    # JS strings
    "📄 ${f.name}": "<i class=\\'ph-fill ph-file-text\\'></i> ${f.name}",
    "spin.textContent = '✓';": "spin.innerHTML = '<i class=\"ph-bold ph-check\"></i>';",
    "↺ Повторить анализ": "<i class=\\'ph-bold ph-arrow-counter-clockwise\\'></i> Повторить анализ",
    "⟳ Анализирую...": "<i class=\\'ph-bold ph-spinner-gap spin\\'></i> Анализирую...",
    "🤖 Свернуть": "<i class=\\'ph-fill ph-caret-up\\'></i> Свернуть",
    "🔴 Почему возникла ошибка:": "<i class=\\'ph-fill ph-warning-circle\\' style=\\'color:#F43F5E\\'></i> Почему возникла ошибка:",
    "✅ Подтверждение соответствия:": "<i class=\\'ph-fill ph-check-circle\\' style=\\'color:#10B981\\'></i> Подтверждение соответствия:",
    "🔧 Как исправить:": "<i class=\\'ph-fill ph-wrench\\' style=\\'color:#3B82F6\\'></i> Как исправить:",
    "💡 Рекомендации по улучшению:": "<i class=\\'ph-fill ph-lightbulb\\' style=\\'color:#F59E0B\\'></i> Рекомендации по улучшению:",
    "🧠 Размышление... <span>▼</span>": "<i class=\\'ph-fill ph-brain\\'></i> Размышление... <span><i class=\\'ph-bold ph-caret-down\\'></i></span>",
    "🧠 Рассуждение <span>▶</span>": "<i class=\\'ph-fill ph-brain\\'></i> Рассуждение <span><i class=\\'ph-bold ph-caret-right\\'></i></span>",
    '<span class="spin" style="font-size:12px;margin-left:4px">⟳</span>': '<span class="spin" style="font-size:12px;margin-left:4px"><i class="ph-bold ph-spinner-gap"></i></span>'
}

for k, v in replacements.items():
    html = html.replace(k, v)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("HTML updated successfully.")
