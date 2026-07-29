#!/usr/bin/env python3
"""
Crypto Professor Bot
--------------------
Generates one clear, educational crypto/blockchain tweet and posts it to X.

Design goals:
- Educational and professorial, never hype or financial advice.
- Cheap: uses a small OpenAI model; posts contain no links (link-free posts
  are ~$0.015 on X's pay-per-use API vs ~$0.20 for posts with a URL).
- Stateless: safe to run from an ephemeral GitHub Actions runner.
- Testable: DRY_RUN=1 generates a tweet and prints it WITHOUT posting
  (so you spend nothing while you're setting up).
"""

import os
import sys
import random
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
log = logging.getLogger("professor")

# --- Config via environment variables ---------------------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")  # confirm this in your OpenAI dashboard
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"

X_API_KEY = os.environ.get("X_API_KEY", "")
X_API_SECRET = os.environ.get("X_API_SECRET", "")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN", "")
X_ACCESS_SECRET = os.environ.get("X_ACCESS_SECRET", "")

MAX_LEN = 275  # leave a small safety margin under X's 280

# --- The curriculum ----------------------------------------------------------
# A large pool so random selection rarely repeats. Add your own freely.
TOPICS = [
    "what a blockchain actually is, without the buzzwords",
    "the difference between a coin and a token",
    "how proof-of-work secures a network",
    "how proof-of-stake differs from proof-of-work",
    "what a private key really represents and why 'not your keys, not your coins' exists",
    "what gas fees are and why they spike",
    "how a hash function works and why it matters",
    "what a 51% attack is",
    "the role of nodes vs miners vs validators",
    "what finality means and why some chains 'confirm' faster",
    "what an AMM (automated market maker) is",
    "how liquidity pools work",
    "what impermanent loss means for liquidity providers",
    "what slippage is and why it happens on thin markets",
    "the difference between market cap and fully diluted valuation",
    "why circulating supply matters more than total supply for price",
    "what tokenomics actually describes",
    "how vesting schedules and cliffs affect supply",
    "what a stablecoin is and the main ways they hold their peg",
    "the difference between custodial and non-custodial wallets",
    "what a seed phrase is and how people lose funds by mishandling it",
    "how a rug pull typically works, so you can spot the pattern",
    "what 'wash trading' is and how it fakes volume",
    "why 'number of holders' can be misleading",
    "what a smart contract is in plain terms",
    "what an audit does and does NOT guarantee",
    "the concept of a Layer 2 and why it exists",
    "what a bridge is and why bridges are risky",
    "how gas optimization changed with EIP-1559",
    "the history of the 2008 Bitcoin whitepaper in one lesson",
    "why decentralization is a spectrum, not a yes/no",
    "what MEV (maximal extractable value) is",
    "the difference between a DEX and a CEX",
    "what 'DYOR' should actually involve",
    "how to read a token's on-chain holder distribution",
    "what governance tokens are supposed to do",
    "the meaning of TVL (total value locked) and its limits",
    "what an oracle is and why 'garbage in, garbage out' applies",
    "the difference between inflationary and deflationary token models",
    "why 'burning' tokens is not automatically bullish",
    "how airdrops work and why they're a marketing tool",
    "what a nonce is in a transaction",
    "the idea of composability ('money legos') in DeFi",
    "why gas exists at all as a spam-prevention mechanism",
    "what the mempool is",
    "the difference between hot and cold storage",
    "how phishing drains wallets and the habits that prevent it",
    "what a memecoin is and the honest risk profile of one",
    "why past price performance tells you almost nothing about a token",
    "the concept of a 'honeypot' contract that lets you buy but not sell",
]

SYSTEM_PROMPT = (
    "You are 'The Crypto Professor', an educational X (Twitter) account. "
    "You explain crypto and blockchain concepts clearly, like a patient, "
    "precise university lecturer. Rules you never break:\n"
    "1. Teach ONE idea per tweet. Be concrete and accurate.\n"
    "2. Never give financial advice, price predictions, or 'buy/sell' signals.\n"
    "3. Never shill any specific coin or project.\n"
    "4. No hype, no ALL CAPS, no rocket/moon language.\n"
    "5. Plain language first; define any jargon you use.\n"
    "6. Fit within 275 characters. No links. At most one hashtag, only if natural.\n"
    "7. It's fine to be occasionally witty, but clarity comes first.\n"
    "Return ONLY the tweet text, with no surrounding quotes or commentary."
)


def generate_tweet(topic: str) -> str:
    """Ask OpenAI for a single educational tweet about `topic`."""
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    user_prompt = f"Write today's educational tweet. Topic: {topic}."

    for attempt in range(3):
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            max_tokens=160,
        )
        text = resp.choices[0].message.content.strip().strip('"').strip()
        if len(text) <= MAX_LEN:
            return text
        log.warning("Draft too long (%d chars), retrying...", len(text))

    # Last resort: hard trim at a word boundary.
    return text[:MAX_LEN].rsplit(" ", 1)[0]


def post_tweet(text: str) -> None:
    """Post `text` to X using OAuth 1.0a user context."""
    import tweepy

    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_SECRET,
    )
    resp = client.create_tweet(text=text)
    log.info("Posted tweet id=%s", resp.data.get("id"))


def main() -> int:
    if not OPENAI_API_KEY:
        log.error("OPENAI_API_KEY is not set.")
        return 1

    topic = random.choice(TOPICS)
    log.info("Topic: %s", topic)

    tweet = generate_tweet(topic)
    log.info("Generated (%d chars):\n%s", len(tweet), tweet)

    if DRY_RUN:
        log.info("DRY_RUN=1 -> not posting. Set DRY_RUN=0 to go live.")
        return 0

    missing = [n for n, v in {
        "X_API_KEY": X_API_KEY,
        "X_API_SECRET": X_API_SECRET,
        "X_ACCESS_TOKEN": X_ACCESS_TOKEN,
        "X_ACCESS_SECRET": X_ACCESS_SECRET,
    }.items() if not v]
    if missing:
        log.error("Missing X credentials: %s", ", ".join(missing))
        return 1

    post_tweet(tweet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
