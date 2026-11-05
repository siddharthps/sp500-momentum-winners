"""Telegram messages (#38): the monthly picks to a public channel, operational alerts to a private
chat (decisions.md, 5 Nov).

    uv run python -m sp500_momentum.notify test            # send a test message to both chats
    uv run python -m sp500_momentum.notify test --dry-run  # print it instead

Settings come from .env (git-ignored), and later from GitHub Secrets:
    TELEGRAM_BOT_TOKEN    from @BotFather
    TELEGRAM_CHANNEL_ID   the public channel, e.g. @my_channel (the bot must be an admin)
    TELEGRAM_CHAT_ID      your private chat with the bot

Rules:
- A failed or unconfigured notification never fails the job that sends it: it's logged and
  skipped. With no token set, every message is just logged.
- The token is never logged: errors are reported by type, because a request error's text
  contains the URL, and the URL contains the token.
- Send-only (one HTTPS request per message): no polling and no server.
"""

from dataclasses import dataclass
import html
import os

from loguru import logger
import pandas as pd
import requests
import typer

API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_LENGTH = 4096  # Telegram's limit per message
OPEN_LOCAL = pd.Timedelta(hours=8, minutes=30)  # the US open in PC time (US Central)
FOOTER = (
    "<i>Research output, not advice. In backtests the model didn't beat the plain 6-month rule, "
    "and neither clearly beat SPY per unit of risk.</i>"
)
STRATEGY_NAMES = {"model": "Headline model (XGBoost)", "rule": "Rule: top 6-month return"}

app = typer.Typer(help="Telegram notifications.")


@dataclass(frozen=True)
class Settings:
    token: str | None
    channel: str | None  # public: the monthly picks
    chat: str | None  # private: alerts and the nightly AV summary

    @classmethod
    def from_env(cls) -> "Settings":
        get = lambda k: os.getenv(k) or None
        return cls(get("TELEGRAM_BOT_TOKEN"), get("TELEGRAM_CHANNEL_ID"), get("TELEGRAM_CHAT_ID"))


def send(text: str, chat: str | None, settings: Settings, dry_run: bool = False) -> bool:
    """Send one message; True if Telegram accepted it. Never raises."""
    text = text if len(text) <= MAX_LENGTH else text[: MAX_LENGTH - 20] + "\n… (cut)"
    if dry_run or not settings.token or not chat:
        why = "dry run" if dry_run else "Telegram not configured"
        logger.info(f"[{why}] message not sent:\n{text}")
        return False
    try:
        r = requests.post(
            API.format(token=settings.token),
            json={
                "chat_id": chat,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )
    except requests.RequestException as e:  # the message would contain the token
        logger.warning(f"Telegram message not sent: {type(e).__name__}")
        return False
    if not r.ok:
        logger.warning(f"Telegram message not sent: HTTP {r.status_code}")
        return False
    return True


def public(text: str, dry_run: bool = False) -> bool:
    s = Settings.from_env()
    return send(text, s.channel, s, dry_run)


def private(text: str, dry_run: bool = False) -> bool:
    s = Settings.from_env()
    return send(text, s.chat, s, dry_run)


# ---------------------------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------------------------


def tradeable(made_at: str, decision_date: str) -> bool:
    """Were the picks made before the next open they trade at? (The first file, for Oct 2026,
    was made days later: nothing leaks, but it couldn't have been traded.)"""
    trade_day = (pd.Timestamp(decision_date) + pd.offsets.BDay(1)).normalize()
    return pd.Timestamp(made_at) < trade_day + OPEN_LOCAL


def live_result(
    record: pd.DataFrame | None, prices: pd.DataFrame, asof: pd.Period
) -> pd.DataFrame | None:
    """How the most recent tradeable picks with a finished month since did, per strategy: the
    average of each pick's return from the next open to the following month-end close, SPY's
    over the same span, and how many picks beat it. `asof` is the current (unfinished) month:
    a decision counts only once the month after it has ended. None when there's no such month."""
    if record is None or record.empty:
        return None
    ok = record[[tradeable(m, d) for m, d in zip(record["made_at"], record["decision_date"])]]
    months = pd.PeriodIndex(pd.to_datetime(ok["decision_date"]), freq="M")
    p = prices.assign(month=pd.PeriodIndex(prices["month"], freq="M")).set_index(
        ["price_ticker", "month"]
    )
    done = months[months + 1 < asof]  # the month the picks were held has ended
    if done.empty:
        return None
    m = done.max()
    picks = ok[months == m]

    def ret(ticker: str) -> float:
        try:
            return p.loc[(ticker, m + 1), "close_adj"] / p.loc[(ticker, m), "entry_px"] - 1
        except KeyError:
            return float("nan")

    spy = ret("SPY")
    rows = []
    for s, g in picks.groupby("strategy"):
        r = pd.Series([ret(t) for t in g["price_ticker"]])
        rows.append(
            {
                "strategy": s,
                "decision": str(m),
                "ret": r.mean(),
                "spy": spy,
                "beat": int((r > spy).sum()),
                "priced": int(r.notna().sum()),
                "picks": len(g),
            }
        )
    return pd.DataFrame(rows)


def picks_message(
    picks: pd.DataFrame,
    decision: pd.Timestamp,
    result: pd.DataFrame | None,
    changes: tuple[list[str], list[str]],
    priced: float,
) -> str:
    """The monthly message: both lists, what changed, last month's live result, the footer."""
    e = html.escape
    trade = (decision + pd.offsets.BDay(1)).strftime("%a %d %b %Y")
    lines = [
        f"<b>S&amp;P 500 momentum: picks at the {decision:%d %b %Y} close</b>",
        f"Buy at the next open ({trade}), equal weight, hold one month.",
        "",
    ]
    for s in ["model", "rule"]:
        names = ", ".join(e(t) for t in picks.loc[picks["strategy"] == s, "ticker"])
        lines += [f"<b>{STRATEGY_NAMES[s]}</b>", names, ""]
    if result is not None and not result.empty:
        r0 = result.iloc[0]
        lines.append(f"<b>Last month ({e(r0['decision'])} picks, next open to month-end)</b>")
        for _, r in result.iterrows():
            lines.append(
                f"{STRATEGY_NAMES[r['strategy']]}: {r['ret']:+.1%} vs SPY {r['spy']:+.1%}; "
                f"{r['beat']} of {r['priced']} beat SPY"
            )
        lines.append("")
    added, removed = changes
    lines.append(
        f"Data: {priced:.0%} of members priced; index changes this month: "
        f"+{len(added)} ({e(', '.join(added)) or '-'}), "
        f"−{len(removed)} ({e(', '.join(removed)) or '-'})."
    )
    lines += ["", FOOTER]
    return "\n".join(lines)


def alert_message(job: str, problems: list[str]) -> str:
    """A failure, exactly as the job's checks state it."""
    items = "\n".join(f"• {html.escape(p)}" for p in problems)
    return f"❗ <b>{html.escape(job)} stopped</b>\n{items}"


def av_message(tonight: dict[str, int], left: int, recovered: int, quota_hit: bool) -> str:
    """The nightly Alpha Vantage summary (private)."""
    if left == 0:
        return (
            "✅ <b>Alpha Vantage queue is empty.</b> Every missing ticker has been tried. "
            "Unregister the task (sp500-momentum-av-pull) and run the final rebuild (#20)."
        )
    parts = ", ".join(f"{k} {v}" for k, v in sorted(tonight.items())) or "nothing pulled"
    extra = (f"; recovered {recovered} files from a killed run" if recovered else "") + (
        "; stopped at the quota" if quota_hit else ""
    )
    return f"Alpha Vantage pull: {sum(tonight.values())} tried ({parts}){extra}. {left} left."


def index_changes(changes: pd.DataFrame, start, end) -> tuple[list[str], list[str]]:
    """Tickers added and removed in (start, end] by Wikipedia's changes table."""
    d = pd.to_datetime(changes["date"])
    c = changes[(d > pd.Timestamp(start)) & (d <= pd.Timestamp(end))]
    clean = lambda s: sorted(str(t) for t in s.dropna())
    return clean(c["added_ticker"]), clean(c["removed_ticker"])


def chats_from_updates(updates: dict) -> list[dict]:
    """The distinct chats in a getUpdates reply (private chats and channels the bot saw)."""
    seen = {}
    for u in updates.get("result", []):
        msg = u.get("message") or u.get("channel_post") or u.get("my_chat_member") or {}
        chat = msg.get("chat", {})
        if "id" in chat:
            name = chat.get("title") or chat.get("username") or chat.get("first_name") or ""
            seen[chat["id"]] = {"id": chat["id"], "type": chat.get("type", ""), "name": name}
    return list(seen.values())


@app.command("find-chats")
def find_chats():
    """List the chats the bot has seen (setup: message the bot, post in the channel, then run
    this). Prints to the terminal only; copy the IDs into .env."""
    s = Settings.from_env()
    if not s.token:
        logger.error("TELEGRAM_BOT_TOKEN is not set (put it in .env)")
        raise typer.Exit(code=1)
    try:
        r = requests.get(f"https://api.telegram.org/bot{s.token}/getUpdates", timeout=20)
        chats = chats_from_updates(r.json())
    except (requests.RequestException, ValueError) as e:
        logger.error(f"Couldn't read the bot's updates: {type(e).__name__}")
        raise typer.Exit(code=1) from None
    if not chats:
        print("No chats yet: send the bot a message, and post once in the channel, then rerun.")
    for c in chats:
        print(f"{c['type']:10s} {c['id']}  {c['name']}")


@app.command()
def test(dry_run: bool = typer.Option(False, help="Print the messages instead of sending")):
    """Send a short test message to the public channel and the private chat."""
    s = Settings.from_env()
    logger.info(
        f"token set: {bool(s.token)}; channel set: {bool(s.channel)}; chat set: {bool(s.chat)}"
    )
    ok_public = public("Test message from sp500-momentum-winners (public channel).", dry_run)
    ok_private = private("Test message from sp500-momentum-winners (private chat).", dry_run)
    logger.info(f"sent: public {ok_public}, private {ok_private}")


if __name__ == "__main__":
    app()
