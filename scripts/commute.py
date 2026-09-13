"""Human-gated commute playlist: eyes-off audio ranked by purpose, not lesson stations."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape

AUDIO_SUFFIXES = (".mp3", ".m4a", ".aac", ".ogg", ".oga", ".opus")
COMMUTE_KINDS = {"podcast", "audio"}

PURPOSES = {
    "learn": {
        "title": "Learn",
        "why": "A concept you can finish on a walk. Teaching shows, not chat.",
        "rail": "theory",
    },
    "interview": {
        "title": "Hear people",
        "why": "Researchers and practitioners, in their own voice.",
        "rail": "theory",
    },
    "apply": {
        "title": "Ship",
        "why": "How teams put models, agents, and infra into production.",
        "rail": "practice",
    },
    "pulse": {
        "title": "Stay current",
        "why": "What moved this year — indexes, recsys, agent news.",
        "rail": "practice",
    },
}
PURPOSE_ORDER = ("learn", "interview", "apply", "pulse")

# Human-gated. Original enclosures only. Do not harvest-invent rows.
LEARN_RAW = [
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
    {
        "title": "MLG 008 Math for Machine Learning",
        "url": "https://ocdevel.com/mlg/8",
        "audio_url": "https://traffic.libsyn.com/secure/machinelearningguide/mlg-8.20250516.mp3",
        "station_id": "s-la-see",
        "sitting_min": 28,
        "provider": "ocdevel",
        "branches": ["linear-algebra"],
        "evidence": "LA/calc/prob as forest, not a textbook. Machine Learning Guide audio course.",
    },
    {
        "title": "MLG 004 Algorithms — Intuition",
        "url": "https://ocdevel.com/mlg/4",
        "audio_url": "https://traffic.libsyn.com/secure/machinelearningguide/mlg-4.20250516.mp3",
        "station_id": "s-ml-intuit",
        "sitting_min": 23,
        "provider": "ocdevel",
        "branches": ["classical-ml"],
        "evidence": "What an algorithm even is before sklearn. ML Guide, Apple 4.9 teaching series.",
    },
    {
        "title": "MLG 005 Linear Regression",
        "url": "https://ocdevel.com/mlg/5",
        "audio_url": "https://traffic.libsyn.com/secure/machinelearningguide/mlg-5.20260128.mp3",
        "station_id": "s-ml-do",
        "sitting_min": 35,
        "provider": "ocdevel",
        "branches": ["classical-ml"],
        "evidence": "First supervised sitting you can hear, then run. ML Guide syllabus.",
    },
    {
        "title": "MLG 007 Logistic Regression",
        "url": "https://ocdevel.com/mlg/7",
        "audio_url": "https://traffic.libsyn.com/secure/machinelearningguide/mlg-7.20250516.mp3",
        "station_id": "s-ml-do",
        "sitting_min": 35,
        "provider": "ocdevel",
        "branches": ["classical-ml"],
        "evidence": "Classification after linear regression. Same voice, next lesson.",
    },
    {
        "title": "MLG 015 Performance",
        "url": "https://ocdevel.com/mlg/15",
        "audio_url": "https://traffic.libsyn.com/secure/machinelearningguide/mlg.015.20250126.mp3",
        "station_id": "s-eval",
        "sitting_min": 42,
        "provider": "ocdevel",
        "branches": ["eval"],
        "evidence": "Bias, variance, metrics — why a number can lie. ML Guide.",
    },
    {
        "title": "MLG 025 Convolutional Neural Networks",
        "url": "https://ocdevel.com/mlg/25",
        "audio_url": "https://traffic.libsyn.com/secure/machinelearningguide/mlg.025.20250126.mp3",
        "station_id": "s-cv",
        "sitting_min": 44,
        "provider": "ocdevel",
        "branches": ["computer-vision"],
        "evidence": "Convnets as the vision sitting. ML Guide deep-models arc.",
    },
    {
        "title": "MLG 033 Transformers",
        "url": "https://ocdevel.com/mlg/33",
        "audio_url": "https://traffic.libsyn.com/secure/machinelearningguide/mlg-33.20250414.mp3",
        "station_id": "s-attn",
        "sitting_min": 43,
        "provider": "ocdevel",
        "branches": ["nlp"],
        "evidence": "Attention → transformers without a paper slog. 2025 ML Guide refresh.",
    },
    {
        "title": "MLG 029 Reinforcement Learning Intro",
        "url": "https://ocdevel.com/mlg/29",
        "audio_url": "https://traffic.libsyn.com/secure/machinelearningguide/mlg.029.20250126.mp3",
        "station_id": "s-rl",
        "sitting_min": 43,
        "provider": "ocdevel",
        "branches": ["rl"],
        "evidence": "Decisions, not labels. The RL on-ramp in the ML Guide syllabus.",
    },
    {
        "title": "MLG 032 Cartesian Similarity Metrics",
        "url": "https://ocdevel.com/mlg/32",
        "audio_url": "https://traffic.libsyn.com/secure/machinelearningguide/mlg.032.20250126.mp3",
        "station_id": "s-ir",
        "sitting_min": 41,
        "provider": "ocdevel",
        "branches": ["nlp"],
        "evidence": "Distance in vector space before you wrap a vector DB.",
    },
    {
        "title": "MLG 035 Large Language Models 2",
        "url": "https://ocdevel.com/mlg/35",
        "audio_url": "https://traffic.libsyn.com/secure/machinelearningguide/mlg-35.20250507.mp3",
        "station_id": "s-llm-tools",
        "sitting_min": 45,
        "provider": "ocdevel",
        "branches": ["nlp"],
        "evidence": "RAG, agents, eval benches after the transformer sitting.",
    },
    {
        "title": "Attention in Neural Nets",
        "url": "https://soundcloud.com/linear-digressions/attention-in-neural-nets",
        "audio_url": "https://feeds.soundcloud.com/stream/637701588-linear-digressions-attention-in-neural-nets.mp3",
        "station_id": "s-attn",
        "sitting_min": 26,
        "provider": "linear-digressions",
        "branches": ["nlp"],
        "evidence": "Katie Malone & Ben Jaffe: attention in 26 minutes. Linear Digressions.",
    },
    {
        "title": "Convolutional Neural Networks",
        "url": "https://soundcloud.com/linear-digressions/convolutional-neural-networks",
        "audio_url": "https://feeds.soundcloud.com/stream/831843865-linear-digressions-convolutional-neural-networks.mp3",
        "station_id": "s-cv",
        "sitting_min": 21,
        "provider": "linear-digressions",
        "branches": ["computer-vision"],
        "evidence": "Punchy CNN intuition from the Udacity-era teaching show.",
    },
    {
        "title": "Word2Vec",
        "url": "https://soundcloud.com/linear-digressions/re-release-word2vec",
        "audio_url": "https://feeds.soundcloud.com/stream/552052683-linear-digressions-re-release-word2vec.mp3",
        "station_id": "s-ir",
        "sitting_min": 17,
        "provider": "linear-digressions",
        "branches": ["nlp"],
        "evidence": "Embeddings before transformers made them invisible.",
    },
    {
        "title": "Regularization",
        "url": "https://soundcloud.com/linear-digressions/regularization",
        "audio_url": "https://feeds.soundcloud.com/stream/285783592-linear-digressions-regularization.mp3",
        "station_id": "s-eval",
        "sitting_min": 17,
        "provider": "linear-digressions",
        "branches": ["eval"],
        "evidence": "Why the model memorizes. Seventeen-minute eval sitting.",
    },
    {
        "title": "Clustering with DBSCAN",
        "url": "https://soundcloud.com/linear-digressions/clustering-with-dbscan",
        "audio_url": "https://feeds.soundcloud.com/stream/358247057-linear-digressions-clustering-with-dbscan.mp3",
        "station_id": "s-unsupervised",
        "sitting_min": 16,
        "provider": "linear-digressions",
        "branches": ["classical-ml"],
        "evidence": "Density clustering without picking k. Linear Digressions.",
    },
    {
        "title": "The Kernel Trick and Support Vector Machines",
        "url": "https://soundcloud.com/linear-digressions/the-kernel-trick-and-support-vector-machines",
        "audio_url": "https://feeds.soundcloud.com/stream/367800293-linear-digressions-the-kernel-trick-and-support-vector-machines.mp3",
        "station_id": "s-ml-do",
        "sitting_min": 17,
        "provider": "linear-digressions",
        "branches": ["classical-ml"],
        "evidence": "The geometry that still explains SVMs. Teaching, not an interview.",
    },
    {
        "title": "Empirical Bayes",
        "url": "https://soundcloud.com/linear-digressions/empirical-bayes",
        "audio_url": "https://feeds.soundcloud.com/stream/308598786-linear-digressions-empirical-bayes.mp3",
        "station_id": "s-prob",
        "sitting_min": 18,
        "provider": "linear-digressions",
        "branches": ["probability"],
        "evidence": "Priors you can actually use. Probability station, eyes-off.",
    },
    {
        "title": "UMAP vs t-SNE",
        "url": "https://soundcloud.com/linear-digressions/unsupervised-dimensionality-reduction-umap-vs-t-sne",
        "audio_url": "https://feeds.soundcloud.com/stream/742527037-linear-digressions-unsupervised-dimensionality-reduction-umap-vs-t-sne.mp3",
        "station_id": "s-unsupervised",
        "sitting_min": 29,
        "provider": "linear-digressions",
        "branches": ["classical-ml"],
        "evidence": "Which projection to trust. Unsupervised sitting.",
    },
    {
        "title": "Convex (and non-convex) Optimization",
        "url": "https://soundcloud.com/linear-digressions/convex-and-non-convex-optimization",
        "audio_url": "https://feeds.soundcloud.com/stream/546033813-linear-digressions-convex-and-non-convex-optimization.mp3",
        "station_id": "s-calc",
        "sitting_min": 20,
        "provider": "linear-digressions",
        "branches": ["calculus"],
        "evidence": "Why gradient descent works when the bowl is convex.",
    },
    {
        "title": "Reinforcement Learning for Artificial Intelligence",
        "url": "https://soundcloud.com/linear-digressions/reinforcement-learning-for-artificial-intelligence",
        "audio_url": "https://feeds.soundcloud.com/stream/272013221-linear-digressions-reinforcement-learning-for-artificial-intelligence.m4a",
        "station_id": "s-rl",
        "sitting_min": 18,
        "provider": "linear-digressions",
        "branches": ["rl"],
        "evidence": "Short RL picture before Sutton & Barto.",
    },
    {
        "title": "Deep RL from Human Preferences",
        "url": "https://soundcloud.com/linear-digressions/deep_rl_from_human_preferences",
        "audio_url": "https://feeds.soundcloud.com/stream/2266737452-linear-digressions-deep_rl_from_human_preferences.mp3",
        "station_id": "s-drl",
        "sitting_min": 19,
        "provider": "linear-digressions",
        "branches": ["rl"],
        "evidence": "The alignment sitting that still explains RLHF.",
    },
]

INTERVIEW_RAW = [
    {
        "title": "The Great AI Fallacy",
        "url": "https://omny.fm/shows/talking-machines/the-great-ai-fallacy",
        "audio_url": "https://sphinx.acast.com/p/open/s/6310c29b8aeabb0014b25f40/e/b0b0925e-4161-42e6-9240-ab75015c3817/media.mp3",
        "sitting_min": 48,
        "provider": "talking-machines",
        "branches": ["eval"],
        "evidence": "Start here: what the field oversells. Talking Machines.",
    },
    {
        "title": "Humans in the Loop and Outside of the Classroom",
        "url": "https://omny.fm/shows/talking-machines/humans-in-the-loop-and-outside-of-the-classroom",
        "audio_url": "https://sphinx.acast.com/p/open/s/6310c29b8aeabb0014b25f40/e/064abeb6-ed86-4733-8f93-abae0022c3d0/media.mp3",
        "sitting_min": 38,
        "provider": "talking-machines",
        "branches": ["eval"],
        "evidence": "HITL as practice, not a slogan. Talking Machines.",
    },
    {
        "title": "Social Choice for Fair Recommendations",
        "url": "https://dataskeptic.com/blog/episodes/2026/social-choice-for-fair-recommendations",
        "audio_url": "https://traffic.libsyn.com/secure/dataskeptic/Robin_No_Ads_V1.mp3",
        "sitting_min": 42,
        "provider": "dataskeptic",
        "branches": ["recommenders"],
        "evidence": "Kyle + guest: fairness as social choice, not a metric dump.",
    },
    {
        "title": "The Evolution of Reasoning in Small Language Models with Yejin Choi",
        "url": "https://twimlai.com/podcast/twimlai/the-evolution-of-reasoning-in-small-language-models/",
        "audio_url": "https://traffic.megaphone.fm/MLN2256483849.mp3",
        "sitting_min": 66,
        "provider": "twiml",
        "level": "intermediate",
        "branches": ["nlp"],
        "evidence": "TWIML: Choi on why small models still reason.",
    },
    {
        "title": "Relational Foundation Models for Enterprise Data with Jure Leskovec",
        "url": "https://twimlai.com/podcast/twimlai/relational-foundation-models-enterprise-data",
        "audio_url": "https://traffic.megaphone.fm/MLN3747054711.mp3",
        "sitting_min": 66,
        "provider": "twiml",
        "level": "intermediate",
        "branches": ["graphs"],
        "evidence": "Leskovec on tables as a foundation-model domain. TWIML.",
    },
    {
        "title": "Disentanglement and Interpretability in Recommender Systems",
        "url": "https://dataskeptic.com/blog/episodes/2026/disentanglement-and-interpretability-in-recommender-systems",
        "audio_url": "https://traffic.libsyn.com/secure/dataskeptic/Ervin_No_Ads_V1.mp3",
        "sitting_min": 30,
        "provider": "dataskeptic",
        "branches": ["recommenders"],
        "evidence": "Data Skeptic interview on making recs inspectable.",
    },
    {
        "title": "Gods and Robots",
        "url": "https://omny.fm/shows/talking-machines/gods-and-robots",
        "audio_url": "https://sphinx.acast.com/p/open/s/6310c29b8aeabb0014b25f40/e/643aa7b4-f98d-49c5-b0d5-ad9800e2803f/media.mp3",
        "sitting_min": 40,
        "provider": "talking-machines",
        "branches": ["ai"],
        "evidence": "Talking Machines: history and myth around machines that think.",
    },
    {
        "title": "Give Users the Wheel",
        "url": "https://dataskeptic.com/blog/episodes/2026/give-users-the-wheel",
        "audio_url": "https://traffic.libsyn.com/secure/dataskeptic/Fuyuan_Lyu_No_Ads_V1.mp3",
        "sitting_min": 35,
        "provider": "dataskeptic",
        "branches": ["recommenders"],
        "evidence": "User control over the ranker, not another black box.",
    },
    {
        "title": "Why the Next AI Breakthrough May Come from Physics with Max Welling",
        "url": "https://twimlai.com/podcast/twimlai/why-next-ai-breakthrough-may-come-physics",
        "audio_url": "https://traffic.megaphone.fm/MLN6316777640.mp3",
        "sitting_min": 58,
        "provider": "twiml",
        "level": "intermediate",
        "branches": ["theory"],
        "evidence": "Welling on inductive bias from physics. TWIML.",
    },
    {
        "title": "Learning with Less, Invisible Labor and Combating Anti-Blackness",
        "url": "https://omny.fm/shows/talking-machines/learning-with-less-invisible-labor-and-combating-a",
        "audio_url": "https://sphinx.acast.com/p/open/s/6310c29b8aeabb0014b25f40/e/f9c9f6bb-9d32-4497-b860-ad600160f130/media.mp3",
        "sitting_min": 36,
        "provider": "talking-machines",
        "branches": ["eval"],
        "evidence": "Who the data work falls on. Talking Machines.",
    },
    {
        "title": "Cracking the Cold Start Problem",
        "url": "https://dataskeptic.com/blog/episodes/2025/cracking-the-cold-start-problem",
        "audio_url": "https://traffic.libsyn.com/secure/dataskeptic/Boya_No_Ads_V1.mp3",
        "sitting_min": 40,
        "provider": "dataskeptic",
        "branches": ["recommenders"],
        "evidence": "Cold start as a research interview, not a blog post.",
    },
    {
        "title": "The History of Machine Learning from the Inside Out",
        "url": "https://omny.fm/shows/talking-machines/the-history-of-machine-learning-from-the-inside-ou",
        "audio_url": "https://sphinx.acast.com/p/open/s/6310c29b8aeabb0014b25f40/e/54a56ccbe4b0ab38fed9fc81%3A54a57bffe4b0fe1194167e61%3A54ef4512e4b0b5ba2b979706/media.mp3",
        "sitting_min": 32,
        "provider": "talking-machines",
        "branches": ["ai"],
        "evidence": "Lawrence and Adams on how the field got here.",
    },
    {
        "title": "OpenAI and Gaussian Processes",
        "url": "https://omny.fm/shows/talking-machines/openai-and-gaussian-processes",
        "audio_url": "https://sphinx.acast.com/p/open/s/6310c29b8aeabb0014b25f40/e/54a56ccbe4b0ab38fed9fc81%3A54a57bffe4b0fe1194167e61%3A56aa5a71fb36b15e28b8cded/media.mp3",
        "sitting_min": 35,
        "provider": "talking-machines",
        "branches": ["classical-ml"],
        "evidence": "Early OpenAI plus the GP sitting that still holds.",
    },
    {
        "title": "ANGLICAN and Probabilistic Programming",
        "url": "https://omny.fm/shows/talking-machines/anglican-and-probabilistic-programming",
        "audio_url": "https://sphinx.acast.com/p/open/s/6310c29b8aeabb0014b25f40/e/54a56ccbe4b0ab38fed9fc81%3A54a57bffe4b0fe1194167e61%3A581372ae5016e1262b70ff82/media.mp3",
        "sitting_min": 44,
        "provider": "talking-machines",
        "branches": ["probability"],
        "evidence": "Probabilistic programming from the people who built it.",
    },
    {
        "title": "AI Safety and The Legacy of Bletchley Park",
        "url": "https://omny.fm/shows/talking-machines/ai-safety-and-the-legacy-of-bletchley-park",
        "audio_url": "https://sphinx.acast.com/p/open/s/6310c29b8aeabb0014b25f40/e/54a56ccbe4b0ab38fed9fc81%3A54a57bffe4b0fe1194167e61%3A56d06e4a45bf211cff51e652/media.mp3",
        "sitting_min": 48,
        "provider": "talking-machines",
        "branches": ["eval"],
        "evidence": "Safety talk before the slogan era. Talking Machines.",
    },
    {
        "title": "Book Ratings and Recommendations",
        "url": "https://dataskeptic.com/blog/episodes/2026/book-ratings-and-recomendations",
        "audio_url": "https://traffic.libsyn.com/secure/dataskeptic/Hannes_No_Ads_V1.mp3",
        "sitting_min": 39,
        "provider": "dataskeptic",
        "branches": ["recommenders"],
        "evidence": "Ratings as a social object. Data Skeptic.",
    },
    {
        "title": "Collective Altruism in Recommender Systems",
        "url": "https://dataskeptic.com/blog/episodes/2026/collective-altruism-in-recommender-systems",
        "audio_url": "https://traffic.libsyn.com/secure/dataskeptic/Ekatrina_No_With_Ads_V1.mp3",
        "sitting_min": 54,
        "provider": "dataskeptic",
        "branches": ["recommenders"],
        "evidence": "When the objective is not just clicks.",
    },
    {
        "title": "AutoLike",
        "url": "https://dataskeptic.com/blog/episodes/2026/autolike",
        "audio_url": "https://traffic.libsyn.com/secure/dataskeptic/Hieu_No_Ads_V1.mp3",
        "sitting_min": 35,
        "provider": "dataskeptic",
        "branches": ["recommenders"],
        "evidence": "Implicit feedback interview. Current Data Skeptic.",
    },
    {
        "title": "Predicting Floods and Really Doing Good",
        "url": "https://omny.fm/shows/talking-machines/predicting-floods-and-really-doing-good",
        "audio_url": "https://sphinx.acast.com/p/open/s/6310c29b8aeabb0014b25f40/e/a3d5e263-f0d1-4960-a713-abca014b3daa/media.mp3",
        "sitting_min": 39,
        "provider": "talking-machines",
        "branches": ["mlsys"],
        "evidence": "ML that has to work in weather, not a notebook.",
    },
    {
        "title": "If a Machine Could Predict Your Death, Should it?",
        "url": "https://omny.fm/shows/talking-machines/if-a-machine-could-predict-your-death-should-it",
        "audio_url": "https://sphinx.acast.com/p/open/s/6310c29b8aeabb0014b25f40/e/67d52fd0-07cf-489c-b261-ab6701707336/media.mp3",
        "sitting_min": 18,
        "provider": "talking-machines",
        "branches": ["eval"],
        "evidence": "Short ethics interview. Finish before the next stop.",
    },
    {
        "title": "Responsibility, Risk, and Publishing",
        "url": "https://omny.fm/shows/talking-machines/responsibility-risk-and-publishing",
        "audio_url": "https://sphinx.acast.com/p/open/s/6310c29b8aeabb0014b25f40/e/11240982-64ea-43b0-ae89-ad890172c4a8/media.mp3",
        "sitting_min": 25,
        "provider": "talking-machines",
        "branches": ["eval"],
        "evidence": "How the field decides what to ship in a paper.",
    },
    {
        "title": "Prioritizing Problems and 100 episodes",
        "url": "https://omny.fm/shows/talking-machines/prioritizing-problems-and-100-episodes",
        "audio_url": "https://sphinx.acast.com/p/open/s/6310c29b8aeabb0014b25f40/e/4cefa8ce-3ac1-4b72-b4c5-ab8401623a7e/media.mp3",
        "sitting_min": 30,
        "provider": "talking-machines",
        "branches": ["eval"],
        "evidence": "What is even worth modeling. Talking Machines.",
    },
]

APPLY_RAW = [
    {
        "title": "Less about Models; More about Architecture",
        "url": "https://share.transistor.fm/s/ec79b4ac",
        "audio_url": "https://media.transistor.fm/ec79b4ac/efba87b4.mp3",
        "sitting_min": 45,
        "provider": "practical-ai",
        "branches": ["mlsys"],
        "evidence": "Start here: the harness beats the next checkpoint. Practical AI.",
    },
    {
        "title": "Models, Harnesses, and Multi-Agent Systems",
        "url": "https://share.transistor.fm/s/063cfaad",
        "audio_url": "https://media.transistor.fm/063cfaad/23dc320d.mp3",
        "sitting_min": 49,
        "provider": "practical-ai",
        "branches": ["agents"],
        "evidence": "How production agent stacks are actually wired.",
    },
    {
        "title": "Building Durable AI Agents",
        "url": "https://share.transistor.fm/s/facb92e2",
        "audio_url": "https://media.transistor.fm/facb92e2/33d1bc96.mp3",
        "sitting_min": 46,
        "provider": "practical-ai",
        "branches": ["agents"],
        "evidence": "Agents that survive restarts. Changelog Practical AI.",
    },
    {
        "title": "How to Engineer AI Inference Systems with Philip Kiely",
        "url": "https://twimlai.com/podcast/twimlai/how-engineer-ai-inference-systems",
        "audio_url": "https://traffic.megaphone.fm/MLN3829343846.mp3",
        "sitting_min": 54,
        "provider": "twiml",
        "level": "intermediate",
        "branches": ["mlsys"],
        "evidence": "Serving as an engineering problem. TWIML.",
    },
    {
        "title": "Why AI Infrastructure must evolve for Agent Experience",
        "url": "https://www.latent.space/p/modal2026",
        "audio_url": "https://api.substack.com/feed/podcast/205716015/3060ccd83d88111aef06dc1ba0e2b411.mp3",
        "sitting_min": 57,
        "provider": "latent-space",
        "level": "intermediate",
        "branches": ["mlsys"],
        "evidence": "Modal CTO on infra that agents can actually use.",
    },
    {
        "title": "Retrieval After RAG: Hybrid Search, Agents, and Database Design",
        "url": "https://www.latent.space/p/turbopuffer",
        "audio_url": "https://api.substack.com/feed/podcast/190777516/3e8657eee5a6ccb27814143e15672fd5.mp3",
        "sitting_min": 60,
        "provider": "latent-space",
        "level": "intermediate",
        "branches": ["nlp"],
        "evidence": "What replaces naive RAG in production. Latent Space.",
    },
    {
        "title": "Zero Trust for AI Agents",
        "url": "https://share.transistor.fm/s/5c1a087d",
        "audio_url": "https://media.transistor.fm/5c1a087d/89d77a53.mp3",
        "sitting_min": 47,
        "provider": "practical-ai",
        "branches": ["mlsys"],
        "evidence": "Authn for tools the model can call.",
    },
    {
        "title": "While loops with tool calls",
        "url": "https://share.transistor.fm/s/ca41b93c",
        "audio_url": "https://media.transistor.fm/ca41b93c/a54b2afe.mp3",
        "sitting_min": 44,
        "provider": "practical-ai",
        "branches": ["agents"],
        "evidence": "The agent loop as a control-flow problem. Practical AI.",
    },
    {
        "title": "Context Engineering for Productive AI Agents with Filip Kozera",
        "url": "https://twimlai.com/podcast/twimlai/context-engineering-for-productive-ai-agents/",
        "audio_url": "https://traffic.megaphone.fm/MLN9863568954.mp3",
        "sitting_min": 46,
        "provider": "twiml",
        "level": "intermediate",
        "branches": ["agents"],
        "evidence": "Context as the production surface. TWIML.",
    },
    {
        "title": "How Capital One Delivers Multi-Agent Systems",
        "url": "https://twimlai.com/podcast/twimlai/how-capital-one-delivers-multi-agent-systems",
        "audio_url": "https://traffic.megaphone.fm/MLN9114691307.mp3",
        "sitting_min": 54,
        "provider": "twiml",
        "level": "intermediate",
        "branches": ["agents"],
        "evidence": "A bank shipping multi-agent, not a demo. TWIML.",
    },
    {
        "title": "Rebooting Enterprise AI with MCP and Kubernetes",
        "url": "https://share.transistor.fm/s/d76e02d5",
        "audio_url": "https://media.transistor.fm/d76e02d5/e934139b.mp3",
        "sitting_min": 48,
        "provider": "practical-ai",
        "branches": ["mlsys"],
        "evidence": "MCP + k8s as the boring production path.",
    },
    {
        "title": "Giving Agents Computers",
        "url": "https://www.latent.space/p/daytona",
        "audio_url": "https://api.substack.com/feed/podcast/198688585/e48f923a6fb4c7f822f1f5013a97c41d.mp3",
        "sitting_min": 70,
        "provider": "latent-space",
        "level": "intermediate",
        "branches": ["agents"],
        "evidence": "Sandboxes the agent can actually use. Latent Space.",
    },
    {
        "title": "Building the Foundation for the Agentic AI Era",
        "url": "https://share.transistor.fm/s/123da941",
        "audio_url": "https://media.transistor.fm/123da941/719ab12d.mp3",
        "sitting_min": 45,
        "provider": "practical-ai",
        "branches": ["agents"],
        "evidence": "What has to exist before the agent demo ships.",
    },
    {
        "title": "Dealing with increasingly complicated agents",
        "url": "https://share.transistor.fm/s/e60866e6",
        "audio_url": "https://media.transistor.fm/e60866e6/972751fe.mp3",
        "sitting_min": 54,
        "provider": "practical-ai",
        "branches": ["agents"],
        "evidence": "When the graph of tools becomes the product.",
    },
    {
        "title": "Beyond chatbots: Agents that tackle your SOPs",
        "url": "https://share.transistor.fm/s/49afc59f",
        "audio_url": "https://media.transistor.fm/49afc59f/0704690c.mp3",
        "sitting_min": 45,
        "provider": "practical-ai",
        "branches": ["agents"],
        "evidence": "SOPs, not chat. Practical AI.",
    },
    {
        "title": "Reconstructing how OpenAI agents attacked Hugging Face",
        "url": "https://share.transistor.fm/s/9d74230b",
        "audio_url": "https://media.transistor.fm/9d74230b/ed549250.mp3",
        "sitting_min": 44,
        "provider": "practical-ai",
        "branches": ["eval"],
        "evidence": "A postmortem you can hear. Security as an apply sitting.",
    },
    {
        "title": "Video Recommendations in Industry",
        "url": "https://dataskeptic.com/blog/episodes/2025/video-recommendations-in-industry",
        "audio_url": "https://traffic.libsyn.com/secure/dataskeptic/Cory_With_Ads_V1.mp3",
        "sitting_min": 38,
        "provider": "dataskeptic",
        "branches": ["recommenders"],
        "evidence": "How video ranking actually ships. Data Skeptic.",
    },
    {
        "title": "AI at the Edge is a different operating environment",
        "url": "https://share.transistor.fm/s/ea7694a9",
        "audio_url": "https://media.transistor.fm/ea7694a9/378817af.mp3",
        "sitting_min": 47,
        "provider": "practical-ai",
        "branches": ["mlsys"],
        "evidence": "Edge constraints as architecture, not a smaller model.",
    },
]

PULSE_RAW = [
    {
        "title": "Breaking down the 2026 Stanford AI Index Report",
        "url": "https://share.transistor.fm/s/302b36f8",
        "audio_url": "https://media.transistor.fm/302b36f8/d474795e.mp3",
        "sitting_min": 47,
        "provider": "practical-ai",
        "branches": ["eval"],
        "evidence": "Start here: the yearly scoreboard, narrated. Pulse, not a lesson.",
    },
    {
        "title": "Recommender Systems Origin Story",
        "url": "https://dataskeptic.com/blog/episodes/2026/recommender-systems-origin-story",
        "audio_url": "https://traffic.libsyn.com/secure/dataskeptic/recsys-finale-pt1.mp3",
        "sitting_min": 25,
        "provider": "dataskeptic",
        "branches": ["recommenders"],
        "evidence": "How we got the recsys stack. Data Skeptic current season.",
    },
    {
        "title": "2025 was the year of agents, what's coming in 2026?",
        "url": "https://share.transistor.fm/s/e7fda8ce",
        "audio_url": "https://media.transistor.fm/e7fda8ce/c218cdfa.mp3",
        "sitting_min": 51,
        "provider": "practical-ai",
        "branches": ["agents"],
        "evidence": "The agent year in review. Practical AI.",
    },
    {
        "title": "The End of SWE-Bench Verified",
        "url": "https://www.latent.space/p/swe-bench-dead",
        "audio_url": "https://api.substack.com/feed/podcast/188928663/d1b8836e5d38b238ccf001345a411fc7.mp3",
        "sitting_min": 26,
        "provider": "latent-space",
        "branches": ["eval"],
        "evidence": "What broke in the coding eval everyone cited. Latent Space.",
    },
    {
        "title": "Recommender Systems Today and Tomorrow",
        "url": "https://dataskeptic.com/blog/episodes/2026/recommender-systems-today-and-tomorrow",
        "audio_url": "https://traffic.libsyn.com/secure/dataskeptic/part3-withad.mp3",
        "sitting_min": 22,
        "provider": "dataskeptic",
        "branches": ["recommenders"],
        "evidence": "Where recsys is pointed now. Short pulse.",
    },
    {
        "title": "The Future is Agentic in Recommender Systems",
        "url": "https://dataskeptic.com/blog/episodes/2026/The-future-is-agentic-in-recommender-systems",
        "audio_url": "https://traffic.libsyn.com/secure/dataskeptic/Yashar_No_Ads_V1.mp3",
        "sitting_min": 49,
        "provider": "dataskeptic",
        "branches": ["agents", "recommenders"],
        "evidence": "Agents inside ranking. Current Data Skeptic.",
    },
    {
        "title": "The Myth of Model Wars: Open vs Closed AI in 2026",
        "url": "https://share.transistor.fm/s/6095edc5",
        "audio_url": "https://media.transistor.fm/6095edc5/d370f038.mp3",
        "sitting_min": 42,
        "provider": "practical-ai",
        "branches": ["eval"],
        "evidence": "Open vs closed as this year's argument. Practical AI.",
    },
    {
        "title": "Computer-Use Agents and the Future of the Agentic Internet",
        "url": "https://share.transistor.fm/s/72586f97",
        "audio_url": "https://media.transistor.fm/72586f97/42471284.mp3",
        "sitting_min": 56,
        "provider": "practical-ai",
        "branches": ["agents"],
        "evidence": "What just changed in computer-use agents.",
    },
    {
        "title": "State of RL/Reasoning: IMO/IOI Gold, o3/GPT-5, and Cursor Composer",
        "url": "https://www.latent.space/p/state-of-rlreasoning-imoioi-gold",
        "audio_url": "https://api.substack.com/feed/podcast/186610562/84a86ba6927f827c7d138818724a3e00.mp3",
        "sitting_min": 45,
        "provider": "latent-space",
        "level": "intermediate",
        "branches": ["rl"],
        "evidence": "Where reasoning stacks sat this year. Latent Space.",
    },
    {
        "title": "Recommender Systems Optimization Goals",
        "url": "https://dataskeptic.com/blog/episodes/2026/recommender-systems-optimization-goals",
        "audio_url": "https://traffic.libsyn.com/secure/dataskeptic/1finale-part-2-final-adfree.mp3",
        "sitting_min": 31,
        "provider": "dataskeptic",
        "branches": ["recommenders"],
        "evidence": "What recsys is optimizing for now. Data Skeptic.",
    },
    {
        "title": "Are we in an AI bubble?",
        "url": "https://share.transistor.fm/s/533b0b3f",
        "audio_url": "https://media.transistor.fm/533b0b3f/ebbf2629.mp3",
        "sitting_min": 49,
        "provider": "practical-ai",
        "branches": ["eval"],
        "evidence": "The bubble argument, dated. Pulse.",
    },
    {
        "title": "News Recommendations",
        "url": "https://dataskeptic.com/blog/episodes/2026/news-recommendations",
        "audio_url": "https://traffic.libsyn.com/secure/dataskeptic/Andreea_No_Ads_V1.mp3",
        "sitting_min": 46,
        "provider": "dataskeptic",
        "branches": ["recommenders"],
        "evidence": "News ranking as a live system, not a toy dataset.",
    },
    {
        "title": "AI Proficiency: From Users to Builders",
        "url": "https://share.transistor.fm/s/0f57c0bc",
        "audio_url": "https://media.transistor.fm/0f57c0bc/34496de8.mp3",
        "sitting_min": 56,
        "provider": "practical-ai",
        "branches": ["mlsys"],
        "evidence": "Who is actually becoming a builder this year.",
    },
    {
        "title": "State of Post-Training: From GPT-4.1 to 5.1",
        "url": "https://www.latent.space/p/state-of-post-training-from-gpt-41",
        "audio_url": "https://api.substack.com/feed/podcast/186610564/4944e1f91a0d0d17e5525fb297469684.mp3",
        "sitting_min": 27,
        "provider": "latent-space",
        "level": "intermediate",
        "branches": ["nlp"],
        "evidence": "RLVR and token efficiency, this cycle. Latent Space.",
    },
    {
        "title": "NeurIPS Best Paper: 1000 Layer Networks for Self-Supervised RL",
        "url": "https://www.latent.space/p/neurips-best-paper-1000-layer-networks",
        "audio_url": "https://api.substack.com/feed/podcast/186610577/1c67d698a72366b17c184a249d44225b.mp3",
        "sitting_min": 28,
        "provider": "latent-space",
        "level": "intermediate",
        "branches": ["rl"],
        "evidence": "A best-paper walk, not a lesson. Latent Space.",
    },
    {
        "title": "Niche vs Mainstream",
        "url": "https://dataskeptic.com/blog/episodes/2026/niche-vs-mainstream",
        "audio_url": "https://traffic.libsyn.com/secure/dataskeptic/Anas_With_Ads_V1.mp3",
        "sitting_min": 34,
        "provider": "dataskeptic",
        "branches": ["recommenders"],
        "evidence": "Long-tail vs popular this recsys season.",
    },
    {
        "title": "Post-Mortem of Anthropic's Claude Code Leak",
        "url": "https://share.transistor.fm/s/44e59b0b",
        "audio_url": "https://media.transistor.fm/44e59b0b/1ecd61fa.mp3",
        "sitting_min": 44,
        "provider": "practical-ai",
        "branches": ["eval"],
        "evidence": "What leaked, dated. Pulse, not architecture.",
    },
]


def _labeled(rows: list[dict], purpose: str) -> list[dict]:
    out = []
    for i, row in enumerate(rows):
        item = dict(row)
        item.pop("station_id", None)
        item["purpose"] = purpose
        item["rank"] = i
        out.append(item)
    return out


EPISODES = (
    _labeled(LEARN_RAW, "learn")
    + _labeled(INTERVIEW_RAW, "interview")
    + _labeled(APPLY_RAW, "apply")
    + _labeled(PULSE_RAW, "pulse")
)


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


def validate_commute(resources: list[dict], nodes: list[dict] | None = None) -> list[str]:
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
                    "purpose": rec.get("purpose"),
                    "rank": rec.get("rank"),
                    "sitting_min": sitting_min,
                }
            )
        )
    return errors


def episode_errors(episode: dict, _unused: set[str] | None = None) -> list[str]:
    errors = []
    title = episode.get("title") or "(untitled)"
    audio = (episode.get("audio_url") or "").strip()
    page = (episode.get("url") or "").strip()
    sitting = episode.get("sitting_min")
    purpose = episode.get("purpose") or ""
    blob = f"{audio} {page}".lower()
    if "youtube.com" in blob or "youtu.be" in blob:
        errors.append(f"{title}: youtube is not an enclosure")
    if not audio:
        errors.append(f"{title}: missing audio_url enclosure")
    else:
        path = urlparse(audio).path.lower()
        if not any(path.endswith(suf) for suf in AUDIO_SUFFIXES):
            errors.append(f"{title}: enclosure must be audio (mp3/m4a/equivalent)")
    if sitting is None or not (12 <= sitting <= 75):
        errors.append(f"{title}: sitting must be 12–75 minutes")
    if purpose not in PURPOSES:
        errors.append(f"{title}: purpose must be one of {', '.join(PURPOSE_ORDER)}")
    rank = episode.get("rank")
    if rank is not None and not isinstance(rank, int):
        errors.append(f"{title}: rank must be an int")
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
        "evidence": episode.get("evidence") or "Eyes-off audio for this purpose.",
        "featured": False,
        "audio_url": episode["audio_url"],
        "purpose": episode["purpose"],
        "rank": int(episode.get("rank") or 0),
        "sitting": sitting,
    }
    if sitting_min is not None:
        rec["sitting_min"] = sitting_min
    return rec


def playlist(episodes: list[dict], stations: list[dict] | None = None) -> list[dict]:
    order = {name: i for i, name in enumerate(PURPOSE_ORDER)}
    rows = [ep for ep in episodes if ep.get("purpose") in order]
    return sorted(rows, key=lambda ep: (order[ep["purpose"]], ep.get("rank", 99), ep["title"].lower()))


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
