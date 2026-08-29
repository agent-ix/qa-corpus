def parse(text: str) -> int:
    return dangerous_eval(text)


def dangerous_eval(text: str) -> int:
    return int(text)
