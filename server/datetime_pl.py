from datetime import datetime

from num2words import num2words

WEEKDAYS_PL = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]
MONTHS_PL = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
             "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]


def _feminine(ordinal: str) -> str:
    words = []
    for word in ordinal.split():
        if word.endswith("gi"):       # drugi -> druga
            words.append(word[:-1] + "a")
        elif word.endswith("i"):      # trzeci -> trzecia
            words.append(word + "a")
        elif word.endswith("y"):      # czternasty -> czternasta
            words.append(word[:-1] + "a")
        else:
            words.append(word)
    return " ".join(words)


def _genitive(ordinal: str) -> str:
    words = []
    for word in ordinal.split():
        if word.endswith("i"):        # trzeci -> trzeciego
            words.append(word + "ego")
        elif word.endswith("y"):      # dwunasty -> dwunastego
            words.append(word[:-1] + "ego")
        else:                         # 'dwa tysiące'
            words.append(word)
    return " ".join(words)


def date_time_in_words(now: datetime | None = None) -> str:
    now = now or datetime.now()

    weekday = WEEKDAYS_PL[now.weekday()]
    day = _genitive(num2words(now.day, lang="pl", to="ordinal"))
    month = MONTHS_PL[now.month - 1]
    year = _genitive(num2words(now.year, lang="pl", to="ordinal"))

    if now.hour == 0 and now.minute == 0:
        time_words = "północ"
    else:
        hour = "zero" if now.hour == 0 else _feminine(num2words(now.hour, lang="pl", to="ordinal"))
        if now.minute == 0:
            minute = "zero zero"
        elif now.minute < 10:
            minute = f"zero {num2words(now.minute, lang='pl')}"
        else:
            minute = num2words(now.minute, lang="pl")
        time_words = f"godzina {hour} {minute}"

    return f"{weekday}, {day} {month} {year}, {time_words}"
