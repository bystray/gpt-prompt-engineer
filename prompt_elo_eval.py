import math
import os
import random
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

from openai import OpenAI

try:
    from _secrets import OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


# =========================
# CONFIG
# =========================

CANDIDATE_MODELS = ["o4-mini", "gpt-4o-mini"]   # генерация/исполнение (fallback)
JUDGE_MODELS = ["o3-mini", "o4-mini"]           # judge (fallback)
GEN_TEMPERATURE = 0.9
EXEC_TEMPERATURE = 0.2

DEFAULT_ELO = 1200.0
K_FACTOR = 24.0                # можно 16..32
ROUNDS = 12                    # сколько раундов матчей (pairwise)
PAIRS_PER_ROUND = 8            # сколько пар в раунде
SEED = 42

# Если True — judge видит ответы кандидатов на тест-кейсы.
# Если False — judge сравнивает только сами промпты (хуже).
JUDGE_SEES_ANSWERS = True


# =========================
# CLIENT
# =========================

client = OpenAI(api_key=OPENAI_API_KEY)


# =========================
# UTILS
# =========================

def _call_with_fallback(models: List[str], *, input_text: str, temperature: float) -> Tuple[str, str]:
    last_err = None
    for model in models:
        for use_temp in (True, False):
            try:
                kwargs = {"model": model, "input": input_text}
                if use_temp:
                    kwargs["temperature"] = temperature
                resp = client.responses.create(**kwargs)
                return resp.output_text, model
            except Exception as e:
                err_msg = str(e).lower()
                if "temperature" in err_msg and "not supported" in err_msg and use_temp:
                    continue
                last_err = e
                break
    raise RuntimeError(f"No available model from {models}. Last error: {last_err}")


def expected_score(r_a: float, r_b: float) -> float:
    # Elo expected score for A
    return 1.0 / (1.0 + 10 ** ((r_b - r_a) / 400.0))


def update_elo(r_a: float, r_b: float, s_a: float, k: float = K_FACTOR) -> Tuple[float, float]:
    # s_a: 1 win, 0 loss, 0.5 draw
    e_a = expected_score(r_a, r_b)
    e_b = 1.0 - e_a
    r_a2 = r_a + k * (s_a - e_a)
    r_b2 = r_b + k * ((1.0 - s_a) - e_b)
    return r_a2, r_b2


def _normalize_prompt_list(text: str, n: int) -> List[str]:
    # Пытаемся вытащить список (по строкам/маркировкам). Без фанатизма.
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cleaned = []
    for ln in lines:
        ln = re.sub(r"^\s*[\-\*\d\.\)\]]+\s*", "", ln).strip()
        if ln:
            cleaned.append(ln)
    # Склеим если модель вернула один большой блок
    if len(cleaned) < 2 and len(text.strip()) > 0:
        cleaned = [text.strip()]
    return cleaned[:n]


def _safe_truncate(s: str, limit: int = 2000) -> str:
    return s if len(s) <= limit else (s[:limit] + "…")


GENERATED_PROMPTS_DIR = "generated_prompts"


def _task_to_filename(description: str) -> str:
    """Имя файла по описанию задачи: безопасное + короткий хеш для уникальности."""
    safe = re.sub(r"[^\w\s-]", "", description, flags=re.IGNORECASE)
    safe = re.sub(r"[-\s]+", "_", safe).strip("_")[:50] or "task"
    return f"{safe}_{hash(description) % 100000}.txt"


def save_prompts_to_file(
    description: str,
    test_cases: List[str],
    result: Dict,
    filepath: Optional[str] = None,
) -> str:
    """Пишет все промпты и лидерборд в txt. Возвращает путь к файлу."""
    os.makedirs(GENERATED_PROMPTS_DIR, exist_ok=True)
    path = filepath or os.path.join(GENERATED_PROMPTS_DIR, _task_to_filename(description))
    lines = [
        "=== ЗАДАЧА ===",
        description,
        "",
        "=== ТЕСТОВЫЕ СЛУЧАИ ===",
        *test_cases,
        "",
        "=== LEADERBOARD (ELO) ===",
    ]
    for c in result["candidates"]:
        lines.append(f"{c.id}\tELO={c.rating:.1f}")
        lines.append(c.prompt)
        lines.append("")
    lines.append("=== ЛУЧШИЙ ПРОМПТ ===")
    lines.append(result["candidates"][0].prompt)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


# =========================
# DATA STRUCTURES
# =========================

@dataclass
class Candidate:
    id: str
    prompt: str
    rating: float = DEFAULT_ELO


# =========================
# STEP 1: GENERATE CANDIDATES
# =========================

def generate_candidate_prompts(description: str, test_cases: List[str], n: int) -> List[str]:
    gen_input = f"""
Ты — prompt engineer. Сгенерируй {n} разных системных промптов для решения задачи.

Задача:
{description}

Тестовые случаи (для ориентира):
{test_cases}

Требования:
- Каждый промпт должен быть пригоден как system prompt.
- Промпты должны отличаться подходом (структура, критерии качества, формат ответа).
- Верни только список промптов (каждый с новой строки). Без пояснений.
""".strip()

    out, used = _call_with_fallback(CANDIDATE_MODELS, input_text=gen_input, temperature=GEN_TEMPERATURE)
    prompts = _normalize_prompt_list(out, n)
    if len(prompts) < n:
        # добьём недостающее одной дополнительной генерацией (без циклов бесконечно)
        need = n - len(prompts)
        out2, _ = _call_with_fallback(CANDIDATE_MODELS, input_text=gen_input, temperature=GEN_TEMPERATURE)
        prompts += _normalize_prompt_list(out2, need)
        prompts = prompts[:n]
    print(f"[gen] model={used} candidates={len(prompts)}")
    return prompts


# =========================
# STEP 2: RUN CANDIDATE ON TESTS (optional but recommended)
# =========================

def run_candidate_on_tests(system_prompt: str, test_cases: List[str]) -> List[str]:
    answers = []
    for tc in test_cases:
        exec_input = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": tc},
        ]
        # Responses API принимает input как строку или structured content.
        # Делаем простым текстом: системный промпт + задача.
        merged = f"SYSTEM:\n{system_prompt}\n\nUSER TASK:\n{tc}\n"
        out, _ = _call_with_fallback(CANDIDATE_MODELS, input_text=merged, temperature=EXEC_TEMPERATURE)
        answers.append(out.strip())
    return answers


# =========================
# STEP 3: PAIRWISE JUDGE
# =========================

def judge_pair(
    description: str,
    test_cases: List[str],
    cand_a: Candidate,
    cand_b: Candidate,
    answers_a: Optional[List[str]] = None,
    answers_b: Optional[List[str]] = None,
) -> Tuple[str, str]:
    """
    Returns (winner_id, reason_short). winner_id in {cand_a.id, cand_b.id, "DRAW"}
    """

    if JUDGE_SEES_ANSWERS and (answers_a is not None) and (answers_b is not None):
        # Показываем judge ответы на тесты, чтобы сравнение было по факту.
        paired = []
        for i, tc in enumerate(test_cases):
            paired.append(
                f"TEST #{i+1}:\n{tc}\n\n"
                f"ANSWER A:\n{_safe_truncate(answers_a[i], 1200)}\n\n"
                f"ANSWER B:\n{_safe_truncate(answers_b[i], 1200)}\n"
            )
        evidence = "\n\n".join(paired)
        judge_input = f"""
Ты — строгий evaluator. Твоя задача — выбрать, какой вариант (A или B) лучше решает задачу.

Задача:
{description}

Критерии (по важности):
1) Корректность и полнота относительно задачи и тестов
2) Отсутствие галлюцинаций / лишних предположений
3) Практичность, применимость, структурность
4) Следование формату, если он требуется

СРАВНЕНИЕ:
{evidence}

Ответь строго в формате:
WINNER: A|B|DRAW
REASON: <1 короткое предложение, без воды>
""".strip()
    else:
        # Сравнение только промптов (хуже, но иногда достаточно).
        judge_input = f"""
Ты — строгий evaluator. Выбери лучший system prompt для задачи.

Задача:
{description}

PROMPT A:
{cand_a.prompt}

PROMPT B:
{cand_b.prompt}

Критерии:
- Ясность инструкций
- Управление рисками (галлюцинации/проверки)
- Качество формата ответа
- Универсальность на тестах

Ответь строго:
WINNER: A|B|DRAW
REASON: <1 короткое предложение>
""".strip()

    out, used = _call_with_fallback(JUDGE_MODELS, input_text=judge_input, temperature=0.0)

    winner = "DRAW"
    m = re.search(r"WINNER:\s*(A|B|DRAW)", out, re.IGNORECASE)
    if m:
        winner = m.group(1).upper()

    reason = ""
    m2 = re.search(r"REASON:\s*(.+)", out, re.IGNORECASE)
    if m2:
        reason = m2.group(1).strip()
    reason = _safe_truncate(reason, 160)

    if winner == "A":
        return cand_a.id, f"[judge={used}] {reason}"
    if winner == "B":
        return cand_b.id, f"[judge={used}] {reason}"
    return "DRAW", f"[judge={used}] {reason}"


# =========================
# STEP 4: ELO TOURNAMENT
# =========================

def sample_pairs(cands: List[Candidate], pairs_per_round: int, rng: random.Random) -> List[Tuple[Candidate, Candidate]]:
    # Берём случайные пары без повторов внутри раунда (best-effort).
    ids = list(range(len(cands)))
    rng.shuffle(ids)

    pairs = []
    used = set()
    for i in range(0, len(ids) - 1, 2):
        if len(pairs) >= pairs_per_round:
            break
        a = cands[ids[i]]
        b = cands[ids[i + 1]]
        key = tuple(sorted([a.id, b.id]))
        if key in used:
            continue
        used.add(key)
        pairs.append((a, b))
    return pairs


def run_elo_eval(
    description: str,
    test_cases: List[str],
    prompts: List[str],
    rounds: int = ROUNDS,
    pairs_per_round: int = PAIRS_PER_ROUND,
    seed: int = SEED,
) -> Dict:
    rng = random.Random(seed)

    candidates = [
        Candidate(id=f"P{i+1}", prompt=p.strip(), rating=DEFAULT_ELO)
        for i, p in enumerate(prompts)
    ]

    # Предрасчёт ответов (дороже, но честнее). Можно отключить JUDGE_SEES_ANSWERS.
    answers_cache: Dict[str, List[str]] = {}
    if JUDGE_SEES_ANSWERS:
        print("[run] generating answers for each candidate on test cases…")
        for c in candidates:
            answers_cache[c.id] = run_candidate_on_tests(c.prompt, test_cases)

    match_log = []

    for r in range(1, rounds + 1):
        pairs = sample_pairs(candidates, pairs_per_round, rng)
        if not pairs:
            break

        for a, b in pairs:
            a_ans = answers_cache.get(a.id) if JUDGE_SEES_ANSWERS else None
            b_ans = answers_cache.get(b.id) if JUDGE_SEES_ANSWERS else None

            winner_id, reason = judge_pair(description, test_cases, a, b, a_ans, b_ans)

            if winner_id == "DRAW":
                s_a = 0.5
            elif winner_id == a.id:
                s_a = 1.0
            else:
                s_a = 0.0

            old_a, old_b = a.rating, b.rating
            a.rating, b.rating = update_elo(a.rating, b.rating, s_a, k=K_FACTOR)

            match_log.append({
                "round": r,
                "a": a.id,
                "b": b.id,
                "winner": winner_id,
                "reason": reason,
                "elo_before": {a.id: old_a, b.id: old_b},
                "elo_after": {a.id: a.rating, b.id: b.rating},
            })

        # лёгкая “перетасовка” по рейтингу, чтобы пары были более информативными
        candidates.sort(key=lambda c: c.rating, reverse=True)

    candidates.sort(key=lambda c: c.rating, reverse=True)

    return {
        "candidates": candidates,
        "match_log": match_log,
    }


# =========================
# DEMO / ENTRYPOINT
# =========================

if __name__ == "__main__":
    description = "Напиши ограничения по использованию бланшированых свежезамороженных овощей"
    test_cases = [
        "Требуется морозильное хранение",
        "Нужна стабильная холодовая цепь при доставке",
        "После разморозки нельзя повторно замораживать",
        "Занимает место в морозильной камере",
        "Требует планирования объёмов разморозки",
        "Зависимость от наличия морозильного оборудования",
        "Можно ли размораживать овощи?",
        "Когда Цена овощного полуфабриката выше чем цена сырого в сезон, а когда ниже"
    ]

    N = 6  # количество кандидатов
    prompts = generate_candidate_prompts(description, test_cases, n=N)

    result = run_elo_eval(description, test_cases, prompts, rounds=10, pairs_per_round=6, seed=42)

    print("\n=== LEADERBOARD (ELO) ===")
    for c in result["candidates"]:
        print(f"{c.id}\tELO={c.rating:.1f}\t{_safe_truncate(c.prompt, 120)}")

    top = result["candidates"][0]
    print("\n=== BEST PROMPT ===")
    print(top.prompt)

    saved = save_prompts_to_file(description, test_cases, result)
    print(f"\nПромпты сохранены: {saved}")
