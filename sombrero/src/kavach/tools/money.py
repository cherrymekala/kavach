"""Amount formatting, shared by the documents Kavach writes and the replies it sends.

Indian claims are grouped the way Indian readers expect (1,23,45,678), which is not what
Python's `,` format does; the other packs use their own symbol.
"""


def indian(n: int) -> str:
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return ",".join([head, *groups, tail]) if head else ",".join([*groups, tail])


def money(amount: float | None, currency: str | None) -> str:
    if amount is None:
        return ""
    if currency == "INR":
        return f"Rs. {indian(round(amount))}"
    symbol = {"SGD": "S$", "MYR": "RM"}.get(currency or "", currency or "")
    return f"{symbol} {amount:,.0f}".strip()
