# gpt-prompt-engineer
[![Twitter Follow](https://img.shields.io/twitter/follow/mattshumer_?style=social)](https://twitter.com/mattshumer_) [![Open Main Version In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mshumer/gpt-prompt-engineer/blob/main/gpt_prompt_engineer.ipynb) [![Open Classification Version In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/16NLMjqyuUWxcokE_NF6RwHD8grwEeoaJ?usp=sharing)

[Узнавайте первыми о новых AI-сборках и демо!](https://tally.so/r/w2M17p)

## Обзор

Инженерия промптов похожа на алхимию: заранее не угадаешь, что сработает лучше. Нужно экспериментировать, пока не найдёшь подходящий промпт. `gpt-prompt-engineer` выносит эти эксперименты на новый уровень.

**Достаточно задать описание задачи и тестовые случаи — система сгенерирует множество промптов, проверит их и отсортирует по рейтингу, чтобы выделить самые эффективные.**

## *Обновление 20.03.24: версия для Claude 3 Opus*
Добавлена версия gpt-prompt-engineer под Anthropic Claude 3 Opus. В ней тестовые случаи генерируются автоматически, а пользователь может задать несколько входных переменных — это делает инструмент мощнее и гибче. Запускайте ноутбук `claude-prompt-engineer.ipynb` из репозитория.

## *Обновление 20.03.24: конвертация Claude 3 Opus → Haiku*
Ноутбук позволяет собирать быстрые и эффективные AI-системы при заметно меньших затратах. Opus задаёт «пространство» качества, а Haiku используется для генерации: Opus создаёт набор эталонных примеров, по которым Haiku выдаёт результат сопоставимого качества при существенно меньшей задержке и стоимости. Запускайте `opus-to-haiku-conversion.ipynb`.

## Возможности

- **Генерация промптов**: с помощью GPT-4, GPT-3.5-Turbo или Claude 3 Opus генерируются варианты промптов по заданному сценарию и тестовым случаям.

- **Проверка промптов**: каждый вариант проверяется на всех тестовых случаях, результаты сравниваются и ранжируются по системе ELO.
<img width="1563" alt="Screen Shot 2023-07-04 at 11 41 54 AM" src="https://github.com/mshumer/gpt-prompt-engineer/assets/41550495/f8171cff-1703-40ca-b9fd-f0aa24d07110">

- **Рейтинг ELO**: у каждого промпта стартовый рейтинг 1200. В «турнире» по ответам на тестовые случаи рейтинги обновляются в зависимости от качества. Так видно, какие промпты работают лучше всего.

- **Версия для классификации**: ноутбук `gpt-prompt-engineer -- Classification Version` заточен под задачи классификации. Корректность проверяется по соответствию ожидаемому ответу ('true' или 'false'), в итоге выводится таблица с оценками по каждому промпту.
<img width="1607" alt="Screen Shot 2023-07-10 at 5 22 24 PM" src="https://github.com/mshumer/gpt-prompt-engineer/assets/41550495/d5c9f2a8-97fa-445d-9c38-dec744f77854">

- **Версия Claude 3**: ноутбук claude-prompt-engineer работает с Claude 3 Opus, сам генерирует тестовые случаи и поддерживает несколько входных переменных.

- **Конвертация Opus → Haiku**: сохраняет качество Opus для вашего сценария при скорости и стоимости Haiku.

- **Логирование в [Weights & Biases](https://wandb.ai/site/prompts)**: по желанию можно логировать конфиг (temperature, max tokens), системные и пользовательские промпты, тестовые случаи и итоговый ELO по каждому кандидату. Включите: `use_wandb = True`.

- **[Portkey](https://portkey.ai)**: опциональное логирование и трассировка цепочек промптов и ответов. Включите: `use_portkey = True`.

## Установка и настройка

1. Откройте ноутбук в [Google Colab](https://colab.research.google.com/github/mshumer/gpt-prompt-engineer/blob/main/gpt_prompt_engineer.ipynb) или в локальном Jupyter. Для классификации — [этот](https://colab.research.google.com/drive/16NLMjqyuUWxcokE_NF6RwHD8grwEeoaJ?usp=sharing). Для Claude 3 — [этот](https://colab.research.google.com/drive/1likU_S4VfkzoLMPfVdMs3E54cn_W6I7o?usp=sharing).

2. Укажите OpenAI API ключ: создайте файл `_secrets.py` из `_secrets.example.py` и пропишите в нём `OPENAI_API_KEY`. В версии для Claude 3 укажите ключ Anthropic в переменной `ANTHROPIC_API_KEY`.

## Как пользоваться

1. Для версии на GPT-4 задайте сценарий использования и тестовые случаи. Сценарий — это описание того, что должна делать модель. Тестовые случаи — конкретные запросы, на которые она будет отвечать. Пример:

```
description = "По запросу сгенерировать заголовок для лендинга." # такое описание обычно даёт хороший результат

test_cases = [
    {'prompt': 'Продвижение нового фитнес-приложения Smartly'},
    {'prompt': 'Почему веганская диета полезна для здоровья'},
    {'prompt': 'Запуск онлайн-курса по цифровому маркетингу'},
    {'prompt': 'Запуск линейки экологичной одежды'},
    {'prompt': 'Продвижение блога о бюджетных путешествиях'},
    {'prompt': 'Реклама ПО для управления проектами'},
    {'prompt': 'Презентация книги по изучению Python'},
    {'prompt': 'Продвижение платформы для изучения языков'},
    {'prompt': 'Реклама сервиса персональных планов питания'},
    {'prompt': 'Запуск приложения для ментального здоровья и медитации'},
]
```

Для версии классификации тестовые случаи задаются в формате:

```
test_cases = [
    {'prompt': 'У меня был отличный день!', 'output': 'true'},
    {'prompt': 'Мне грустно.', 'output': 'false'},
    # добавьте свои тестовые случаи
]
```

Для версии Claude 3 можно задать входные переменные помимо описания сценария:

```
description = "По запросу сгенерировать персональный ответ на email."

input_variables = [
    {"variable": "SENDER_NAME", "description": "Имя отправителя письма."},
    {"variable": "RECIPIENT_NAME", "description": "Имя получателя."},
    {"variable": "TOPIC", "description": "Тема или суть письма. Одно-два предложения."}
]
```

Тестовые случаи будут сгенерированы автоматически по описанию и переменным.

3. Выберите, сколько вариантов промптов генерировать. Учтите, что при большом числе запросов затраты растут. Разумный старт — 10.

4. Вызовите `generate_optimal_prompt(description, test_cases, number_of_prompts)` — будет сгенерирован список промптов и оценена их эффективность. В версии классификации достаточно выполнить последнюю ячейку. В версии Claude 3: `generate_optimal_prompt(description, input_variables, num_test_cases, number_of_prompts, use_wandb)`.

5. Итоговые рейтинги ELO выводятся в таблице по убыванию: чем выше рейтинг, тем лучше промпт.
<img width="1074" alt="Screen Shot 2023-07-04 at 11 48 45 AM" src="https://github.com/mshumer/gpt-prompt-engineer/assets/41550495/324f90b8-c0ee-45fd-b219-6c44d9aa281b">

В версии классификации для каждого промпта выводятся оценки в таблице (как на изображении выше).

## Приветствуются контрибуции. Идеи:
- несколько генераторов системных промптов в разных стилях (с примерами, краткие, развёрнутые, markdown и т.д.);
- автоматическая генерация тестовых случаев;
- расширение версии классификации на более чем два класса (например, с tiktoken).

## Лицензия

Проект распространяется под лицензией [MIT](https://github.com/your_username/your_repository/blob/master/LICENSE).

## Контакты

Matt Shumer — [@mattshumer_](https://twitter.com/mattshumer_)

Ссылка на проект: [https://github.com/mshumer/gpt-prompt-engineer](url)

Если интересны ещё более продвинутые инструменты — загляните в [HyperWrite Personal Assistant](https://app.hyperwriteai.com/personalassistant): ИИ с доступом к актуальной информации, который умеет писать естественно и управлять браузером для выполнения задач.

А также [ShumerPrompt](https://ShumerPrompt.com) — «Github для промптов».
