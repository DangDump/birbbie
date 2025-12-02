from datetime import timedelta, datetime
import discord
from utils import Paginator
import os


def DefaultTypes():
    return [
        "Activity Notice",
        "Verbal Warning",
        "Warning",
        "Strike",
        "Demotion",
        "Termination",
    ]


def IsSeperateBot():
    return any(
        [
            os.getenv("CUSTOM_GUILD"),
            os.getenv("DEFAULT_ALLOWED_SERVERS"),
            os.getenv("REMOVE_EMOJIS"),
        ]
    )


async def PaginatorButtons(extra: list = None):
    Sep = IsSeperateBot()
    emojis = {
        "first": "",
        "previous": "",
        "next": "",
        "last": "",
    }
    paginator = Paginator.Simple(
        PreviousButton=discord.ui.Button(
            emoji=emojis["previous"] if not Sep else None,
            label="<<" if Sep else None,
        ),
        NextButton=discord.ui.Button(
            emoji=emojis["next"] if not Sep else None,
            label=">>" if Sep else None,
        ),
        FirstEmbedButton=discord.ui.Button(
            emoji=emojis["first"] if not Sep else None,
            label="<<" if Sep else None,
        ),
        LastEmbedButton=discord.ui.Button(
            emoji=emojis["last"] if not Sep else None,
            label=">>" if Sep else None,
        ),
        InitialPage=0,
        timeout=360,
        extra=extra or [],
    )
    return paginator


async def strtotime(duration: str, *, back: bool = False, Interger: bool = False, DifferentNow: bool = False):

    now = datetime.now() if not DifferentNow else DifferentNow
    units = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
        "w": 604800,
    }

    duration = duration.lower().strip()
    TotalS = 0
    current = ""
    for char in duration:
        if char.isdigit():
            current += char
        elif char in units:
            if not current:
                raise ValueError("Invalid format: missing number before unit.")
            TotalS += int(current) * units[char]
            current = ""
        else:
            raise ValueError(f"Unknown character '{char}' in duration.")

    if Interger:
        return TotalS
    elif back:
        return now - timedelta(seconds=TotalS)
    else:
        return now + timedelta(seconds=TotalS)


def ordinal(n):
    if 10 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def Replace(text, replacements):
    if text is None:
        return text
    for placeholder, replacement in replacements.items():
        if isinstance(replacement, (str, int, float)):
            text = text.replace(placeholder, str(replacement))
        elif isinstance(replacement, tuple) and len(replacement) > 0:
            text = text.replace(placeholder, str(replacement[0]))
        else:
            text = text.replace(placeholder, "")
    return text
