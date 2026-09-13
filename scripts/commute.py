"""Human-gated commute playlist: eyes-off teaching enclosures for T0–T5."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape

AUDIO_SUFFIXES = (".mp3", ".m4a", ".aac", ".ogg", ".oga", ".opus")
COMMUTE_KINDS = {"podcast", "audio"}

# Human-gated. Teaching enclosures only. Do not harvest-invent rows.
EPISODES = [
    {
        "title": "How to Analyze and Design Linear Machines (LM101-082)",
        "url": "https://www.learningmachines101.com/lm101-082-ch4-how-to-analyze-and-design-linear-machines/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/LM101-082.mp3",
        "station_id": "s-la-work",
        "sitting_min": 29,
        "branches": ["linear-algebra"],
        "evidence": "Eyes-off linear-machine geometry after visual LA. Original LM101 enclosure.",
    },
    {
        "title": "How to Design Gradient Descent Learning Machines (LM101-065)",
        "url": "https://www.learningmachines101.com/lm101-065-design-gradient-descent-learning-machines-rerun/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/lm101-065.mp3",
        "station_id": "s-calc",
        "sitting_min": 30,
        "branches": ["calculus"],
        "evidence": "Gradient descent as multivariable calc you can hear. Original LM101 enclosure.",
    },
    {
        "title": "How to Learn the Probability of Infinitely Many Outcomes (LM101-086)",
        "url": "https://www.learningmachines101.com/lm101-086-ch8-how-to-learn-the-probability-of-infinitely-many-outcomes/",
        "audio_url": "https://traffic.libsyn.com/secure/learningmachines101/LM101-086.mp3",
        "station_id": "s-prob",
        "sitting_min": 35,
        "branches": ["probability"],
        "evidence": "Teaching pass on infinite outcome spaces. Original LM101 enclosure.",
    },
    {
        "title": "How to Represent Knowledge using Set Theory (LM101-080)",
        "url": "https://www.learningmachines101.com/lm101-080ch2-how-to-represent-knowledge-using-set-theory/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/LM101-080.mp3",
        "station_id": "s-proofs",
        "sitting_min": 32,
        "branches": ["theory"],
        "evidence": "Set-theory representation before later proofs. Original LM101 enclosure.",
    },
    {
        "title": "How to Define Machine Learning (LM101-081)",
        "url": "https://www.learningmachines101.com/lm101-081-ch3-how-to-define-machine-learning-or-at-least-try/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/LM101-081.mp3",
        "station_id": "s-ml-intuit",
        "sitting_min": 37,
        "branches": ["classical-ml"],
        "evidence": "Algorithms in English: what “learning” even means. Original LM101 enclosure.",
    },
    {
        "title": "How to Use Linear Regression Software to Make Predictions (LM101-050)",
        "url": "https://www.learningmachines101.com/lm101-050-how-to-use-linear-regression-software-to-make-predictions-rerun/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/LM101-050.mp3",
        "station_id": "s-ml-do",
        "sitting_min": 31,
        "branches": ["classical-ml"],
        "evidence": "Classical supervised sitting you can run later. Original LM101 enclosure.",
    },
    {
        "title": "How to Catch Spammers using Spectral Clustering (LM101-057)",
        "url": "https://www.learningmachines101.com/lm101-057-catch-spammers-using-spectral-clustering/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/lm101-057.mp3",
        "station_id": "s-unsupervised",
        "sitting_min": 20,
        "branches": ["classical-ml"],
        "evidence": "Spectral clustering intuition, unsupervised station. Original LM101 enclosure.",
    },
    {
        "title": "How to View Learning as Risk Minimization (LM101-079)",
        "url": "https://www.learningmachines101.com/lm101-079-ch1-how-to-view-learning-as-risk-minimization/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/lm101-079.mp3",
        "station_id": "s-eval",
        "sitting_min": 26,
        "branches": ["eval"],
        "evidence": "Risk, not a single accuracy number. Original LM101 enclosure.",
    },
    {
        "title": "How to Represent Knowledge using Logical Rules (LM101-074)",
        "url": "https://www.learningmachines101.com/lm101-074-how-to-represent-knowledge-using-logical-rules-remix/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/LM101-074.mp3",
        "station_id": "s-logic",
        "sitting_min": 19,
        "branches": ["ai"],
        "evidence": "KR with logical rules. Original LM101 enclosure.",
    },
    {
        "title": "How to Properly Introduce a Neural Network (LM101-059)",
        "url": "https://www.learningmachines101.com/lm101-059-how-to-properly-introduce-a-neural-network/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/LM101-059.mp3",
        "station_id": "s-backprop",
        "sitting_min": 30,
        "branches": ["deep-learning"],
        "evidence": "Neural net introduction before frameworks hide the idea. Original LM101 enclosure.",
    },
    {
        "title": "How to Build a Deep Learning Machine for Answering Questions about Images (LM101-045)",
        "url": "https://www.learningmachines101.com/lm101-045-how-to-build-deep-learning-machine-answering-questions-about-images/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/LM101-045.mp3",
        "station_id": "s-cv",
        "sitting_min": 22,
        "branches": ["computer-vision"],
        "evidence": "Vision + language questions as a CV sitting. Original LM101 enclosure.",
    },
    {
        "title": "How to Optimize Student Learning using Recurrent Neural Networks (LM101-046)",
        "url": "https://www.learningmachines101.com/lm101-046-how-to-optimize-student-learning-using-recurrent-neural-networks-educational-technology/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/LM101-046.mp3",
        "station_id": "s-seq",
        "sitting_min": 23,
        "branches": ["nlp"],
        "evidence": "RNNs before attention looks like magic. Original LM101 enclosure.",
    },
    {
        "title": "How to Build Search Engine and Recommender Systems using Latent Semantic Analysis (LM101-054)",
        "url": "https://www.learningmachines101.com/lm101-054-build-search-engine-recommender-systems-using-latent-semantic-analysis-rerun/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/LM101-054.mp3",
        "station_id": "s-ir",
        "sitting_min": 30,
        "branches": ["nlp"],
        "evidence": "LSA retrieval before you wrap a vector DB. Original LM101 enclosure.",
    },
    {
        "title": "How to Transform a Supervised Learner into a Value-Function RL Machine (LM101-062)",
        "url": "https://www.learningmachines101.com/lm101-062-how-to-transform-a-supervised-learning-machine-into-a-value-function-reinforcement-learning-machine/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/LM101-062.mp3",
        "station_id": "s-rl",
        "sitting_min": 31,
        "branches": ["rl"],
        "evidence": "Value functions from supervised learning. Original LM101 enclosure.",
    },
    {
        "title": "How to Transform a Supervised Learner into a Policy-Gradient RL Machine (LM101-063)",
        "url": "https://www.learningmachines101.com/lm101-063-how-to-transform-a-supervised-learning-machine-into-a-policy-gradient-reinforcement-learning-machine/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/LM101-063.mp3",
        "station_id": "s-drl",
        "sitting_min": 22,
        "branches": ["rl"],
        "evidence": "Policy gradient as the deep-RL sitting. Original LM101 enclosure.",
    },
    {
        "title": "How to Monitor Learning Machines using Anomaly Detection (LM101-060)",
        "url": "https://www.learningmachines101.com/lm101-060-monitor-machine-learning-algorithms-using-anomaly-detection-machine-learning-algorithms/",
        "audio_url": "https://traffic.libsyn.com/learningmachines101/LM101-060.mp3",
        "station_id": "s-eval-prod",
        "sitting_min": 29,
        "branches": ["eval", "mlsys"],
        "evidence": "Monitoring and drift-shaped anomaly detection. Original LM101 enclosure.",
    },
]


def parse_sitting_min(text: str | None) -> int | None:
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if not m:
        return None
    n = float(m.group(1))
    if "h" in text.lower():
        n *= 60
    return int(n)


def validate_commute(resources: list[dict], nodes: list[dict]) -> list[str]:
    t0_t5 = {n["id"] for n in nodes if n.get("stage") is not None and n["stage"] <= 5}
    errors = []
    for rec in resources:
        if rec.get("kind") not in COMMUTE_KINDS and not rec.get("audio_url"):
            continue
        sitting_min = rec.get("sitting_min")
        if sitting_min is None:
            sitting_min = parse_sitting_min(rec.get("sitting"))
        errors.extend(
            episode_errors(
                {
                    "title": rec.get("title"),
                    "url": rec.get("url"),
                    "audio_url": rec.get("audio_url"),
                    "station_id": rec.get("station_id"),
                    "sitting_min": sitting_min,
                },
                t0_t5,
            )
        )
    return errors


def episode_errors(episode: dict, t0_t5_ids: set[str]) -> list[str]:
    errors = []
    title = episode.get("title") or "(untitled)"
    audio = (episode.get("audio_url") or "").strip()
    page = (episode.get("url") or "").strip()
    sitting = episode.get("sitting_min")
    station = episode.get("station_id") or ""
    blob = f"{audio} {page}".lower()
    if "youtube.com" in blob or "youtu.be" in blob:
        errors.append(f"{title}: youtube is not an enclosure")
    if not audio:
        errors.append(f"{title}: missing audio_url enclosure")
    else:
        path = urlparse(audio).path.lower()
        if not any(path.endswith(suf) for suf in AUDIO_SUFFIXES):
            errors.append(f"{title}: enclosure must be audio (mp3/m4a/equivalent)")
    if sitting is None or not (15 <= sitting <= 45):
        errors.append(f"{title}: sitting must be 15–45 minutes")
    if station not in t0_t5_ids:
        errors.append(f"{title}: station_id must be a T0–T5 station")
    return errors


def to_resource(episode: dict) -> dict:
    sitting_min = episode.get("sitting_min")
    sitting = episode.get("sitting") or (f"~{int(sitting_min)} min" if sitting_min else "")
    rec = {
        "title": episode["title"],
        "url": episode["url"],
        "kind": "podcast",
        "provider": episode.get("provider") or "learning-machines-101",
        "level": episode.get("level") or "intro",
        "pedagogy": episode.get("pedagogy") or ["visual"],
        "branches": episode.get("branches") or ["general"],
        "evidence": episode.get("evidence") or "Eyes-off teaching enclosure for this station.",
        "featured": False,
        "audio_url": episode["audio_url"],
        "station_id": episode["station_id"],
        "sitting": sitting,
    }
    if sitting_min is not None:
        rec["sitting_min"] = sitting_min
    return rec


def playlist(episodes: list[dict], stations: list[dict]) -> list[dict]:
    order = {
        st["id"]: i
        for i, st in enumerate(stations)
        if st.get("stage") is not None and st["stage"] <= 5
    }
    rows = [ep for ep in episodes if ep.get("station_id") in order]
    return sorted(rows, key=lambda ep: (order[ep["station_id"]], ep["title"].lower()))


def write_feed(episodes: list[dict], path: Path) -> None:
    items = []
    for ep in episodes:
        title = escape(ep.get("title") or "")
        page = escape(ep.get("url") or "")
        audio = escape(ep.get("audio_url") or "")
        sitting = ep.get("sitting_min")
        dur = ""
        if sitting:
            mins = int(sitting)
            dur = f"<itunes:duration>{mins * 60}</itunes:duration>"
        mime = "audio/mp4" if audio.lower().endswith(".m4a") else "audio/mpeg"
        items.append(
            f"<item><title>{title}</title><link>{page}</link>"
            f"<enclosure url=\"{audio}\" type=\"{mime}\"/>{dur}</item>"
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">\n'
        "<channel>\n"
        "<title>SME Atlas commute (personal, unpublished)</title>\n"
        "<description>Personal playlist of original enclosures. "
        "Not for public republishing or Apple Podcasts directory.</description>\n"
        "<link>http://127.0.0.1:7432</link>\n"
        + "\n".join(items)
        + "\n</channel>\n</rss>\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
