from openai import OpenAI
import os
import random
import re

# ======================
# CONFIG
# ======================

# Модели по приоритету. Первые могут не поддерживать temperature — вызов без него.
CANDIDATE_MODELS = [
    "o4-mini",       # дешёвый; temperature не поддерживается
    "gpt-4.1-mini",  # fallback (см. Limits в OpenAI)
    "gpt-4.1-nano",
]

JUDGE_MODEL = "o3-mini"

TEMPERATURE = 0.9

# ======================
# CLIENT
# ======================

try:
    from _secrets import OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

client = OpenAI(api_key=OPENAI_API_KEY)


# ======================
# SAFE MODEL CALL (fallback)
# ======================

def call_model(input_text, models):
    last_error = None

    for model in models:
        for use_temp in (True, False):  # сначала с temperature, при ошибке — без
            try:
                kwargs = {"model": model, "input": input_text}
                if use_temp:
                    kwargs["temperature"] = TEMPERATURE
                resp = client.responses.create(**kwargs)
                return resp.output_text, model
            except Exception as e:
                err_msg = str(e).lower()
                if "temperature" in err_msg and "not supported" in err_msg and use_temp:
                    continue  # повторить без temperature
                print(f"Model {model} failed → {e}")
                last_error = e
                break

    raise RuntimeError(f"No available model: {last_error}")


# ======================
# GENERATE CANDIDATE PROMPTS
# ======================

def generate_candidate_prompts(description, test_cases, n=5):

    prompt = f"""
Ты — prompt engineer.

Описание задачи:
{description}

Тестовые случаи:
{test_cases}

Сгенерируй {n} разных промптов.
Ответ только списком.
"""

    output, model_used = call_model(prompt, CANDIDATE_MODELS)

    prompts = [p.strip("- ").strip() for p in output.split("\n") if p.strip()]

    print("Generated with:", model_used)

    return prompts[:n]


# ======================
# TEST PROMPT
# ======================

def run_prompt(prompt, test_case):

    input_text = f"""
Используй этот системный промпт:

{prompt}

Задача:
{test_case}
"""

    output, _ = call_model(input_text, CANDIDATE_MODELS)

    return output


# ======================
# JUDGE (EVAL)
# ======================

def judge_answer(description, test_case, answer):

    judge_prompt = f"""
Ты строгий evaluator.

Описание задачи:
{description}

Тест:
{test_case}

Ответ модели:
{answer}

Оцени качество от 1 до 10.
Верни только число.
"""

    try:
        resp = client.responses.create(
            model=JUDGE_MODEL,
            input=judge_prompt,
            temperature=0
        )
    except Exception as e:
        if "temperature" in str(e).lower() and "not supported" in str(e).lower():
            resp = client.responses.create(model=JUDGE_MODEL, input=judge_prompt)
        else:
            raise

    score = resp.output_text.strip()

    try:
        return float(score)
    except:
        return 0


# ======================
# MAIN PIPELINE
# ======================

def generate_optimal_prompt(description, test_cases, number_of_prompts=5):

    candidates = generate_candidate_prompts(
        description,
        test_cases,
        number_of_prompts
    )

    results = []

    for prompt in candidates:

        total_score = 0

        for case in test_cases:

            answer = run_prompt(prompt, case)
            score = judge_answer(description, case, answer)

            total_score += score

        avg = total_score / len(test_cases)

        results.append({
            "prompt": prompt,
            "score": avg
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    return results


# ======================
# SAVE PROMPTS TO FILE
# ======================

GENERATED_PROMPTS_DIR = "generated_prompts"


def _task_to_filename(description):
    safe = re.sub(r"[^\w\s-]", "", description, flags=re.IGNORECASE)
    safe = re.sub(r"[-\s]+", "_", safe).strip("_")[:50] or "task"
    return f"{safe}_{hash(description) % 100000}.txt"


def save_prompts_to_file(description, test_cases, results, filepath=None):
    """Пишет задачу, тест-кейсы и все промпты с оценками в txt. Возвращает путь."""
    os.makedirs(GENERATED_PROMPTS_DIR, exist_ok=True)
    path = filepath or os.path.join(GENERATED_PROMPTS_DIR, _task_to_filename(description))
    lines = [
        "=== ЗАДАЧА ===",
        description,
        "",
        "=== ТЕСТОВЫЕ СЛУЧАИ ===",
        *test_cases,
        "",
        "=== ПРОМПТЫ (по убыванию оценки) ===",
    ]
    for i, r in enumerate(results, 1):
        lines.append(f"--- Промпт {i} (оценка: {r['score']}) ---")
        lines.append(r["prompt"])
        lines.append("")
    lines.append("=== ЛУЧШИЙ ПРОМПТ ===")
    lines.append(results[0]["prompt"])
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


# ======================
# EXAMPLE
# ======================

description = "Объяснять кодовую базу React проекта"
test_cases = [
    "Explain architecture",
    "Explain folder structure",
    "Explain state management"
]

best = generate_optimal_prompt(description, test_cases, 5)

for r in best:
    print("-----")
    print(r["score"])
    print(r["prompt"])

saved = save_prompts_to_file(description, test_cases, best)
print(f"\nПромпты сохранены: {saved}")
