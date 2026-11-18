#!/usr/bin/env python3
"""
Synthetic data generator for the "Search & Support Effectiveness" dashboard.

EVERYTHING HERE IS SYNTHETIC. "Quillstone Software" is a fictional company; the
agents, cases, queries and articles are invented. No real client data is used.

Usage:
    python generate_data.py                       # writes ./data/*.csv.gz (seed 42)
    python generate_data.py --out data --seed 7 --scale 0.5

Tables written:
    events    release / incident / content annotations for the charts
    agents    one row per support agent
    articles  knowledge-base articles
    cases     support cases handled by agents
    sessions  search sessions (a person searching until they resolve it or give up)
    searches  one row per query inside a session

Planted patterns (so the dashboard has a real story to tell):
    1. Search relevance regression   2026-07-21 .. 2026-07-27 (index/synonym change):
       more zero-result searches, lower CTR, slower time-to-click, latency spike.
    2. Feature launch gap            "Workflow & Automation" launches 2026-08-17, but
       docs only publish 2026-09-08 -> three weeks of unanswerable demand.
    3. Persistent content gaps       Integrations has many topics with no article at all;
       a few topics elsewhere (SCIM, PO invoicing, field-level permissions, ...).
    4. Vocabulary mismatch           users search "locked out", "app crashing" but the
       articles use other words -> synonym opportunities.
    5. Weak / stale content          articles that get clicked but rarely resolve
       (API & Webhooks is stale; a few "weak" topics elsewhere).
    6. Mobile incident               2026-06-09 .. 2026-06-12 spike of "app crashing".
    7. Agent skill spread            5 star agents, 8 brand-new agents, learning curve.
    8. Search matters                cases where the agent finds an answer resolve
       faster, escalate less and score higher CSAT.
    9. Seasonality                   weekday/weekend, hour of day, month-end billing spike,
       US holidays, slow growth.
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

COMPANY = "Quillstone Software"

START = pd.Timestamp("2026-05-01")
END_EXCL = pd.Timestamp("2026-11-01")
REG_START = pd.Timestamp("2026-07-21")
REG_END_EXCL = pd.Timestamp("2026-07-28")
INCIDENT_START = pd.Timestamp("2026-06-09")
INCIDENT_END_EXCL = pd.Timestamp("2026-06-13")
LAUNCH = pd.Timestamp("2026-08-17")
DOCS = pd.Timestamp("2026-09-08")
WORKFLOW = "Workflow & Automation"
HOLIDAYS = {"2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07"}


def _sec(ts: pd.Timestamp) -> float:
    return float(ts.timestamp())


START_SEC, END_SEC = _sec(START), _sec(END_EXCL)
REG0, REG1 = _sec(REG_START), _sec(REG_END_EXCL)
INC0, INC1 = _sec(INCIDENT_START), _sec(INCIDENT_END_EXCL)
LAUNCH_SEC, DOCS_SEC = _sec(LAUNCH), _sec(DOCS)

# --------------------------------------------------------------------------------------
# Topic catalogue.  "canonical|variant|variant".  Prefix flags:
#   !  no article exists (content gap)      ~  article exists, vocabulary mismatch
#   *  article exists but is weak (clicked, rarely resolves)
# --------------------------------------------------------------------------------------
TOPIC_SPEC: dict[str, list[str]] = {
    "Authentication & SSO": [
        "configure saml sso|saml setup|sso configuration okta|set up single sign on",
        "reset user password|password reset email not received|forgot password link expired",
        "enable two factor authentication|2fa setup|mfa not working",
        "sso login loop|saml 403 error|sso redirect error",
        "session timeout settings|auto logout|session expires too fast",
        "!scim user provisioning|okta scim provisioning|scim sync failing",
        "ip allowlist|restrict login by ip|allowed ip ranges",
        "~unlock user account|locked out of account|too many login attempts",
    ],
    "Billing & Invoices": [
        "download invoice|invoice pdf|past invoices",
        "update payment method|change credit card|card declined",
        "change subscription plan|upgrade plan|downgrade plan",
        "update billing contact|change billing email|invoice recipient",
        "add vat number|tax id on invoice|tax exemption certificate",
        "proration charges|prorated billing|unexpected charge",
        "!pay by purchase order|purchase order invoicing|net 60 payment terms",
        "cancel subscription|cancel account|refund policy",
        "usage overage charges|overage pricing|seat true up",
    ],
    "API & Webhooks": [
        "api rate limits|429 too many requests|rate limit headers",
        "create api key|generate api token|api authentication",
        "webhook signature verification|verify webhook|webhook signing secret",
        "*webhook retries|webhook not firing|webhook delivery failed",
        "*pagination cursor|list endpoint pagination|next page token",
        "bulk api endpoint|batch requests|bulk create records",
        "api versioning|deprecated endpoints|v1 to v2 migration",
        "oauth scopes|oauth token refresh|authorization code flow",
    ],
    "Integrations": [
        "jira integration setup|link jira issues|jira sync",
        "google sheets export|connect google sheets|sheets sync",
        "!salesforce field mapping|salesforce sync custom fields|salesforce integration",
        "hubspot connector|hubspot sync contacts|hubspot integration error",
        "!slack channel permissions|slack app not posting|connect slack",
        "sftp scheduled export|sftp connection|automated file export",
        "!zapier trigger delays|zapier integration|zap not triggering",
        "!microsoft teams notifications|teams integration|teams webhook",
    ],
    "Data Import & Export": [
        "*import csv|csv upload error|bulk import users",
        "export data|download all records|export to excel",
        "data retention policy|delete old data|retention settings",
        "*merge duplicate records|duplicate records|dedupe import",
        "map import fields|map columns|custom fields import",
        "~import stuck|upload hangs|import never finishes",
        "restore deleted records|backup restore|undelete",
        "fix import date format|wrong date format|timezone mismatch",
    ],
    "Permissions & Roles": [
        "create custom role|custom permissions|role editor",
        "admin vs member permissions|what can admins do|admin permissions",
        "share dashboard permissions|view only access|restrict access to project",
        "audit log|who changed setting|activity log export",
        "invite users|add team member|invitation expired",
        "deactivate user|remove user|offboard employee",
        "!field level permissions|hide sensitive fields|column level security",
        "transfer ownership|change owner|owner left company",
    ],
    "Reports & Dashboards": [
        "build custom report|create report|report builder",
        "*schedule report email|scheduled reports|report not sending",
        "dashboard filters|filter not applying|global filters",
        "export report to pdf|pdf export cut off|print dashboard",
        "change chart type|chart types|add trend line",
        "*calculated fields|custom formula|formula syntax",
        "!embed dashboard|embed report in website|iframe embed",
        "report numbers dont match|report data mismatch|report discrepancy",
    ],
    "Mobile App": [
        "~app crashing|app keeps crashing|app freezes on launch",
        "mobile push notifications|not receiving push|enable notifications on phone",
        "offline mode|work offline|sync when back online",
        "biometric login|face id login|mobile login",
        "update mobile app|app version|minimum supported version",
        "scan barcode|camera scanner|qr code scan",
        "dark mode|change theme|font size",
    ],
    "Security & Compliance": [
        "soc 2 report|request soc2|compliance documents",
        "gdpr data request|delete personal data|data subject request",
        "data residency|eu data center|where is data stored",
        "encryption at rest|encryption keys|customer managed keys",
        "!hipaa baa|hipaa compliance|sign baa",
        "security questionnaire|vendor assessment|penetration test results",
        "report vulnerability|bug bounty|responsible disclosure",
        "subprocessor list|data processing agreement|dpa signing",
    ],
    WORKFLOW: [  # launched 2026-08-17, docs published 2026-09-08
        "create workflow|workflow builder|automation rule",
        "workflow triggers|trigger conditions|when record created",
        "workflow actions|send email action|update field action",
        "workflow not running|automation failed|workflow error log",
        "!workflow templates|automation examples|prebuilt workflows",
        "approval workflow|approval step|require approval",
        "!workflow limits|automation quota|max actions per run",
        "schedule workflow|recurring automation|run daily",
    ],
}
AREAS = list(TOPIC_SPEC)
# share of searches: (customers, agents)
AREA_WEIGHT = {
    "Authentication & SSO": (16, 11), "Billing & Invoices": (15, 7), "API & Webhooks": (7, 14),
    "Integrations": (7, 12), "Data Import & Export": (9, 9), "Permissions & Roles": (9, 8),
    "Reports & Dashboards": (10, 8), "Mobile App": (8, 3), "Security & Compliance": (4, 7),
    WORKFLOW: (7, 9),
}
AREA_RELEVANCE = {a: 1.0 for a in AREAS} | {"API & Webhooks": 0.90}
AREA_COMPLEXITY = {
    "Authentication & SSO": 0.95, "Billing & Invoices": 0.8, "API & Webhooks": 1.25,
    "Integrations": 1.35, "Data Import & Export": 1.05, "Permissions & Roles": 0.9,
    "Reports & Dashboards": 1.0, "Mobile App": 0.95, "Security & Compliance": 1.2, WORKFLOW: 1.3,
}
TEAMS = {"Tier 1 Support": 18, "Tier 2 Technical": 10, "Billing & Accounts": 6, "Onboarding & Success": 6}
TEAM_BY_AREA = {
    "Billing & Invoices": {"Billing & Accounts": .72, "Tier 1 Support": .28},
    "Authentication & SSO": {"Tier 1 Support": .62, "Tier 2 Technical": .28, "Onboarding & Success": .10},
    "API & Webhooks": {"Tier 2 Technical": .70, "Tier 1 Support": .30},
    "Integrations": {"Tier 2 Technical": .55, "Onboarding & Success": .25, "Tier 1 Support": .20},
    "Data Import & Export": {"Tier 1 Support": .50, "Onboarding & Success": .30, "Tier 2 Technical": .20},
    "Permissions & Roles": {"Tier 1 Support": .72, "Onboarding & Success": .18, "Tier 2 Technical": .10},
    "Reports & Dashboards": {"Tier 1 Support": .60, "Onboarding & Success": .30, "Tier 2 Technical": .10},
    "Mobile App": {"Tier 1 Support": .80, "Tier 2 Technical": .20},
    "Security & Compliance": {"Tier 2 Technical": .60, "Tier 1 Support": .40},
    WORKFLOW: {"Tier 2 Technical": .50, "Onboarding & Success": .30, "Tier 1 Support": .20},
}
ESCALATION_BASE = {"Tier 1 Support": 0.13, "Tier 2 Technical": 0.05, "Billing & Accounts": 0.04,
                   "Onboarding & Success": 0.06}

DOW = np.array([1.12, 1.15, 1.10, 1.05, 0.95, 0.42, 0.38])  # Mon..Sun
H_CUSTOMER = np.array([.3, .2, .15, .15, .2, .4, .8, 1.6, 3.2, 4.6, 5.2, 4.8,
                       4.2, 4.6, 5.0, 4.6, 3.8, 2.8, 2.0, 1.6, 1.4, 1.1, .8, .5])
H_AGENT = np.zeros(24)
H_AGENT[8:20] = [2.5, 4.2, 4.8, 4.4, 3.0, 3.6, 4.4, 4.2, 3.4, 2.6, 1.6, 0.8]
H_CUSTOMER, H_AGENT = H_CUSTOMER / H_CUSTOMER.sum(), H_AGENT / H_AGENT.sum()

ACRONYMS = {"saml": "SAML", "sso": "SSO", "api": "API", "csv": "CSV", "pdf": "PDF", "scim": "SCIM",
            "2fa": "2FA", "mfa": "MFA", "ip": "IP", "vat": "VAT", "oauth": "OAuth", "gdpr": "GDPR",
            "dpa": "DPA", "soc": "SOC", "hipaa": "HIPAA", "baa": "BAA", "sftp": "SFTP", "qr": "QR",
            "id": "ID", "v1": "v1", "v2": "v2", "okta": "Okta", "jira": "Jira", "slack": "Slack",
            "salesforce": "Salesforce", "hubspot": "HubSpot", "zapier": "Zapier", "ios": "iOS"}

FIRST = ["Maya", "Liam", "Noor", "Ethan", "Sofia", "Amir", "Chloe", "Diego", "Hana", "Oliver", "Priya",
         "Lucas", "Zara", "Mateo", "Ines", "Jonas", "Leila", "Owen", "Mei", "Felix", "Anika", "Rafael",
         "Tessa", "Kofi", "Elena", "Samir", "Nora", "Gabriel", "Yuki", "Isla", "Omar", "Clara", "Theo",
         "Aisha", "Marcus", "Lena", "Victor", "Rosa", "Daniel", "Freya"]
LAST = ["Carter", "Nguyen", "Okafor", "Silva", "Haddad", "Lindqvist", "Moreau", "Tanaka", "Patel", "Brennan",
        "Kowalski", "Reyes", "Abara", "Fischer", "Costa", "Ibrahim", "Larsen", "Mensah", "Romano", "Sato",
        "Dubois", "Khan", "Walsh", "Novak", "Bianchi", "Ortega", "Hughes", "Petrov", "Santos", "Weber"]


def _fix_acronyms(text: str) -> str:
    words = " ".join(ACRONYMS.get(w, w) for w in text.split())
    return words[:1].upper() + words[1:]


# --------------------------------------------------------------------------------------
# catalogues
# --------------------------------------------------------------------------------------
def build_topics() -> pd.DataFrame:
    rows = []
    for area, specs in TOPIC_SPEC.items():
        zipf = 1.0 / (np.arange(len(specs)) + 1) ** 0.85
        zipf = zipf / zipf.sum()
        for spec, w in zip(specs, zipf):
            flags = ""
            while spec and spec[0] in "!~*":
                flags, spec = flags + spec[0], spec[1:]
            variants = [v.strip() for v in spec.split("|")]
            rows.append(dict(area=area, topic=variants[0], variants=variants, weight=w,
                             uncovered="!" in flags, syn="~" in flags, weak="*" in flags,
                             launch=(area == WORKFLOW and "!" not in flags)))
    t = pd.DataFrame(rows)
    t["area_id"] = t["area"].map({a: i for i, a in enumerate(AREAS)})
    return t


def build_articles(rng: np.random.Generator, topics: pd.DataFrame) -> pd.DataFrame:
    kinds = [("How-to", "{c} - step-by-step guide"), ("Troubleshooting", "{c} - troubleshooting"),
             ("FAQ", "{c} - FAQ"), ("Reference", "{c} - reference")]
    rows = []
    for t in topics.itertuples():
        if t.uncovered:
            continue
        n = rng.choice([1, 2, 3], p=[.55, .35, .10])
        for k in rng.permutation(4)[:n]:
            ctype, tpl = kinds[k]
            if t.launch:
                pub = DOCS
            else:
                pub = START - pd.Timedelta(days=int(rng.integers(40, 1800)))
            if t.area == "API & Webhooks" or t.weak:
                q = float(np.clip(rng.beta(3.6, 3.0), .35, .8)) if not t.weak else float(np.clip(rng.beta(1.6, 6.0), .05, .28))
                upd = max(pub, pd.Timestamp("2023-06-01") + pd.Timedelta(days=int(rng.integers(0, 430))))
            else:
                q = float(np.clip(rng.beta(6.0, 2.0), .5, .97))
                span = max((END_EXCL - pub).days, 1)
                upd = pub + pd.Timedelta(days=int(span * rng.beta(2.0, 1.2)))
            rows.append(dict(title=tpl.format(c=_fix_acronyms(t.topic)), product_area=t.area,
                             content_type=ctype, topic=t.topic, published_date=pub.normalize(),
                             last_updated=min(upd, END_EXCL - pd.Timedelta(days=1)).normalize(), quality=q))
    generic = ["Getting started", "Admin checklist", "Best practices", "Glossary", "Release notes",
               "Migration notes", "Limits and quotas", "Keyboard shortcuts"]
    w = np.array([AREA_WEIGHT[a][1] for a in AREAS], float)
    for i in range(70):
        area = AREAS[rng.choice(len(AREAS), p=w / w.sum())]
        if area == WORKFLOW:
            area = AREAS[0]
        pub = START - pd.Timedelta(days=int(rng.integers(60, 1800)))
        rows.append(dict(title=f"{area}: {generic[i % len(generic)]} ({i // len(generic) + 1})",
                         product_area=area, content_type="Reference" if i % 3 else "Release notes",
                         topic="general", published_date=pub.normalize(),
                         last_updated=(pub + pd.Timedelta(days=int(rng.integers(0, 900)))).normalize(),
                         quality=float(rng.beta(4, 3))))
    a = pd.DataFrame(rows)
    a.insert(0, "article_id", [f"KB-{1000 + i}" for i in range(len(a))])
    return a


def build_agents(rng: np.random.Generator) -> pd.DataFrame:
    rows, used = [], set()
    for team, n in TEAMS.items():
        for _ in range(n):
            while True:
                name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
                if name not in used:
                    used.add(name)
                    break
            rows.append(dict(name=name, team=team,
                             tenure_months=int(min(rng.gamma(2.0, 14) + 1, 96)),
                             region=rng.choice(["Americas", "EMEA", "APAC"], p=[.55, .30, .15])))
    a = pd.DataFrame(rows)
    a["skill"] = rng.beta(5, 3, len(a)) * (0.62 + 0.38 * np.minimum(a["tenure_months"] / 8, 1))
    stars = a[(a.tenure_months > 24)].sample(5, random_state=int(rng.integers(1_000_000))).index
    a.loc[stars, "skill"] = rng.uniform(0.90, 0.97, len(stars))
    new = a[(a.team.isin(["Tier 1 Support", "Onboarding & Success"])) & (~a.index.isin(stars))] \
        .sample(8, random_state=int(rng.integers(1_000_000))).index
    a.loc[new, "tenure_months"] = rng.integers(1, 4, len(new))
    a.loc[new, "skill"] = rng.uniform(0.25, 0.45, len(new))
    a["capacity"] = rng.uniform(0.7, 1.3, len(a)) * np.where(a.tenure_months < 4, 0.6, 1.0)
    a.insert(0, "agent_id", [f"A-{i + 1:03d}" for i in range(len(a))])
    return a


# --------------------------------------------------------------------------------------
# volume model
# --------------------------------------------------------------------------------------
def day_table() -> pd.DataFrame:
    days = pd.date_range(START, END_EXCL - pd.Timedelta(days=1), freq="D")
    d = pd.DataFrame({"day": days})
    d["sec"] = [_sec(x) for x in days]
    f = DOW[days.dayofweek] * (1 + 0.12 * np.arange(len(days)) / (len(days) - 1))
    f = np.where(days.strftime("%Y-%m-%d").isin(HOLIDAYS), f * 0.55, f)
    d["factor"] = f
    since_launch = (days - LAUNCH).days.values
    surge = np.where(since_launch >= 0, 1 + 0.18 * np.exp(-since_launch / 21), 1.0)
    inc = ((days >= INCIDENT_START) & (days < INCIDENT_END_EXCL)).astype(float)
    d["cust_mult"] = surge * (1 + 0.35 * inc)
    d["agent_mult"] = surge * (1 + 0.15 * inc)
    return d


def topic_weights(day: pd.Timestamp, topics: pd.DataFrame, user: int) -> np.ndarray:
    """user: 0 customers, 1 agents."""
    w = topics["weight"].values * topics["area"].map(lambda a: AREA_WEIGHT[a][user]).values
    w = w.astype(float)
    area = topics["area"].values
    if day.day >= 28 or day.day <= 2:
        w[area == "Billing & Invoices"] *= 1.8
    if day < LAUNCH:
        w[area == WORKFLOW] = 0.0
    else:
        w[area == WORKFLOW] *= 1 + 1.6 * np.exp(-(day - LAUNCH).days / 21)
    if INCIDENT_START <= day < INCIDENT_END_EXCL:
        w[topics["topic"].values == "app crashing"] *= 9.0
    return w / w.sum()


def draw_times(rng, day_sec: np.ndarray, pdf: np.ndarray) -> np.ndarray:
    hour = rng.choice(24, size=len(day_sec), p=pdf)
    return day_sec + hour * 3600 + rng.integers(0, 3600, len(day_sec))


def make_sessions(rng, topics, agents, days, scale):
    # ---- customers (help centre / in-app widget)
    n_c = rng.poisson(221 * scale * days["factor"].values * days["cust_mult"].values)
    c_day = np.repeat(np.arange(len(days)), n_c)
    c_ts = draw_times(rng, days["sec"].values[c_day], H_CUSTOMER)
    c_topic = np.empty(len(c_day), int)
    for di in np.unique(c_day):
        m = c_day == di
        c_topic[m] = rng.choice(len(topics), size=m.sum(), p=topic_weights(days["day"][di], topics, 0))
    cust = pd.DataFrame(dict(start=c_ts, topic_id=c_topic, agent_idx=-1, case_idx=-1,
                             user_type="Customer",
                             channel=rng.choice(["Help Center", "In-App Widget"], len(c_ts), p=[.72, .28])))

    # ---- cases and agent sessions (support console)
    n_k = rng.poisson(105 * scale * days["factor"].values * days["agent_mult"].values)
    k_day = np.repeat(np.arange(len(days)), n_k)
    k_ts = draw_times(rng, days["sec"].values[k_day], H_AGENT)
    k_topic = np.empty(len(k_day), int)
    for di in np.unique(k_day):
        m = k_day == di
        k_topic[m] = rng.choice(len(topics), size=m.sum(), p=topic_weights(days["day"][di], topics, 1))
    k_area = topics["area"].values[k_topic]
    k_team = np.empty(len(k_topic), object)
    for area, dist in TEAM_BY_AREA.items():
        m = k_area == area
        k_team[m] = rng.choice(list(dist), size=m.sum(), p=list(dist.values()))
    k_agent = np.empty(len(k_topic), int)
    for team in TEAMS:
        ag = agents.index[agents.team == team].values
        m = k_team == team
        p = agents.loc[ag, "capacity"].values
        k_agent[m] = rng.choice(ag, size=m.sum(), p=p / p.sum())
    cases = pd.DataFrame(dict(created=k_ts, topic_id=k_topic, agent_idx=k_agent, team=k_team,
                              priority=rng.choice(["P1", "P2", "P3", "P4"], len(k_ts), p=[.05, .20, .45, .30]),
                              channel=rng.choice(["Email", "Chat", "Phone"], len(k_ts), p=[.5, .38, .12])))
    n_sess = 1 + (rng.random(len(cases)) < 0.45) + (rng.random(len(cases)) < 0.15)
    rep = np.repeat(np.arange(len(cases)), n_sess)
    order = np.concatenate([np.arange(k) for k in n_sess])
    offs = rng.exponential(6 * 60, len(rep)) + order * rng.exponential(18 * 60, len(rep))
    a_start = np.minimum(cases["created"].values[rep] + offs, END_SEC - 90)
    agent_sess = pd.DataFrame(dict(start=a_start, topic_id=cases["topic_id"].values[rep],
                                   agent_idx=cases["agent_idx"].values[rep], case_idx=rep,
                                   user_type="Agent", channel="Support Console"))
    sess = pd.concat([cust, agent_sess], ignore_index=True)
    return sess, cases


# --------------------------------------------------------------------------------------
# search simulation
# --------------------------------------------------------------------------------------
def _typo(rng, s: str) -> str:
    if len(s) < 5:
        return s
    i = int(rng.integers(1, len(s) - 2))
    if rng.random() < 0.5:
        return s[:i] + s[i + 1] + s[i] + s[i + 2:]
    return s[:i] + s[i + 1:]


def simulate(rng, topics, articles, agents, sess) -> pd.DataFrame:
    t_area = topics["area_id"].values
    t_unc, t_syn = topics["uncovered"].values, topics["syn"].values
    t_launch = topics["launch"].values
    variants = topics["variants"].values
    nvars = np.array([len(v) for v in variants])
    area_rel = np.array([AREA_RELEVANCE[a] for a in AREAS])
    art_q = articles["quality"].values
    art_by_topic = [articles.index[articles.topic == t.topic].values if not t.uncovered else np.array([], int)
                    for t in topics.itertuples()]
    early = articles[(articles.published_date <= START)]
    pool = [early.index[early.product_area == a].values for a in AREAS]
    global_pool = early.index.values
    agent_skill = agents["skill"].values

    n_s = len(sess)
    s_topic, s_agent = sess["topic_id"].values, sess["agent_idx"].values
    cur_ts = sess["start"].values.astype(float)
    active = np.arange(n_s)
    chunks = []
    for rnd in range(5):
        n = len(active)
        if n == 0:
            break
        top, ag, ts = s_topic[active], s_agent[active], np.minimum(cur_ts[active], END_SEC - 1)
        is_agent = ag >= 0
        sk = np.where(is_agent, agent_skill[np.maximum(ag, 0)], 0.5)
        in_reg = (ts >= REG0) & (ts < REG1)
        has_art = ~t_unc[top] & (~t_launch[top] | (ts >= DOCS_SEC))
        syn = t_syn[top]

        power = np.where(syn, 0.55 if rnd == 0 else 1.0, 1.6)
        vidx = np.minimum((rng.random(n) ** power * nvars[top]).astype(int), nvars[top] - 1)
        query = np.array([variants[t][v] for t, v in zip(top, vidx)], dtype=object)
        typo = rng.random(n) < 0.03
        for i in np.where(typo)[0]:
            query[i] = _typo(rng, query[i])
        cap = rng.random(n) < 0.10
        query = np.where(cap, np.array([q[:1].upper() + q[1:] for q in query], dtype=object), query)

        r = np.where(has_art, np.where(syn, rng.beta(3.6, 3.0, n), rng.beta(7.0, 2.2, n)),
                     rng.beta(1.8, 5.0, n))
        r = r * area_rel[t_area[top]] + np.where(is_agent, (sk - 0.5) * 0.45, -0.04)
        r = r + np.where(has_art, 0.10 * rnd, 0.03 * rnd)
        r = np.clip(np.where(in_reg, r * 0.74, r), 0.02, 0.98)

        pz = np.where(has_art, np.where(syn, np.where(vidx == 0, 0.04, 0.30), 0.012), 0.50)
        pz = np.where(typo, np.maximum(pz, 0.55), pz)
        pz = np.where(in_reg, np.minimum(pz * 2.0 + 0.04, 0.95), pz)
        zero = rng.random(n) < pz
        n_res = np.clip(np.round(np.exp(rng.normal(2.4, 0.8, n))) + 1, 1, 500)
        n_res = np.where(has_art, n_res, np.maximum(1, np.round(n_res * 0.4)))
        n_res = np.where(zero, 0, n_res).astype(int)

        clicked = (~zero) & (rng.random(n) < np.clip(0.10 + 0.85 * r, 0, 0.97))
        pos = np.minimum(rng.geometric(np.clip(0.25 + 0.6 * r, 0.2, 0.9)), np.maximum(n_res, 1))
        pos = np.where(clicked, np.minimum(pos, 20), 0)

        art = np.full(n, -1)
        m = clicked & has_art
        for t in np.unique(top[m]):
            idx = np.where(m & (top == t))[0]
            ids = art_by_topic[t]
            w = art_q[ids]
            art[idx] = rng.choice(ids, size=len(idx), p=w / w.sum())
        m2 = np.where(clicked & ~has_art)[0]
        for a in np.unique(t_area[top[m2]]):
            idx = m2[t_area[top[m2]] == a]
            p_ = pool[a] if len(pool[a]) and AREAS[a] != WORKFLOW else global_pool
            art[idx] = rng.choice(p_, size=len(idx))
        qa = np.where(has_art & (art >= 0), art_q[np.maximum(art, 0)], 0.25)

        p_res = np.clip(0.08 + 0.9 * (0.4 * r + 0.6 * qa) - 0.05 * np.maximum(pos - 1, 0), 0.02, 0.95)
        resolved = clicked & (rng.random(n) < p_res)

        base = np.where(is_agent, 5.5, 9.0)
        speed = np.where(is_agent, 1.5 - 0.8 * sk, 1.0)
        med = base * (1.7 - 0.9 * r) * speed * np.where(in_reg, 1.45, 1.0) * (1 + 0.08 * np.maximum(pos - 1, 0))
        ttfc = np.clip(med * np.exp(rng.normal(0, 0.55, n)), 0.6, 180)
        ttfc = np.where(clicked, ttfc, np.nan)
        lat = 160 * np.exp(rng.normal(0, 0.35, n)) * np.where(in_reg, 2.8, 1.0)
        lat = lat * np.where(rng.random(n) < 0.008, 6.0, 1.0)

        p_ref = np.where(is_agent, 0.50 + 0.35 * sk, np.where(clicked, 0.55, 0.60)) * (0.85 ** rnd)
        cont = (~resolved) & (rng.random(n) < p_ref) & (rnd < 4)
        nxt = ts + np.where(clicked, np.nan_to_num(ttfc), 5.0) + rng.exponential(25, n) + 4
        cur_ts[active[cont]] = nxt[cont]

        chunks.append(pd.DataFrame(dict(
            sess_idx=active, ts=ts, round=rnd + 1, topic_id=top, query=query, n_results=n_res,
            zero_result=zero, clicked=clicked, click_position=np.where(clicked, pos, np.nan),
            clicked_article_idx=np.where(clicked, art, -1), time_to_first_click_s=np.round(ttfc, 1),
            latency_ms=np.round(lat).astype(int), resolved=resolved, reformulated=cont)))
        active = active[cont]
    return pd.concat(chunks, ignore_index=True)


# --------------------------------------------------------------------------------------
# assemble
# --------------------------------------------------------------------------------------
def generate(seed: int = 42, scale: float = 1.0) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    topics = build_topics()
    articles = build_articles(rng, topics)
    agents = build_agents(rng)
    days = day_table()
    sess, cases = make_sessions(rng, topics, agents, days, scale)
    s = simulate(rng, topics, articles, agents, sess)

    # ---- searches
    s = s.sort_values(["ts", "sess_idx", "round"]).reset_index(drop=True)
    sm = sess.loc[s["sess_idx"]].reset_index(drop=True)
    s["search_id"] = [f"Q-{i + 1:07d}" for i in range(len(s))]
    s["session_id"] = ["S-" + f"{i + 1:06d}" for i in s["sess_idx"]]
    s["user_type"], s["channel"] = sm["user_type"], sm["channel"]
    s["agent_id"] = np.where(sm["agent_idx"] >= 0, agents["agent_id"].values[np.maximum(sm["agent_idx"], 0)], None)
    s["case_id"] = np.where(sm["case_idx"] >= 0, "C-" + (sm["case_idx"] + 1).astype(str).str.zfill(6), None)
    s["product_area"] = topics["area"].values[s["topic_id"]]
    s["topic"] = topics["topic"].values[s["topic_id"]]
    s["clicked_article_id"] = np.where(s["clicked_article_idx"] >= 0,
                                       articles["article_id"].values[np.maximum(s["clicked_article_idx"], 0)], None)
    s["timestamp"] = pd.to_datetime(s["ts"], unit="s").dt.floor("s")

    # ---- sessions
    g = s.groupby("sess_idx")
    ses = pd.DataFrame(dict(n_searches=g.size(), resolved=g["resolved"].max(),
                            first_ts=g["ts"].min(), last_ts=g["ts"].max(),
                            last_ttfc=g["time_to_first_click_s"].last())).reset_index()
    ses = ses.merge(sess.reset_index().rename(columns={"index": "sess_idx"})[
        ["sess_idx", "user_type", "channel", "agent_idx", "case_idx", "topic_id"]], on="sess_idx")
    ses["session_id"] = ["S-" + f"{i + 1:06d}" for i in ses["sess_idx"]]
    ses["product_area"] = topics["area"].values[ses["topic_id"]]
    ses["topic"] = topics["topic"].values[ses["topic_id"]]
    ses["agent_id"] = np.where(ses["agent_idx"] >= 0, agents["agent_id"].values[np.maximum(ses["agent_idx"], 0)], None)
    ses["case_id"] = np.where(ses["case_idx"] >= 0, "C-" + (ses["case_idx"] + 1).astype(str).str.zfill(6), None)
    p_case = np.where(ses["resolved"], 0.02, 0.36 * np.where(ses["product_area"] == "Billing & Invoices", 1.4, 1.0))
    ses["case_created"] = (ses["user_type"] == "Customer") & (rng.random(len(ses)) < p_case)
    ses["duration_s"] = np.round(ses["last_ts"] - ses["first_ts"] + np.nan_to_num(ses["last_ttfc"], nan=6)).astype(int)
    ses["start_time"] = pd.to_datetime(ses["first_ts"], unit="s").dt.floor("s")

    # ---- cases
    cs = ses[ses["case_idx"] >= 0].groupby("case_idx").agg(
        case_searches=("n_searches", "sum"), found=("resolved", "max"), last=("last_ts", "max"))
    cases = cases.join(cs).fillna({"case_searches": 0, "found": False})
    cases["found"] = cases["found"].astype(bool)
    skill = agents["skill"].values[cases["agent_idx"]]
    base_h = cases["priority"].map({"P1": 4, "P2": 10, "P3": 26, "P4": 52}).values
    cx = topics["area"].map(AREA_COMPLEXITY).values[cases["topic_id"]]
    hours = base_h * cx * (1 + 0.32 * (~cases["found"]) + 0.06 * np.minimum(np.maximum(cases["case_searches"] - 1, 0), 5)) \
        * (1.25 - 0.5 * skill) * np.exp(rng.normal(0, 0.45, len(cases)))
    cases["resolution_hours"] = np.round(np.clip(hours, 0.3, 400), 1)
    created = cases["created"].values
    resolved_sec = np.maximum(created + cases["resolution_hours"] * 3600, cases["last"].fillna(0) + 120)
    esc = np.array([ESCALATION_BASE[t] for t in cases["team"]]) + 0.14 * (~cases["found"]) + 0.02 * (cases["priority"] == "P1")
    cases["escalated"] = rng.random(len(cases)) < np.clip(esc, 0, 0.9)
    cases["reopened"] = rng.random(len(cases)) < (0.04 + 0.05 * (~cases["found"]))
    fr = cases["priority"].map({"P1": 6, "P2": 18, "P3": 55, "P4": 140}).values * (1.2 - 0.4 * skill)
    cases["first_response_min"] = np.round(np.clip(fr * np.exp(rng.normal(0, 0.5, len(cases))), 1, 2000), 0).astype(int)
    csat = np.clip(np.round(rng.normal(4.25 - 0.6 * (~cases["found"]) - 0.5 * cases["escalated"]
                                       - 0.25 * (cases["resolution_hours"] > base_h * cx * 1.6), 0.8)), 1, 5)
    cases["csat"] = np.where(rng.random(len(cases)) < 0.38, csat, np.nan)

    # ---- tables out
    out_cases = pd.DataFrame(dict(
        case_id=["C-" + f"{i + 1:06d}" for i in cases.index],
        created_at=pd.to_datetime(cases["created"], unit="s").dt.floor("s"),
        resolved_at=pd.to_datetime(resolved_sec, unit="s").dt.floor("s"),
        agent_id=agents["agent_id"].values[cases["agent_idx"]], team=cases["team"],
        product_area=topics["area"].values[cases["topic_id"]], priority=cases["priority"],
        channel=cases["channel"], first_response_min=cases["first_response_min"],
        resolution_hours=cases["resolution_hours"], escalated=cases["escalated"],
        reopened=cases["reopened"], csat=cases["csat"]))
    out_ses = ses[["session_id", "start_time", "user_type", "channel", "agent_id", "case_id", "product_area",
                   "topic", "n_searches", "resolved", "case_created", "duration_s"]].sort_values("start_time")
    out_s = s[["search_id", "session_id", "timestamp", "round", "user_type", "channel", "agent_id", "case_id",
               "product_area", "topic", "query", "n_results", "zero_result", "clicked", "click_position",
               "clicked_article_id", "time_to_first_click_s", "latency_ms", "resolved", "reformulated"]]

    clicks = s["clicked_article_idx"][s["clicked_article_idx"] >= 0].value_counts()
    a = articles.copy()
    a["clicks_seed"] = a.index.map(clicks).fillna(0).astype(int)
    votes = rng.binomial(a["clicks_seed"], 0.06)
    a["helpful_votes"] = rng.binomial(votes, np.clip(0.25 + 0.65 * a["quality"], 0, 1))
    a["unhelpful_votes"] = votes - a["helpful_votes"]
    out_a = a.drop(columns=["quality", "clicks_seed"])
    out_ag = agents[["agent_id", "name", "team", "tenure_months", "region"]]
    events = pd.DataFrame([
        ("2026-06-09", "2026-06-12", "Mobile 4.2 crash spike", "Incident"),
        ("2026-07-21", "2026-07-27", "Search index migration", "Incident"),
        ("2026-08-17", "2026-08-17", "Workflow launch", "Release"),
        ("2026-09-08", "2026-09-08", "Workflow docs live", "Content"),
    ], columns=["start", "end", "label", "kind"])
    return dict(agents=out_ag, articles=out_a, cases=out_cases, sessions=out_ses, searches=out_s, events=events)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--scale", type=float, default=1.0, help="volume multiplier (0.3 = lighter)")
    args = ap.parse_args()
    tables = generate(args.seed, args.scale)
    os.makedirs(args.out, exist_ok=True)
    for name, df in tables.items():
        path = os.path.join(args.out, f"{name}.csv.gz")
        df.to_csv(path, index=False, compression="gzip")
        print(f"{name:9s} {len(df):>9,} rows  -> {path}")


if __name__ == "__main__":
    main()
