# SIPL Language Toolkit

Набір інструментів для мови програмування **SIPL**

## Обраний набір завдань

CORE-01 — Граматика SIPL (grammar/sipl.lark), лексика та тести (0.5)
CORE-02 — Парсер, AST з позиціями (SourceSpan) і помилки (1.5)
CORE-03 — Інтерпретатор, ліміт кроків і покриття тестами від 80% (2.0)
CORE-05 — CLI (check, parse, run, sem, viz) і JSON-вивід (1.0)
VIS-01 — Візуалізація Parse Tree у Text, JSON, DOT та SVG (1.5)
VIS-02 — Візуалізація AST і порівняння Parse Tree з AST у HTML/SVG (1.0)
SEM-01 — Побудова семантичного терму та трасування правил (2.0)
REL-01 — GitHub Actions CI (ruff, mypy, pytest) (0.5)
Разом: 10.0

## Архітектура проєкту

```text
sipl-toolkit/
├── grammar/sipl.lark          # Граматика мови SIPL
├── src/sipl/
│   ├── ast.py                 # Вузли AST та SourceSpan
│   ├── parser.py              # Парсер і синтаксичні помилки
│   ├── interpreter.py         # Інтерпретатор програм
│   ├── semantics.py           # Побудова семантичних термів
│   ├── visualization.py       # Експорт дерев у Text, JSON, DOT, SVG та HTML
│   └── cli.py                 # Консольний інтерфейс (sipl)
├── examples/                  # Приклади програм (power.sipl, gcd.sipl, fact.sipl)
├── tests/                     # Тести
└── .github/workflows/ci.yml   # Перевірки CI
```
