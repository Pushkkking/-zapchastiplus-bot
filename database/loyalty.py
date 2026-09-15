import re

# Порог общей суммы полученных покупок -> ставка кешбэка.
LOYALTY_LEVELS = [
    (0, 0, 'Старт'),
    (5_000, 1, '🥉 Bronze'),
    (10_000, 2, '🥈 Silver'),
    (20_000, 3, '🥇 Gold'),
    (50_000, 4, '💎 Platinum'),
    (100_000, 5, '👑 VIP'),
]


def parse_amount(text):
    """Extract the final/total ruble amount from an offer text."""
    if not text:
        return 0.0
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    candidates = []
    for line in lines:
        low = line.lower()
        if any(marker in low for marker in ('итого', 'всего', 'к оплате', 'сумма')):
            candidates.extend(
                re.findall(r'(\d[\d\s]*[.,]?\d*)\s*(?:₽|руб\.?|р\.)', line, flags=re.I)
            )
    if not candidates:
        candidates = re.findall(
            r'(\d[\d\s]*[.,]?\d*)\s*(?:₽|руб\.?|р\.)',
            str(text),
            flags=re.I,
        )
    if not candidates:
        return 0.0
    raw = candidates[-1].replace(' ', '').replace(',', '.')
    try:
        return float(raw)
    except ValueError:
        return 0.0


def get_level(total_amount):
    level = LOYALTY_LEVELS[0]
    for item in LOYALTY_LEVELS:
        if total_amount >= item[0]:
            level = item
        else:
            break
    return level[2], level[1]


def get_next_level(total_amount):
    for threshold, rate, name in LOYALTY_LEVELS:
        if total_amount < threshold:
            return threshold, rate, name
    return None


def calculate_cashback(total_after_purchase, purchase_amount):
    """Cashback for a purchase based on the tier reached after that purchase."""
    _, rate = get_level(total_after_purchase)
    return round(purchase_amount * rate / 100, 2)
