#!/usr/bin/env python3
"""Compile harvest markdown + curated winners into resources.json and graph.json."""

from __future__ import annotations

import json
import re
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlunparse

ROOT = Path(__file__).resolve().parents[1]
HARVEST = ROOT / "harvest"
DATA = ROOT / "data"

import sys

sys.path.insert(0, str(Path(__file__).parent))
from assignments import apply_placements, filter_placements, load_assignments
from commute import EPISODES, playlist, to_resource, write_feed
from graph_spec import CURATED_EXTRA
from graph_spec import STATIONS as GRAPH_STATIONS
from topic_request import harvest_files_from_disk

LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
HEADING_RE = re.compile(r"^#{1,4}\s+(.*)$", re.M)

DENY = (
    "shields.io",
    "badge",
    "travis-ci",
    "circleci",
    "cdn.rawgit",
    "img.shields",
    "gitter.im",
    "twitter.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "reddit.com",
    "sindresorhus/awesome",
    "libgen",
    "sci-hub",
    "thepiratebay",
    "1337x",
)

HOST_HINTS = (
    "coursera.org",
    "edx.org",
    "udacity.com",
    "youtube.com",
    "youtu.be",
    "ocw.mit.edu",
    "mit.edu",
    "stanford.edu",
    "berkeley.edu",
    "cmu.edu",
    "caltech.edu",
    "harvard.edu",
    "princeton.edu",
    "columbia.edu",
    "nyu.edu",
    "umich.edu",
    "cam.ac.uk",
    "ox.ac.uk",
    "huggingface.co",
    "fast.ai",
    "arxiv.org",
    "distill.pub",
    "paperswithcode.com",
    "nptel.ac.in",
    "pluralsight.com",
    "deeplearning.ai",
    "3blue1brown.com",
    "karpathy.ai",
    "openai.com",
    "deepmind",
    "pytorch.org",
    "tensorflow.org",
    "scikit-learn.org",
    "kaggle.com",
    "developers.google.com",
    "ai.google.dev",
    "mml-book.github.io",
    "probml.github.io",
    "incompleteideas.net",
    "deeplearningbook.org",
    "neuralnetworksanddeeplearning.com",
    "statquest.org",
    "lilianweng.github.io",
    "huyenchip.com",
    "d2l.ai",
    "manning.com",
    "oreilly.com",
    "jmlr.org",
    "pmlr.press",
    "neurips.cc",
    "openreview.net",
    "aclanthology.org",
    "themlbook.com",
    "ciml.info",
    "gaussianprocess.org",
    "otexts.com",
    "greenteapress.com",
    "nlp.stanford.edu",
    "nltk.org",
    "cs231n.github.io",
    "videolectures.net",
    "khanacademy.org",
    "gymnasium.farama.org",
    "lightning.ai",
    "wandb.ai",
    "colah.github.io",
    "atcold.github.io",
    "spinningup.openai.com",
    "www.cs.toronto.edu",
    "www.cs.cmu.edu",
    "www.robots.ox.ac.uk",
    "people.csail.mit.edu",
    "web.stanford.edu",
    "online.stanford.edu",
    "math.mit.edu",
    "see.stanford.edu",
    "classcentral.com",
    "nature.com",
    "openaccess.thecvf.com",
    "papers.nips.cc",
    "mitpress.mit.edu",
    "inference.org.uk",
    "inference.phy.cam.ac.uk",
    "bayes.wustl.edu",
    "full-stack-deep-learning.com",
    "madewithml.com",
    "course.fast.ai",
    "www.fast.ai",
    "learn.microsoft.com",
    "learn.nvidia.com",
    "cloud.google.com",
    "speechbrain",
    "spacy.io",
    "farama.org",
    "stable-baselines",
    "cleanrl",
    "amazon.com",
    "cambridge.org",
    "springer.com",
    "github.io",
)


def allowed(url: str) -> bool:
    u = url.lower()
    if any(d in u for d in DENY):
        return False
    host = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()
    if host.endswith(".edu") or host.endswith(".ac.uk") or host.endswith(".ac.in"):
        return True
    if any(h in host for h in HOST_HINTS):
        return True
    if host in {"github.com", "www.github.com"}:
        keys = (
            "course",
            "book",
            "lecture",
            "tutorial",
            "paper",
            "notes",
            "nanogpt",
            "micrograd",
            "fastai",
            "karpathy",
            "ml-youtube",
            "cs231",
            "cs229",
            "cs224",
            "deep-learning",
            "machine-learning",
            "spinningup",
            "annotated",
            "stat-learning",
            "probabilistic",
            "transformer",
            "diffusion",
            "reinforcement",
            "nlp",
            "computer-vision",
            "mml-book",
            "d2l",
            "practical-ml",
        )
        return any(k in path for k in keys)
    return False


KEEP_WWW = {"sktime.net"}


def normalize(url: str) -> str:
    url = url.strip().rstrip(").,]")
    p = urlparse(url)
    host = p.netloc.lower()
    if host.startswith("www."):
        bare = host[4:]
        if bare not in KEEP_WWW:
            host = bare
    query = ""
    if "youtube.com" in host or host == "youtu.be":
        qs = parse_qs(p.query)
        if host == "youtu.be":
            vid = p.path.strip("/")
            return f"https://www.youtube.com/watch?v={vid}"
        if "list" in qs:
            return f"https://www.youtube.com/playlist?list={qs['list'][0]}"
        if "v" in qs:
            return f"https://www.youtube.com/watch?v={qs['v'][0]}"
    if "arxiv.org" in host:
        path = p.path.replace("/pdf/", "/abs/").replace(".pdf", "")
        return f"https://arxiv.org{path}"
    return urlunparse(("https", host, p.path.rstrip("/"), "", query, ""))


def kind_of(url: str, title: str) -> str:
    u = url.lower()
    t = title.lower()
    if "arxiv.org" in u or "paperswithcode" in u or "openreview" in u:
        return "paper"
    if any(x in u for x in ("manning.com", "oreilly.com", "deeplearningbook", "book", "isbn")) or "book" in t:
        return "book"
    if "youtube.com" in u or "youtu.be" in u or "videolectures" in u:
        return "lecture-series" if "playlist" in u else "lecture-series"
    if any(x in u for x in ("coursera.org", "edx.org", "udacity.com", "nptel", "ocw.mit", "fast.ai", "huggingface.co/learn", "pluralsight")):
        return "course"
    if "github.com" in u:
        return "repo"
    return "article"


def provider_of(url: str) -> str:
    host = urlparse(url).netloc.lower().lstrip("www.")
    mapping = {
        "coursera.org": "coursera",
        "pluralsight.com": "pluralsight",
        "youtube.com": "youtube",
        "youtu.be": "youtube",
        "arxiv.org": "arxiv",
        "huggingface.co": "huggingface",
        "fast.ai": "fast.ai",
        "course.fast.ai": "fast.ai",
        "nptel.ac.in": "nptel",
        "onlinecourses.nptel.ac.in": "nptel",
        "deeplearning.ai": "deeplearning.ai",
        "ocw.mit.edu": "mit-ocw",
        "stanford.edu": "stanford",
        "web.stanford.edu": "stanford",
        "manning.com": "manning",
        "kaggle.com": "kaggle",
        "3blue1brown.com": "3blue1brown",
        "karpathy.ai": "karpathy",
        "d2l.ai": "d2l",
    }
    for k, v in mapping.items():
        if k in host:
            return v
    if host.endswith(".edu"):
        return "university"
    return host.split(".")[0]


def access_of(provider: str) -> str:
    if provider == "coursera":
        return "coursera"
    if provider == "pluralsight":
        return "pluralsight"
    return "free"


def branches_of(title: str, url: str, heading: str) -> list[str]:
    blob = f"{title} {url} {heading}".lower()
    rules = [
        ("linear-algebra", ("linear algebra", "matrix", "svd", "eigen")),
        ("calculus", ("calculus", "gradient", "backprop")),
        ("probability", ("probability", "bayes", "statistic", "inference")),
        ("optimization", ("optim", "convex", "sgd")),
        ("classical-ml", ("machine learning", "supervised", "scikit", "xgboost", "tree", "svm")),
        ("deep-learning", ("deep learning", "neural", "pytorch", "tensorflow", "backprop")),
        ("computer-vision", ("vision", "cnn", "image", "detection", "cvpr")),
        ("nlp", ("nlp", "language", "transformer", "bert", "gpt", "llm", "speech")),
        ("rl", ("reinforcement", "rl ", "mdp", "bandit", "policy")),
        ("generative", ("gan", "diffusion", "vae", "generative", "llm")),
        ("mlsys", ("mlops", "system", "serving", "deploy", "distributed")),
        ("theory", ("pac", "vc dimension", "generalization", "information theory")),
        ("causal", ("causal", "do-calculus", "identifi")),
        ("graphs", ("graph neural", "gnn", "geometric")),
        ("robotics", ("robot", "control", "slam")),
    ]
    found = [name for name, keys in rules if any(k in blob for k in keys)]
    return found or ["general"]


def heading_at(text: str, pos: int) -> str:
    last = ""
    for m in HEADING_RE.finditer(text[:pos]):
        last = m.group(1).strip()
    return last


def make_id(url: str) -> str:
    return "r-" + hashlib.sha1(url.encode()).hexdigest()[:10]


CURATED = [
    # winners — intuition and structure first
    {
        "title": "Essence of Linear Algebra",
        "url": "https://www.3blue1brown.com/topics/linear-algebra",
        "kind": "lecture-series",
        "provider": "3blue1brown",
        "level": "intro",
        "pedagogy": ["visual"],
        "branches": ["linear-algebra"],
        "evidence": "Consensus visual on-ramp; 15 short videos before any textbook.",
        "sitting": "~3 h",
        "scores": {"intuition": 5, "exercises": 3, "stack": 5, "depth": 3},
        "featured": True,
    },
    {
        "title": "MIT 18.06 Linear Algebra (Gilbert Strang)",
        "url": "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/",
        "kind": "course",
        "provider": "mit-ocw",
        "level": "intro",
        "pedagogy": ["proofs", "assignments"],
        "branches": ["linear-algebra"],
        "evidence": "Problem sets + four subspaces, least squares, SVD. The rigor pass after 3Blue1Brown.",
        "sitting": "~3 h (lecture + exercises)",
        "scores": {"intuition": 4, "exercises": 5, "stack": 3, "depth": 5},
        "featured": True,
    },
    {
        "title": "Mathematics for Machine Learning: Linear Algebra (Imperial)",
        "url": "https://www.coursera.org/learn/linear-algebra-machine-learning",
        "kind": "course",
        "provider": "coursera",
        "level": "intro",
        "pedagogy": ["assignments", "visual"],
        "branches": ["linear-algebra"],
        "evidence": "ML-shaped Python labs (PCA, PageRank). Best Coursera pairing with Strang.",
        "sitting": "~4 h (week 1)",
        "scores": {"intuition": 4, "exercises": 5, "stack": 5, "depth": 3},
        "featured": True,
    },
    {
        "title": "Mathematics for Machine Learning (book, Deisenroth et al.)",
        "url": "https://mml-book.github.io/",
        "kind": "book",
        "provider": "mml-book",
        "level": "intro",
        "pedagogy": ["proofs"],
        "branches": ["linear-algebra", "calculus", "probability"],
        "evidence": "Free desk reference that maps LA/calc/prob onto ML notation.",
        "featured": True,
    },
    {
        "title": "Essence of Calculus",
        "url": "https://www.3blue1brown.com/topics/calculus",
        "kind": "lecture-series",
        "provider": "3blue1brown",
        "level": "intro",
        "pedagogy": ["visual"],
        "branches": ["calculus"],
        "evidence": "Geometric derivatives and integrals before multivariable ML calc.",
        "sitting": "~3 h",
        "scores": {"intuition": 5, "exercises": 3, "stack": 5, "depth": 3},
        "featured": True,
    },
    {
        "title": "Mathematics for Machine Learning: Multivariate Calculus (Imperial)",
        "url": "https://www.coursera.org/learn/multivariate-calculus-machine-learning",
        "kind": "course",
        "provider": "coursera",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["calculus"],
        "evidence": "Gradients and backprop-shaped multivariable calc with notebooks.",
        "sitting": "~4 h (week 1)",
        "scores": {"intuition": 4, "exercises": 5, "stack": 5, "depth": 3},
        "featured": True,
    },
    {
        "title": "StatQuest Machine Learning playlist",
        "url": "https://www.youtube.com/@statquest",
        "kind": "lecture-series",
        "provider": "statquest",
        "level": "intro",
        "pedagogy": ["visual"],
        "branches": ["classical-ml", "probability"],
        "evidence": "Best algorithm-by-algorithm intuition before any specialization.",
        "sitting": "~1 h to start",
        "scores": {"intuition": 5, "exercises": 2, "stack": 4, "depth": 3},
        "featured": True,
    },
    {
        "title": "Probability & Statistics for Machine Learning & Data Science",
        "url": "https://www.coursera.org/learn/machine-learning-probability-and-statistics",
        "kind": "course",
        "provider": "coursera",
        "level": "intro",
        "pedagogy": ["visual", "assignments"],
        "branches": ["probability"],
        "evidence": "Serrano / DeepLearning.AI visual MLE/MAP and A/B testing in Python.",
        "sitting": "~4 h (week 1)",
        "scores": {"intuition": 4, "exercises": 4, "stack": 5, "depth": 3},
        "featured": True,
    },
    {
        "title": "Machine Learning Specialization (Andrew Ng)",
        "url": "https://www.coursera.org/specializations/machine-learning-introduction",
        "kind": "course",
        "provider": "coursera",
        "level": "intro",
        "pedagogy": ["assignments", "visual"],
        "branches": ["classical-ml"],
        "evidence": "Best structured first ML course in 2026 comparisons; Python, broad, graded labs.",
        "sitting": "~4 h (week 1)",
        "scores": {"intuition": 4, "exercises": 5, "stack": 5, "depth": 4},
        "featured": True,
    },
    {
        "title": "An Introduction to Statistical Learning (Python)",
        "url": "https://www.statlearning.com/",
        "kind": "book",
        "provider": "isl",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["classical-ml"],
        "evidence": "Exercises that force you to implement, not only watch Ng.",
        "sitting": "~3 h (one chapter + labs)",
        "scores": {"intuition": 4, "exercises": 5, "stack": 4, "depth": 4},
        "featured": True,
    },
    {
        "title": "The Elements of Statistical Learning",
        "url": "https://web.stanford.edu/~hastie/ElemStatLearn/",
        "kind": "book",
        "provider": "stanford",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["classical-ml", "theory"],
        "evidence": "SME desk book after ISL. Not a first course.",
        "featured": True,
    },
    {
        "title": "Stanford CS229 Machine Learning",
        "url": "https://cs229.stanford.edu/",
        "kind": "course",
        "provider": "stanford",
        "level": "advanced",
        "pedagogy": ["proofs", "assignments"],
        "branches": ["classical-ml", "theory"],
        "evidence": "Graduate notes after Ng + math. Requires LA, calc, probability.",
        "featured": True,
    },
    {
        "title": "Practical Deep Learning for Coders (fast.ai)",
        "url": "https://course.fast.ai/",
        "kind": "course",
        "provider": "fast.ai",
        "level": "intermediate",
        "pedagogy": ["from-scratch", "assignments"],
        "branches": ["deep-learning"],
        "evidence": "Top-down PyTorch. Wins for engineers who already code.",
        "sitting": "~3 h (lesson 1)",
        "scores": {"intuition": 5, "exercises": 5, "stack": 5, "depth": 3},
        "featured": True,
    },
    {
        "title": "Neural Networks: Zero to Hero (Karpathy)",
        "url": "https://karpathy.ai/zero-to-hero.html",
        "kind": "lecture-series",
        "provider": "karpathy",
        "level": "intermediate",
        "pedagogy": ["from-scratch"],
        "branches": ["deep-learning", "nlp", "generative"],
        "evidence": "micrograd → makemore → GPT. Best internals series in the catalog.",
        "sitting": "~3 h (one video + notebook)",
        "scores": {"intuition": 5, "exercises": 5, "stack": 5, "depth": 4},
        "featured": True,
    },
    {
        "title": "Deep Learning Specialization (Andrew Ng)",
        "url": "https://www.coursera.org/specializations/deep-learning",
        "kind": "course",
        "provider": "coursera",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["deep-learning"],
        "evidence": "Guided TensorFlow labs. Parallel to fast.ai, not a replacement.",
        "sitting": "~4 h (week 1)",
        "scores": {"intuition": 4, "exercises": 5, "stack": 4, "depth": 3},
        "featured": True,
    },
    {
        "title": "Stanford CS231n Convolutional Neural Networks",
        "url": "https://cs231n.stanford.edu/",
        "kind": "course",
        "provider": "stanford",
        "level": "intermediate",
        "pedagogy": ["assignments", "proofs"],
        "branches": ["computer-vision", "deep-learning"],
        "evidence": "Best CV theory course; assignments are the point.",
        "sitting": "~6 h (assignment 1)",
        "scores": {"intuition": 4, "exercises": 5, "stack": 4, "depth": 5},
        "featured": True,
    },
    {
        "title": "Stanford CS224N NLP with Deep Learning",
        "url": "https://web.stanford.edu/class/cs224n/",
        "kind": "course",
        "provider": "stanford",
        "level": "intermediate",
        "pedagogy": ["assignments"],
        "branches": ["nlp"],
        "evidence": "Manning. Canonical transformer-era NLP lecture course.",
        "sitting": "~4 h (assignment 1)",
        "scores": {"intuition": 4, "exercises": 5, "stack": 4, "depth": 5},
        "featured": True,
    },
    {
        "title": "Hugging Face NLP Course",
        "url": "https://huggingface.co/learn/nlp-course",
        "kind": "course",
        "provider": "huggingface",
        "level": "intermediate",
        "pedagogy": ["assignments"],
        "branches": ["nlp", "generative"],
        "evidence": "Practice rail for tokenizers, Trainer, Hub. Pairs with CS224N.",
        "sitting": "~3 h (chapter 1)",
        "scores": {"intuition": 4, "exercises": 5, "stack": 5, "depth": 3},
        "featured": True,
    },
    {
        "title": "Generative AI Engineering with LLMs",
        "url": "https://www.coursera.org/specializations/generative-ai-engineering-with-llms",
        "kind": "course",
        "provider": "coursera",
        "level": "intermediate",
        "pedagogy": ["assignments", "production"],
        "branches": ["generative", "nlp"],
        "evidence": "Employer Coursera: RAG, fine-tune, LangChain labs after Karpathy/CS224N.",
        "sitting": "~4 h (week 1)",
        "scores": {"intuition": 3, "exercises": 5, "stack": 5, "depth": 3},
        "featured": True,
    },
    {
        "title": "David Silver Reinforcement Learning course",
        "url": "https://www.deepmind.com/learning-resources/reinforcement-learning-lecture-series-2021",
        "kind": "lecture-series",
        "provider": "deepmind",
        "level": "intermediate",
        "pedagogy": ["proofs", "visual"],
        "branches": ["rl"],
        "evidence": "Standard first RL lecture series cited by CS234 and Chip Huyen.",
        "featured": True,
    },
    {
        "title": "Reinforcement Learning: An Introduction (Sutton & Barto)",
        "url": "http://incompleteideas.net/book/the-book-2nd.html",
        "kind": "book",
        "provider": "sutton-barto",
        "level": "intermediate",
        "pedagogy": ["proofs", "assignments"],
        "branches": ["rl"],
        "evidence": "The book. Read selected chapters alongside Silver.",
        "sitting": "~3 h (one chapter)",
        "scores": {"intuition": 3, "exercises": 5, "stack": 3, "depth": 5},
        "featured": True,
    },
    {
        "title": "Hugging Face Deep Reinforcement Learning Course",
        "url": "https://huggingface.co/learn/deep-rl-course/en/unit0/introduction",
        "kind": "course",
        "provider": "huggingface",
        "level": "intermediate",
        "pedagogy": ["assignments"],
        "branches": ["rl"],
        "evidence": "Fun envs (Doom, Huggy) on top of Silver/Sutton. Practice rail.",
        "sitting": "~3 h (unit 1)",
        "scores": {"intuition": 4, "exercises": 5, "stack": 5, "depth": 3},
        "featured": True,
    },
    {
        "title": "Alberta Reinforcement Learning Specialization",
        "url": "https://www.coursera.org/specializations/reinforcement-learning",
        "kind": "course",
        "provider": "coursera",
        "level": "intermediate",
        "pedagogy": ["assignments"],
        "branches": ["rl"],
        "evidence": "Structured Coursera MDPs/value functions with coding assignments.",
        "featured": True,
    },
    {
        "title": "Designing Machine Learning Systems (Chip Huyen)",
        "url": "https://huyenchip.com/mlsys/",
        "kind": "book",
        "provider": "huyenchip",
        "level": "intermediate",
        "pedagogy": ["production"],
        "branches": ["mlsys"],
        "evidence": "Best single production-systems book for ML engineers.",
        "featured": True,
    },
    {
        "title": "Pluralsight path: Machine Learning Engineering",
        "url": "https://www.pluralsight.com/paths/machine-learning-engineering",
        "kind": "path",
        "provider": "pluralsight",
        "level": "intermediate",
        "pedagogy": ["production"],
        "branches": ["mlsys"],
        "evidence": "Hours-scale serving, monitoring, Airflow. Overlay, not first explanation of SGD.",
        "featured": True,
    },
    {
        "title": "Pluralsight path: Building Deep Learning Solutions with PyTorch",
        "url": "https://www.pluralsight.com/paths/building-deep-learning-solutions-with-pytorch",
        "kind": "path",
        "provider": "pluralsight",
        "level": "intermediate",
        "pedagogy": ["assignments", "production"],
        "branches": ["deep-learning"],
        "evidence": "Short PyTorch production overlay beside fast.ai/Karpathy.",
        "featured": True,
    },
    {
        "title": "Pluralsight path: Generative AI Engineering and Architecture",
        "url": "https://www.pluralsight.com/paths/generative-ai-engineering-and-architecture",
        "kind": "path",
        "provider": "pluralsight",
        "level": "advanced",
        "pedagogy": ["production"],
        "branches": ["generative", "mlsys"],
        "evidence": "RAG/agents/LLMOps architecture after you can train a transformer.",
        "featured": True,
    },
    {
        "title": "Learning From Data (Caltech, Abu-Mostafa)",
        "url": "https://work.caltech.edu/telecourse.html",
        "kind": "course",
        "provider": "caltech",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["theory"],
        "evidence": "Clearest intro to VC/generalization without drowning in measure theory.",
        "featured": True,
    },
    {
        "title": "Pattern Recognition and Machine Learning (Bishop)",
        "url": "https://www.microsoft.com/en-us/research/uploads/prod/2006/01/Bishop-Pattern-Recognition-and-Machine-Learning-2006.pdf",
        "kind": "book",
        "provider": "microsoft-research",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["classical-ml", "probability"],
        "evidence": "Bayesian SME book. Desk reference, not week-1.",
        "featured": True,
    },
    {
        "title": "Probabilistic Machine Learning (Murphy, book 1)",
        "url": "https://probml.github.io/pml-book/book1.html",
        "kind": "book",
        "provider": "murphy",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["classical-ml", "deep-learning", "probability"],
        "evidence": "Modern replacement path for Bishop if you want 2022 coverage.",
        "featured": True,
    },
    {
        "title": "Dive into Deep Learning",
        "url": "https://d2l.ai/",
        "kind": "book",
        "provider": "d2l",
        "level": "intermediate",
        "pedagogy": ["assignments", "from-scratch"],
        "branches": ["deep-learning"],
        "evidence": "Runnable book. Strong skim/parallel next to fast.ai.",
        "featured": True,
    },
    {
        "title": "Deep Learning (Goodfellow, Bengio, Courville)",
        "url": "https://www.deeplearningbook.org/",
        "kind": "book",
        "provider": "mitpress",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["deep-learning"],
        "evidence": "Theory chapters 6–9 after you have trained a net.",
        "featured": True,
    },
    {
        "title": "Neural Networks and Deep Learning (Nielsen)",
        "url": "http://neuralnetworksanddeeplearning.com/",
        "kind": "book",
        "provider": "nielsen",
        "level": "intro",
        "pedagogy": ["from-scratch"],
        "branches": ["deep-learning"],
        "evidence": "Best written from-scratch backprop before Karpathy if you want prose.",
        "featured": True,
    },
    {
        "title": "Convex Optimization (Boyd & Vandenberghe)",
        "url": "https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf",
        "kind": "book",
        "provider": "stanford",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["optimization"],
        "evidence": "The convex opt book. SME theory rail.",
        "featured": True,
    },
    {
        "title": "Information Theory, Inference, and Learning Algorithms (MacKay)",
        "url": "https://www.inference.org.uk/mackay/itila/",
        "kind": "book",
        "provider": "mackay",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["theory", "probability"],
        "evidence": "Best single book linking info theory to learning.",
        "featured": True,
    },
    {
        "title": "Artificial Intelligence: A Modern Approach (Russell & Norvig)",
        "url": "https://aima.cs.berkeley.edu/",
        "kind": "book",
        "provider": "berkeley",
        "level": "intro",
        "pedagogy": ["proofs"],
        "branches": ["classical-ml"],
        "evidence": "Search, logic, planning. Classical AI SME, not ML-only.",
        "sitting": "~3 h (one chapter + exercises)",
        "scores": {"intuition": 3, "exercises": 5, "stack": 3, "depth": 5},
        "featured": True,
    },
    {
        "title": "Berkeley CS188 Artificial Intelligence",
        "url": "https://inst.eecs.berkeley.edu/~cs188/",
        "kind": "course",
        "provider": "berkeley",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["classical-ml", "rl"],
        "evidence": "Projects on search and MDPs. Beats dated fuzzy/swarm surveys.",
        "sitting": "~8 h (Project 1)",
        "scores": {"intuition": 4, "exercises": 5, "stack": 4, "depth": 4},
        "featured": True,
    },
    {
        "title": "Google Machine Learning Crash Course",
        "url": "https://developers.google.com/machine-learning/crash-course",
        "kind": "course",
        "provider": "google",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["classical-ml"],
        "evidence": "Short practical skim if Ng feels slow; not the SME path.",
        "featured": False,
    },
    {
        "title": "Kaggle Learn",
        "url": "https://www.kaggle.com/learn",
        "kind": "course",
        "provider": "kaggle",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["classical-ml"],
        "evidence": "Micro-certificates and datasets for stage projects.",
        "featured": False,
    },
    {
        "title": "Attention Is All You Need",
        "url": "https://arxiv.org/abs/1706.03762",
        "kind": "paper",
        "provider": "arxiv",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["nlp", "generative"],
        "evidence": "Read after Karpathy GPT lecture, not before.",
        "featured": True,
    },
    {
        "title": "nanoGPT",
        "url": "https://github.com/karpathy/nanoGPT",
        "kind": "project",
        "provider": "karpathy",
        "level": "intermediate",
        "pedagogy": ["from-scratch"],
        "branches": ["nlp", "generative"],
        "evidence": "The stage-3 project: train on a corpus you like.",
        "sitting": "~4 h (train a small GPT)",
        "scores": {"intuition": 5, "exercises": 5, "stack": 5, "depth": 4},
        "featured": True,
    },
    {
        "title": "micrograd",
        "url": "https://github.com/karpathy/micrograd",
        "kind": "project",
        "provider": "karpathy",
        "level": "intro",
        "pedagogy": ["from-scratch"],
        "branches": ["deep-learning"],
        "evidence": "Stage-2 project: autograd from scalars.",
        "sitting": "~3 h",
        "scores": {"intuition": 5, "exercises": 5, "stack": 5, "depth": 3},
        "featured": True,
    },
    {
        "title": "Full Stack Deep Learning",
        "url": "https://fullstackdeeplearning.com/",
        "kind": "course",
        "provider": "fsdl",
        "level": "intermediate",
        "pedagogy": ["production"],
        "branches": ["mlsys"],
        "evidence": "Project-centered ML systems. Parallel to Huyen.",
        "featured": True,
    },
    {
        "title": "Made With ML",
        "url": "https://madewithml.com/",
        "kind": "course",
        "provider": "madewithml",
        "level": "intermediate",
        "pedagogy": ["production", "assignments"],
        "branches": ["mlsys"],
        "evidence": "MLOps from a single repo. Practice rail for stage 5.",
        "featured": True,
    },
    {
        "title": "Spinning Up in Deep RL (OpenAI)",
        "url": "https://spinningup.openai.com/en/latest/",
        "kind": "course",
        "provider": "openai",
        "level": "intermediate",
        "pedagogy": ["from-scratch", "assignments"],
        "branches": ["rl"],
        "evidence": "Implementations of key deep RL algorithms. After Silver.",
        "featured": True,
    },
    {
        "title": "Colah's blog (Understanding LSTM Networks, etc.)",
        "url": "https://colah.github.io/",
        "kind": "article",
        "provider": "colah",
        "level": "intermediate",
        "pedagogy": ["visual"],
        "branches": ["deep-learning", "nlp"],
        "evidence": "Best written intuition for LSTMs and groups; skim rail.",
        "featured": True,
    },
    {
        "title": "Distill.pub",
        "url": "https://distill.pub/",
        "kind": "article",
        "provider": "distill",
        "level": "intermediate",
        "pedagogy": ["visual"],
        "branches": ["deep-learning"],
        "evidence": "Interactive visual papers. Skim gems (feature viz, attention).",
        "featured": True,
    },
    {
        "title": "Lilian Weng's blog",
        "url": "https://lilianweng.github.io/",
        "kind": "article",
        "provider": "lilianweng",
        "level": "advanced",
        "pedagogy": ["visual"],
        "branches": ["generative", "rl", "nlp"],
        "evidence": "Best long-form surveys (transformers, diffusion, agents).",
        "featured": True,
    },
    {
        "title": "NYU Deep Learning (Tandon / LeCun)",
        "url": "https://atcold.github.io/NYU-DLSP21/",
        "kind": "course",
        "provider": "nyu",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["deep-learning"],
        "evidence": "Alternate DL theory series. Skim if CS231n is the CV pick.",
        "featured": False,
    },
    {
        "title": "Stanford CS234 Reinforcement Learning",
        "url": "https://web.stanford.edu/class/cs234/",
        "kind": "course",
        "provider": "stanford",
        "level": "advanced",
        "pedagogy": ["assignments"],
        "branches": ["rl"],
        "evidence": "Graduate RL after Silver. Assignments include deep RL.",
        "featured": True,
    },
    {
        "title": "Berkeley CS285 Deep Reinforcement Learning",
        "url": "https://rail.eecs.berkeley.edu/deeprlcourse/",
        "kind": "course",
        "provider": "berkeley",
        "level": "advanced",
        "pedagogy": ["assignments"],
        "branches": ["rl"],
        "evidence": "Deep RL SME course. After CS234/Silver.",
        "featured": True,
    },
    {
        "title": "Probabilistic Graphical Models (Koller, Coursera)",
        "url": "https://www.coursera.org/specializations/probabilistic-graphical-models",
        "kind": "course",
        "provider": "coursera",
        "level": "advanced",
        "pedagogy": ["assignments", "proofs"],
        "branches": ["probability", "theory"],
        "evidence": "Canonical PGM specialization for the branch year.",
        "featured": True,
    },
    {
        "title": "Causal Inference for the Brave and True",
        "url": "https://matheusfacure.github.io/python-causality-handbook/landing-page.html",
        "kind": "book",
        "provider": "facure",
        "level": "intermediate",
        "pedagogy": ["assignments"],
        "branches": ["causal"],
        "evidence": "Intuitive Python causality handbook. Better on-ramp than Pearl first.",
        "featured": True,
    },
    {
        "title": "The Book of Why (Pearl & Mackenzie)",
        "url": "http://bayes.cs.ucla.edu/WHY/",
        "kind": "book",
        "provider": "pearl",
        "level": "intro",
        "pedagogy": ["visual"],
        "branches": ["causal"],
        "evidence": "Narrative causal ladder. Pair with Facure for exercises.",
        "featured": True,
    },
    {
        "title": "MIT 6.S191 Introduction to Deep Learning",
        "url": "https://introtodeeplearning.com/",
        "kind": "course",
        "provider": "mit",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["deep-learning"],
        "evidence": "Short MIT intro. Skim if already doing fast.ai.",
        "featured": False,
    },
    {
        "title": "Understanding Machine Learning (Shalev-Shwartz & Ben-David)",
        "url": "https://www.cs.huji.ac.il/~shais/UnderstandingMachineLearning/",
        "kind": "book",
        "provider": "huji",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["theory"],
        "evidence": "Clean PAC-learning textbook. Stage-6 theory.",
        "featured": True,
    },
    {
        "title": "A Course in Machine Learning (Daumé)",
        "url": "http://ciml.info/",
        "kind": "book",
        "provider": "ciml",
        "level": "intermediate",
        "pedagogy": ["proofs"],
        "branches": ["classical-ml", "theory"],
        "evidence": "Free CIML. Good middle between Ng and CS229.",
        "featured": True,
    },
    {
        "title": "Hands-On Machine Learning (Géron)",
        "url": "https://www.oreilly.com/library/view/hands-on-machine-learning/9781098122461/",
        "kind": "book",
        "provider": "oreilly",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["classical-ml", "deep-learning"],
        "evidence": "Engineer-friendly sklearn/TF/Keras. Parallel practice book.",
        "featured": True,
    },
    {
        "title": "Mathematics for Machine Learning: PCA (Imperial)",
        "url": "https://www.coursera.org/learn/pca-machine-learning",
        "kind": "course",
        "provider": "coursera",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["linear-algebra", "classical-ml"],
        "evidence": "Third Imperial course. Harder; worth it after LA+calc.",
        "featured": True,
    },
    {
        "title": "Khan Academy Linear Algebra",
        "url": "https://www.khanacademy.org/math/linear-algebra",
        "kind": "course",
        "provider": "khan",
        "level": "intro",
        "pedagogy": ["visual"],
        "branches": ["linear-algebra"],
        "evidence": "Remedial if 3Blue1Brown is still too fast. Not SME depth.",
        "featured": False,
    },
    {
        "title": "MIT 18.06SC Linear Algebra (recitations)",
        "url": "https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/",
        "kind": "course",
        "provider": "mit-ocw",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["linear-algebra"],
        "evidence": "Scholar recitations if Strang OCW 2010 is the lecture pick.",
        "featured": False,
    },
    {
        "title": "Matrix Methods in Data Analysis (Strang 18.065)",
        "url": "https://ocw.mit.edu/courses/18-065-matrix-methods-in-data-analysis-signal-processing-and-machine-learning-spring-2018/",
        "kind": "course",
        "provider": "mit-ocw",
        "level": "intermediate",
        "pedagogy": ["proofs"],
        "branches": ["linear-algebra", "classical-ml"],
        "evidence": "Strang's ML-flavored sequel. After 18.06.",
        "featured": True,
    },
    {
        "title": "Boyd EE104 / Introduction to Applied Linear Algebra",
        "url": "https://www.vandenberghe.ucla.edu/ee133a.html",
        "kind": "course",
        "provider": "ucla",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["linear-algebra"],
        "evidence": "Least squares first. Alternate rigor path to Strang.",
        "featured": False,
    },
    {
        "title": "Introduction to Applied Linear Algebra (Boyd & Vandenberghe book)",
        "url": "https://web.stanford.edu/~boyd/vmls/",
        "kind": "book",
        "provider": "stanford",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["linear-algebra"],
        "evidence": "Vectors, least squares, Julia/Python. Free.",
        "featured": True,
    },
    {
        "title": "Blizstein Stat 110",
        "url": "https://stat110.harvard.edu/",
        "kind": "course",
        "provider": "harvard",
        "level": "intermediate",
        "pedagogy": ["proofs", "assignments"],
        "branches": ["probability"],
        "evidence": "Best full probability course if Serrano is too light.",
        "featured": True,
    },
    {
        "title": "MIT 6.041 Probabilistic Systems Analysis",
        "url": "https://ocw.mit.edu/courses/6-041-probabilistic-systems-analysis-and-applied-probability-fall-2010/",
        "kind": "course",
        "provider": "mit-ocw",
        "level": "intermediate",
        "pedagogy": ["proofs", "assignments"],
        "branches": ["probability"],
        "evidence": "Alternate to Stat 110. Engineering probability.",
        "featured": False,
    },
    {
        "title": "Think Bayes",
        "url": "https://allendowney.github.io/ThinkBayes2/",
        "kind": "book",
        "provider": "downey",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["probability"],
        "evidence": "Computational Bayes in Python. Fun parallel to Serrano.",
        "featured": True,
    },
    {
        "title": "Probabilistic Programming and Bayesian Methods for Hackers",
        "url": "https://camdavidsonpilon.github.io/Probabilistic-Programming-and-Bayesian-Methods-for-Hackers/",
        "kind": "book",
        "provider": "davidson-pilon",
        "level": "intermediate",
        "pedagogy": ["assignments"],
        "branches": ["probability"],
        "evidence": "PyMC-flavored. After Think Bayes.",
        "featured": True,
    },
    {
        "title": "Gaussian Processes for Machine Learning",
        "url": "https://www.gaussianprocess.org/gpml/",
        "kind": "book",
        "provider": "gpml",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["classical-ml", "probability"],
        "evidence": "The GP book. Branch depth, not spine.",
        "featured": True,
    },
    {
        "title": "Stanford CS221 Artificial Intelligence",
        "url": "https://stanford-cs221.github.io/",
        "kind": "course",
        "provider": "stanford",
        "level": "intermediate",
        "pedagogy": ["assignments"],
        "branches": ["classical-ml"],
        "evidence": "Search, MDPs, Bayes nets. Graduate CS188 equivalent.",
        "featured": True,
    },
    {
        "title": "DeepLearning.AI Machine Learning Specialization (site)",
        "url": "https://www.deeplearning.ai/courses/machine-learning-specialization/",
        "kind": "course",
        "provider": "deeplearning.ai",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["classical-ml"],
        "evidence": "Canonical landing page for Ng ML spec.",
        "featured": False,
    },
    {
        "title": "Deep Learning Specialization (DeepLearning.AI site)",
        "url": "https://www.deeplearning.ai/courses/deep-learning-specialization/",
        "kind": "course",
        "provider": "deeplearning.ai",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["deep-learning"],
        "evidence": "Canonical landing page for DLS.",
        "featured": False,
    },
    {
        "title": "MLOps Specialization (DeepLearning.AI)",
        "url": "https://www.coursera.org/specializations/machine-learning-engineering-for-production-mlops",
        "kind": "course",
        "provider": "coursera",
        "level": "intermediate",
        "pedagogy": ["production", "assignments"],
        "branches": ["mlsys"],
        "evidence": "Coursera MLOps. Parallel to Huyen + Pluralsight.",
        "featured": True,
    },
    {
        "title": "Hugging Face Agents course",
        "url": "https://huggingface.co/learn/agents-course",
        "kind": "course",
        "provider": "huggingface",
        "level": "intermediate",
        "pedagogy": ["assignments"],
        "branches": ["generative", "nlp"],
        "evidence": "Tool-using agents after LLM practice.",
        "sitting": "~3 h (unit 1)",
        "scores": {"intuition": 4, "exercises": 5, "stack": 5, "depth": 3},
        "featured": True,
    },
    {
        "title": "Hugging Face Deep RL (hub)",
        "url": "https://huggingface.co/learn/deep-rl-course",
        "kind": "course",
        "provider": "huggingface",
        "level": "intermediate",
        "pedagogy": ["assignments"],
        "branches": ["rl"],
        "evidence": "Canonical HF RL course root.",
        "featured": False,
    },
    {
        "title": "fast.ai Practical Deep Learning (forums)",
        "url": "https://forums.fast.ai/",
        "kind": "article",
        "provider": "fast.ai",
        "level": "intermediate",
        "pedagogy": ["assignments"],
        "branches": ["deep-learning"],
        "evidence": "Where fast.ai actually gets unstuck. Not a course.",
        "featured": False,
    },
    {
        "title": "fast.ai book (Practical Deep Learning)",
        "url": "https://github.com/fastai/fastbook",
        "kind": "book",
        "provider": "fast.ai",
        "level": "intermediate",
        "pedagogy": ["assignments"],
        "branches": ["deep-learning"],
        "evidence": "Notebooks that accompany course.fast.ai.",
        "sitting": "~3 h (one notebook)",
        "scores": {"intuition": 4, "exercises": 5, "stack": 5, "depth": 3},
        "featured": True,
    },
    {
        "title": "PyTorch official tutorials",
        "url": "https://pytorch.org/tutorials/",
        "kind": "course",
        "provider": "pytorch",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["deep-learning"],
        "evidence": "Canonical API tutorials. Parallel to Pluralsight PyTorch.",
        "featured": True,
    },
    {
        "title": "scikit-learn user guide",
        "url": "https://scikit-learn.org/stable/user_guide.html",
        "kind": "article",
        "provider": "sklearn",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["classical-ml"],
        "evidence": "The library you will actually use in stage 1 projects.",
        "featured": True,
    },
    {
        "title": "Gymnasium documentation",
        "url": "https://gymnasium.farama.org/",
        "kind": "article",
        "provider": "farama",
        "level": "intermediate",
        "pedagogy": ["assignments"],
        "branches": ["rl"],
        "evidence": "Env API for RL projects.",
        "featured": False,
    },
    {
        "title": "Papers With Code — methods",
        "url": "https://paperswithcode.com/methods",
        "kind": "article",
        "provider": "paperswithcode",
        "level": "advanced",
        "pedagogy": ["production"],
        "branches": ["deep-learning"],
        "evidence": "SOTA tracker. Skim when picking a paper to reproduce.",
        "featured": False,
    },
    {
        "title": "The Hundred-Page Machine Learning Book",
        "url": "http://themlbook.com/",
        "kind": "book",
        "provider": "burkov",
        "level": "intro",
        "pedagogy": ["visual"],
        "branches": ["classical-ml"],
        "evidence": "Dense overview. Skim, then ISL.",
        "featured": False,
    },
    {
        "title": "Grokking Deep Learning (Trask)",
        "url": "https://www.manning.com/books/grokking-deep-learning",
        "kind": "book",
        "provider": "manning",
        "level": "intro",
        "pedagogy": ["from-scratch"],
        "branches": ["deep-learning"],
        "evidence": "NumPy-only nets. Alternate to Nielsen.",
        "featured": False,
    },
    {
        "title": "Deep Learning with Python (Chollet)",
        "url": "https://www.manning.com/books/deep-learning-with-python-second-edition",
        "kind": "book",
        "provider": "manning",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["deep-learning"],
        "evidence": "Keras-first. Parallel if you take DLS (TensorFlow).",
        "featured": False,
    },
    {
        "title": "Speech and Language Processing (Jurafsky & Martin)",
        "url": "https://web.stanford.edu/~jurafsky/slp3/",
        "kind": "book",
        "provider": "stanford",
        "level": "intermediate",
        "pedagogy": ["proofs"],
        "branches": ["nlp"],
        "evidence": "NLP desk book beside CS224N.",
        "featured": True,
    },
    {
        "title": "Foundations of Statistical Natural Language Processing (Manning & Schütze)",
        "url": "https://nlp.stanford.edu/fsnlp/",
        "kind": "book",
        "provider": "stanford",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["nlp"],
        "evidence": "Pre-neural NLP SME. Historical + still useful for IR stats.",
        "featured": False,
    },
    {
        "title": "Introduction to Information Retrieval",
        "url": "https://nlp.stanford.edu/IR-book/",
        "kind": "book",
        "provider": "stanford",
        "level": "intermediate",
        "pedagogy": ["proofs"],
        "branches": ["nlp"],
        "evidence": "IR before RAG. Understand BM25 before embeddings.",
        "sitting": "~3 h (one chapter)",
        "scores": {"intuition": 3, "exercises": 4, "stack": 3, "depth": 5},
        "featured": True,
    },
    {
        "title": "NLTK book",
        "url": "https://www.nltk.org/book/",
        "kind": "book",
        "provider": "nltk",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["nlp"],
        "evidence": "Classic NLP lab book. Skim in 2026; still good for linguistics labs.",
        "featured": False,
    },
    {
        "title": "Annotated Transformer (Harvard NLP)",
        "url": "https://nlp.seas.harvard.edu/annotated-transformer/",
        "kind": "article",
        "provider": "harvard",
        "level": "intermediate",
        "pedagogy": ["from-scratch"],
        "branches": ["nlp"],
        "evidence": "Line-by-line Attention Is All You Need. After Karpathy GPT.",
        "featured": True,
    },
    {
        "title": "The Illustrated Transformer (Alammar)",
        "url": "https://jalammar.github.io/illustrated-transformer/",
        "kind": "article",
        "provider": "jalammar",
        "level": "intro",
        "pedagogy": ["visual"],
        "branches": ["nlp"],
        "evidence": "Best single visual for attention. Do before the paper.",
        "sitting": "~1 h",
        "scores": {"intuition": 5, "exercises": 1, "stack": 4, "depth": 3},
        "featured": True,
    },
    {
        "title": "Berkeley CS182 / Deep Learning (or equivalent notes)",
        "url": "https://cs182sp21.github.io/",
        "kind": "course",
        "provider": "berkeley",
        "level": "intermediate",
        "pedagogy": ["assignments"],
        "branches": ["deep-learning"],
        "evidence": "Alternate university DL. Skim vs CS231n.",
        "featured": False,
    },
    {
        "title": "Oxford Deep NLP (2017, still useful lectures)",
        "url": "https://github.com/oxford-cs-deepnlp-2017/lectures",
        "kind": "lecture-series",
        "provider": "oxford",
        "level": "intermediate",
        "pedagogy": ["proofs"],
        "branches": ["nlp"],
        "evidence": "Historical. Skim; CS224N is the live path.",
        "featured": False,
    },
    {
        "title": "CMU 11-785 Introduction to Deep Learning",
        "url": "https://deeplearning.cs.cmu.edu/",
        "kind": "course",
        "provider": "cmu",
        "level": "advanced",
        "pedagogy": ["assignments"],
        "branches": ["deep-learning"],
        "evidence": "Heavy recitation DL. SME alternate to fast.ai+Karpathy.",
        "featured": True,
    },
    {
        "title": "CMU 10-701 / 10-715 Machine Learning",
        "url": "https://www.cs.cmu.edu/~nihars/teaching/10715-fa20/",
        "kind": "course",
        "provider": "cmu",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["classical-ml", "theory"],
        "evidence": "CMU theory-flavored ML. Stage 6 alternate to CS229.",
        "featured": False,
    },
    {
        "title": "UCL COMPM050 / DeepMind x UCL RL lectures (Silver 2015)",
        "url": "https://www.youtube.com/playlist?list=PLqYmG7hTraZDM-OYHWgPebj2MfCFzFObQ",
        "kind": "lecture-series",
        "provider": "youtube",
        "level": "intermediate",
        "pedagogy": ["proofs"],
        "branches": ["rl"],
        "evidence": "Widely mirrored Silver 2015 playlist.",
        "sitting": "~2 h (lecture 1)",
        "scores": {"intuition": 4, "exercises": 3, "stack": 3, "depth": 5},
        "featured": True,
    },
    {
        "title": "NPTEL: Mathematical Foundations for Machine Learning (IISc)",
        "url": "https://www.youtube.com/playlist?list=PLgMDNELGJ1CYPJS6m_ygxb4KtHYxh1HjR",
        "kind": "lecture-series",
        "provider": "nptel",
        "level": "intro",
        "pedagogy": ["proofs"],
        "branches": ["classical-ml"],
        "evidence": "Long IISc survey. Listed; Imperial+Ng rank higher on intuition.",
        "featured": False,
    },
    {
        "title": "NPTEL: Foundations of Deep Learning (IISc)",
        "url": "https://www.youtube.com/playlist?list=PLgMDNELGJ1CaeIiQMBOE0NONdZxS2eD2H",
        "kind": "lecture-series",
        "provider": "nptel",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["deep-learning"],
        "evidence": "IISc DL survey with labs. Ranked below fast.ai + Karpathy for a coder.",
        "featured": False,
    },
    {
        "title": "NPTEL: Mathematical Foundations of Machine Learning (IISc)",
        "url": "https://www.youtube.com/playlist?list=PLgMDNELGJ1Cay-Q9Cn8KcpUcC58NDWuiu",
        "kind": "lecture-series",
        "provider": "nptel",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["theory", "classical-ml"],
        "evidence": "Rigor pass candidate vs Caltech LFD / CS229. Compare, don't default.",
        "featured": False,
    },
    {
        "title": "NPTEL: Fundamentals of Generative AI and LLMs (IISc)",
        "url": "https://www.youtube.com/playlist?list=PLgMDNELGJ1Ca_DduFvH6qfI1eapL48xOr",
        "kind": "lecture-series",
        "provider": "nptel",
        "level": "intermediate",
        "pedagogy": ["assignments"],
        "branches": ["generative"],
        "evidence": "Long genAI survey. Karpathy + CS224N + HF rank higher.",
        "featured": False,
    },
    {
        "title": "NPTEL: Linear Algebra Through Geometry (IISc)",
        "url": "https://www.youtube.com/playlist?list=PLgMDNELGJ1CaTrBVbwaHoHYlTbyeV-q5c",
        "kind": "lecture-series",
        "provider": "nptel",
        "level": "intro",
        "pedagogy": ["proofs"],
        "branches": ["linear-algebra"],
        "evidence": "Geometry-flavored LA. 3Blue1Brown + Strang still win intuition+exercises.",
        "featured": False,
    },
    {
        "title": "NPTEL: Machine Learning for Core Engineering Disciplines",
        "url": "https://www.youtube.com/playlist?list=PLgMDNELGJ1CYxkPswXfE1Fk9rzBeG4hFv",
        "kind": "lecture-series",
        "provider": "nptel",
        "level": "intro",
        "pedagogy": ["assignments"],
        "branches": ["classical-ml", "deep-learning"],
        "evidence": "Applied ML+TF. Ng spec + fast.ai cover the same ground more tightly.",
        "featured": False,
    },
    {
        "title": "NPTEL: Artificial Intelligence Concepts and Techniques",
        "url": "https://www.youtube.com/playlist?list=PLgMDNELGJ1CZSGn478v1uKbzxJzKWZ7zs",
        "kind": "lecture-series",
        "provider": "nptel",
        "level": "intro",
        "pedagogy": ["proofs"],
        "branches": ["classical-ml"],
        "evidence": "Includes dated fuzzy/swarm. CS188/AIMA is the classical-AI pick.",
        "featured": False,
    },
    {
        "title": "NPTEL: Stochastic Approximation",
        "url": "https://www.youtube.com/playlist?list=PLgMDNELGJ1CaCugN_GPrVQUkGUCAKZF2s",
        "kind": "lecture-series",
        "provider": "nptel",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["rl", "optimization"],
        "evidence": "Rare depth on SA/Q-learning theory. Wins a SME-later node.",
        "featured": True,
    },
    {
        "title": "NPTEL: Computer System Optimizations for ML",
        "url": "https://www.youtube.com/playlist?list=PLgMDNELGJ1CY3kDa1Y3hJI3h4TOoO3Dsq",
        "kind": "lecture-series",
        "provider": "nptel",
        "level": "advanced",
        "pedagogy": ["production"],
        "branches": ["mlsys"],
        "evidence": "Hardware/GNN accel. After Huyen; unique vs Coursera MLOps.",
        "featured": True,
    },
    {
        "title": "NPTEL: Concentration inequalities",
        "url": "https://www.youtube.com/playlist?list=PLgMDNELGJ1CZp3yTR9r5utkisB8i92_dZ",
        "kind": "lecture-series",
        "provider": "nptel",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["theory"],
        "evidence": "Short and focused. Strong stage-6 theory candidate.",
        "featured": True,
    },
    {
        "title": "NPTEL: Information Theory (IISc, 68 lectures)",
        "url": "https://www.youtube.com/playlist?list=PLgMDNELGJ1CYS-8dlMGPIaowVfeda4nUj",
        "kind": "lecture-series",
        "provider": "nptel",
        "level": "advanced",
        "pedagogy": ["proofs"],
        "branches": ["theory"],
        "evidence": "Full IT course. MacKay book may teach faster; this is the lecture option.",
        "featured": False,
    },
]


CURATED.extend(CURATED_EXTRA)
STATIONS = GRAPH_STATIONS


def harvest_links() -> list[tuple[str, str, str, str]]:
    rows = []
    for path in sorted(HARVEST.glob("*.md")):
        text = path.read_text(errors="replace")
        for m in LINK_RE.finditer(text):
            title, url = m.group(1).strip(), m.group(2).strip()
            if not allowed(url):
                continue
            try:
                nurl = normalize(url)
            except Exception:
                continue
            if not nurl.startswith("http"):
                continue
            rows.append((nurl, title[:180], path.name, heading_at(text, m.start())))
    return rows


def attach_outlines(resources: list[dict], outlines: dict) -> list[dict]:
    """Attach parts[]; upsert lesson rows for parts that have unique URLs."""
    by_url = {r["url"]: r for r in resources}
    keyed = {}
    for k, v in outlines.items():
        try:
            keyed[normalize(k)] = v
        except Exception:
            continue
    extra = []
    for rec in resources:
        spec = keyed.get(rec["url"])
        if not spec:
            continue
        parts = []
        for item in spec:
            slug = item["slug"]
            raw_url = item.get("url")
            if raw_url:
                nurl = normalize(raw_url)
                child = by_url.get(nurl)
                if child is None:
                    child = {
                        "id": make_id(nurl),
                        "title": item["title"],
                        "url": nurl,
                        "kind": "lesson",
                        "provider": rec.get("provider") or "",
                        "access": rec.get("access") or "free",
                        "level": rec.get("level") or "unspecified",
                        "pedagogy": rec.get("pedagogy") or [],
                        "branches": rec.get("branches") or [],
                        "evidence": f"Lesson of {rec['title']}",
                        "featured": False,
                        "source": "outline",
                        "parent_id": rec["id"],
                    }
                    extra.append(child)
                    by_url[nurl] = child
                else:
                    child["parent_id"] = rec["id"]
                parts.append({"id": child["id"], "title": item["title"], "url": nurl})
            else:
                parts.append({"id": f"{rec['id']}:{slug}", "title": item["title"], "url": None})
        rec["parts"] = parts
    return resources + extra


def harvest_hashes() -> dict:
    out = {}
    for path in sorted(HARVEST.glob("*.md")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        out[path.name] = digest
    return out


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    by_url: dict[str, dict] = {}

    def upsert(item: dict, source: str) -> None:
        url = normalize(item["url"])
        existing = by_url.get(url)
        rec = {
            "id": make_id(url),
            "title": item["title"].strip()[:180],
            "url": url,
            "kind": item.get("kind") or kind_of(url, item["title"]),
            "provider": item.get("provider") or provider_of(url),
            "access": item.get("access") or access_of(item.get("provider") or provider_of(url)),
            "level": item.get("level") or "unspecified",
            "pedagogy": item.get("pedagogy") or [],
            "branches": item.get("branches") or branches_of(item["title"], url, ""),
            "evidence": item.get("evidence") or f"Harvested from {source}",
            "featured": bool(item.get("featured")),
            "source": source,
        }
        if item.get("sitting"):
            rec["sitting"] = item["sitting"]
        if item.get("sitting_min") is not None:
            rec["sitting_min"] = item["sitting_min"]
        if item.get("audio_url"):
            rec["audio_url"] = item["audio_url"]
        if item.get("purpose"):
            rec["purpose"] = item["purpose"]
        if item.get("rank") is not None:
            rec["rank"] = item["rank"]
        if item.get("scores"):
            rec["scores"] = item["scores"]
        if existing:
            if rec["featured"]:
                existing.update({k: rec[k] for k in rec if k != "id"})
                existing["id"] = rec["id"]
            elif existing["title"].startswith("http") or len(rec["title"]) > len(existing["title"]):
                existing["title"] = rec["title"]
            return
        by_url[url] = rec

    for item in CURATED:
        upsert(item, "curated")

    for item in EPISODES:
        upsert(to_resource(item), "commute")

    for url, title, fname, heading in harvest_links():
        upsert(
            {
                "title": title or url,
                "url": url,
                "branches": branches_of(title, url, heading),
            },
            fname,
        )

    resources = sorted(by_url.values(), key=lambda r: (not r["featured"], r["title"].lower()))
    from outlines import OUTLINES

    resources = attach_outlines(resources, OUTLINES)
    resources = sorted(resources, key=lambda r: (not r.get("featured"), r["title"].lower()))
    url_to_id = {r["url"]: r["id"] for r in resources}

    def resolve(urls: list[str]) -> list[str]:
        ids = []
        for u in urls:
            try:
                nu = normalize(u)
            except Exception:
                continue
            rid = url_to_id.get(nu)
            if rid:
                ids.append(rid)
        return ids

    nodes = []
    for st in STATIONS:
        nodes.append(
            {
                "id": st["id"],
                "title": st["title"],
                "stage": st["stage"],
                "rail": st["rail"],
                "branch": st["branch"],
                "prereqs": st["prereqs"],
                "why": st["why"],
                "do": resolve(st["do"]),
                "parallel": resolve(st["parallel"]),
                "skim": resolve(st["skim"]),
                "project": resolve(st["project"]),
            }
        )

    known_ids = set(url_to_id.values())
    seed_nodes = nodes  # after resolve, before overlay
    (DATA / "graph.seed.json").write_text(json.dumps({"nodes": seed_nodes}, indent=2) + "\n")
    placements = filter_placements(load_assignments()["placements"], known_ids)
    nodes = apply_placements(seed_nodes, placements)

    compiled_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip() or "uncommitted"
    except Exception:
        git_sha = "uncommitted"
    graph = {
        "title": "AI/ML SME Atlas",
        "hours_per_week": 15,
        "compiled_at": compiled_at,
        "ranking_pass": "2026-09-12",
        "ranking_rule": "intuition, exercises, modern stack, SME leftover — not institution",
        "stages": [
            {"id": 0, "name": "Sight and ship", "months": "1.5–2"},
            {"id": 1, "name": "Classical ML + AI", "months": "2–2.5"},
            {"id": 2, "name": "Deep learning both ways", "months": "2.5–3"},
            {"id": 3, "name": "Language", "months": "2–2.5"},
            {"id": 4, "name": "Decisions", "months": "2"},
            {"id": 5, "name": "Systems", "months": "1.5"},
            {"id": 6, "name": "Theory desk", "months": "year 2"},
            {"id": 7, "name": "Branches", "months": "year 2–3"},
        ],
        "nodes": nodes,
    }

    commute_rows = playlist([r for r in resources if r.get("audio_url")], nodes)
    write_feed(commute_rows, DATA / "feed.xml")

    (DATA / "resources.json").write_text(json.dumps(resources, indent=2) + "\n")
    (DATA / "graph.json").write_text(json.dumps(graph, indent=2) + "\n")
    hashes = harvest_hashes()
    (DATA / "harvest.hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
    meta = {
        "compiled_at": compiled_at,
        "git_sha": git_sha,
        "ranking_pass": "2026-09-12",
        "resource_count": len(resources),
        "featured_count": sum(1 for r in resources if r.get("featured")),
        "station_count": len(nodes),
        "do_rail_human_gate": True,
        "harvest_files": len(hashes),
        "commute_count": len(commute_rows),
        "github_repo": "sardul3/ai-sme-map",
        "harvest_lists": harvest_files_from_disk(),
    }
    (DATA / "catalog_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    progress_path = DATA / "progress.json"
    if not progress_path.exists():
        progress_path.write_text(json.dumps({"schema_version": 1}, indent=2) + "\n")
    inbox_path = DATA / "inbox.json"
    if not inbox_path.exists():
        inbox_path.write_text(
            json.dumps(
                {
                    "fetched_at": None,
                    "human_gate": True,
                    "harvested": [],
                    "commute_candidates": [],
                },
                indent=2,
            )
            + "\n"
        )

    print(f"resources {len(resources)}")
    print(f"featured {sum(1 for r in resources if r['featured'])}")
    print(f"nodes {len(nodes)}")
    if len(resources) < 500:
        raise SystemExit(f"catalog too small: {len(resources)}")


if __name__ == "__main__":
    main()
