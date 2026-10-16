import csv
import json
import random
from pathlib import Path
from urllib.parse import quote_plus


OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs" / "candidate_dataset"
SEED = 20260619
COUNT = 500


FIRST_NAMES = [
    "Alex",
    "Maya",
    "Lina",
    "Ethan",
    "Sofia",
    "Noah",
    "Iris",
    "Victor",
    "Ava",
    "Leo",
    "Nina",
    "Owen",
    "Chloe",
    "Mason",
    "Zara",
    "Ravi",
    "Anika",
    "Hao",
    "Mei",
    "Yuki",
    "Kenji",
    "Elena",
    "Mateo",
    "Amara",
    "Daniel",
    "Priya",
    "Arjun",
    "Grace",
    "Mila",
    "Theo",
]
LAST_NAMES = [
    "Chen",
    "Wang",
    "Zhang",
    "Li",
    "Singh",
    "Patel",
    "Kim",
    "Park",
    "Tanaka",
    "Sato",
    "Garcia",
    "Martinez",
    "Nguyen",
    "Tran",
    "Smith",
    "Johnson",
    "Brown",
    "Wilson",
    "Miller",
    "Davis",
    "Khan",
    "Rahman",
    "Ivanov",
    "Petrova",
    "Silva",
]

COMPANIES = [
    ("OpenAI", "AI Foundation Model", "https://openai.com"),
    ("Google DeepMind", "AI Research", "https://deepmind.google"),
    ("Anthropic", "AI Foundation Model", "https://www.anthropic.com"),
    ("Meta GenAI", "AI Foundation Model", "https://ai.meta.com"),
    ("Microsoft AI", "AI Platform", "https://www.microsoft.com/ai"),
    ("NVIDIA AI", "AI Infrastructure", "https://www.nvidia.com"),
    ("Scale AI", "AI Data Platform", "https://scale.com"),
    ("Perplexity AI", "AI Search", "https://www.perplexity.ai"),
    ("Mistral AI", "AI Foundation Model", "https://mistral.ai"),
    ("Cohere", "Enterprise AI", "https://cohere.com"),
    ("xAI", "AI Foundation Model", "https://x.ai"),
    ("Databricks Mosaic", "Data AI Platform", "https://www.databricks.com"),
    ("ByteDance Seed", "AI Application", "https://www.bytedance.com"),
    ("Moonshot AI", "AI Application", "https://www.moonshot.cn"),
    ("MiniMax", "AI Application", "https://www.minimax.io"),
    ("Zhipu AI", "AI Foundation Model", "https://www.zhipuai.cn"),
]

ROLES = [
    ("Research Scientist", "Research", "LLM Reasoning"),
    ("Research Engineer", "Post-training", "LLM Post-training"),
    ("Senior Inference Engineer", "Infra", "Inference Infrastructure"),
    ("ML Systems Engineer", "Infra", "Distributed Training"),
    ("Agent Systems Engineer", "Agents", "AI Agents"),
    ("Data Engine Lead", "Data", "Data Engine"),
    ("RLHF Scientist", "Alignment", "RLHF"),
    ("Evaluation Engineer", "Evaluation", "Model Evaluation"),
    ("Product ML Lead", "Product AI", "AI Product"),
    ("Security Researcher", "Safety", "AI Safety"),
    ("Applied Scientist", "Applications", "Multimodal AI"),
    ("GPU Performance Engineer", "Infra", "GPU Optimization"),
]

LOCATIONS = [
    "San Francisco",
    "Palo Alto",
    "Seattle",
    "New York",
    "London",
    "Paris",
    "Berlin",
    "Toronto",
    "Beijing",
    "Shanghai",
    "Shenzhen",
    "Singapore",
    "Tokyo",
    "Seoul",
    "Bengaluru",
]

SIGNALS = [
    ("profile_activity", 16, "Recent public profile wording changed toward broader platform ownership."),
    ("research_silence", 14, "Public research or launch cadence appears quieter than prior period."),
    ("team_signal", 12, "Adjacent team hiring or org movement suggests possible role transition."),
    ("market_signal", 10, "Domain is in active market demand across AI labs and AI infra startups."),
    ("open_source_activity", 9, "Recent public code or technical writing aligns with strategic hiring needs."),
    ("conference_signal", 8, "Recent talk, paper, or panel indicates external visibility."),
    ("leadership_scope", 7, "Current role suggests leverage over roadmap, platform, or model quality."),
    ("location_fit", 5, "Location matches priority hiring hub or remote-friendly function."),
]


def weighted_choice(items: list[tuple[str, int, str]]) -> tuple[str, str]:
    total = sum(weight for _, weight, _ in items)
    pick = random.randint(1, total)
    running = 0
    for code, weight, text in items:
        running += weight
        if pick <= running:
            return code, text
    return items[-1][0], items[-1][2]


def risk_level(score: int) -> str:
    if score >= 85:
        return "very_high"
    if score >= 70:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def recommended_window(score: int) -> str:
    if score >= 85:
        return "within 7 days"
    if score >= 70:
        return "within 2 weeks"
    if score >= 50:
        return "within 1 month"
    return "monitor only"


def make_candidate(index: int, used_names: set[str]) -> dict[str, object]:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    name = f"{first} {last}"
    suffix = 2
    while name in used_names:
        name = f"{first} {last} {suffix}"
        suffix += 1
    used_names.add(name)

    company_name, industry, website = random.choice(COMPANIES)
    title, department, domain = random.choice(ROLES)
    location = random.choice(LOCATIONS)
    signal_count = random.choice([2, 2, 3, 3, 4])
    sampled = [weighted_choice(SIGNALS) for _ in range(signal_count)]
    reason_codes = []
    signal_texts = []
    for code, text in sampled:
        if code not in reason_codes:
            reason_codes.append(code)
            signal_texts.append(text)

    base = random.randint(38, 78)
    boost = sum(next(weight for c, weight, _ in SIGNALS if c == code) for code in reason_codes)
    risk_score = min(96, base + boost // 2 + random.randint(-4, 8))
    confidence_score = min(94, max(55, 58 + len(reason_codes) * 7 + random.randint(-6, 10)))
    level = risk_level(risk_score)
    query = f'{name} "{company_name}" "{title}" LinkedIn'
    search_url = f"https://www.google.com/search?q={quote_plus(query)}"

    profile_summary = (
        f"Synthetic public-signal profile for {name}, currently mapped to {title} "
        f"at {company_name}. Domain focus: {domain}. Key hiring signals: "
        + " ".join(signal_texts)
    )
    evidence_summary = (
        "Synthetic Google/LinkedIn-style search result note: "
        + " ".join(signal_texts)
        + " Human review required before outreach."
    )
    return {
        "candidate_uid": f"synth_{index:04d}",
        "name": name,
        "company_name": company_name,
        "industry": industry,
        "website": website,
        "title": title,
        "department": department,
        "location": location,
        "domain": domain,
        "profile_summary": profile_summary,
        "source_type": "synthetic_google_linkedin_search",
        "search_query": query,
        "source_url": search_url,
        "linkedin_public_signal": "synthetic_search_result_only",
        "evidence_title": f"Public search signal bundle for {name}",
        "evidence_summary": evidence_summary,
        "reason_codes": "|".join(reason_codes),
        "risk_score": risk_score,
        "confidence_score": confidence_score,
        "risk_level": level,
        "recommended_window": recommended_window(risk_score),
        "hunt_priority": "A" if risk_score >= 85 else "B" if risk_score >= 70 else "C",
        "recommended_action": (
            "add_to_pool_and_personalize_outreach"
            if risk_score >= 70
            else "monitor_and_collect_more_evidence"
        ),
        "compliance_note": (
            "Synthetic dataset for product testing. Do not treat as real personal data."
        ),
    }


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    random.seed(SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    used_names: set[str] = set()
    rows = [make_candidate(index, used_names) for index in range(1, COUNT + 1)]

    import_fields = [
        "name",
        "company_name",
        "industry",
        "website",
        "title",
        "department",
        "location",
        "domain",
        "profile_summary",
    ]
    full_fields = list(rows[0].keys())
    write_csv(OUTPUT_DIR / "talentnet_candidates_500_import.csv", rows, import_fields)
    write_csv(OUTPUT_DIR / "talentnet_candidates_500_full.csv", rows, full_fields)
    summary = {
        "count": len(rows),
        "risk_level_counts": {
            level: sum(1 for row in rows if row["risk_level"] == level)
            for level in ["very_high", "high", "medium", "low"]
        },
        "priority_counts": {
            priority: sum(1 for row in rows if row["hunt_priority"] == priority)
            for priority in ["A", "B", "C"]
        },
        "source": "synthetic_google_linkedin_style",
        "import_csv": "talentnet_candidates_500_import.csv",
        "full_csv": "talentnet_candidates_500_full.csv",
    }
    (OUTPUT_DIR / "dataset_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
