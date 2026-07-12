import json

INPUT_FILE = "data.json"
OUTPUT_FILE = "cleaneddata.json"

# Rankings to keep for the MU
MU_RANKINGS = [
    "muWeeklyDamages",
    "muBounty",
    "muReputation",
    "muDamages"
]

# Rankings to keep for members
MEMBER_RANKINGS = [
    "userDamages",
    "weeklyUserDamages",
    "userWealth",
    "userBounty"
]


def normalize_input(data):
    """
    Accepts either the new multi-MU shape:
        { "metadata": {...}, "mus": [ { "mu": {...}, "members": [...] }, ... ] }
    or the old single-MU shape:
        { "metadata": {...}, "mu": {...}, "members": [...] }
    and always returns a list of { "mu": ..., "members": ... } entries.
    """
    if "mus" in data:
        return data["mus"]
    if "mu" in data:
        return [{"mu": data.get("mu", {}), "members": data.get("members", [])}]
    return []


def clean_mu_entry(entry):
    mu = entry.get("mu", {}) or {}
    members = entry.get("members", []) or []

    cleaned = {
        # "_id" is WarEra's stable identifier for the MU. Keep it so we can
        # match this MU across weeks even if it gets renamed.
        "id": mu.get("_id"),
        "name": mu.get("name"),
        "avatarUrl": mu.get("avatarUrl"),
        "rankings": {}
    }

    mu_rankings = mu.get("rankings", {}) or {}
    for ranking in MU_RANKINGS:
        if ranking in mu_rankings:
            cleaned["rankings"][ranking] = mu_rankings[ranking]

    cleaned_members = []
    for member in members:
        member_clean = {
            # Stable player identifier: use this (not username) whenever
            # matching the same player across different fetches/weeks,
            # since usernames can change.
            "id": member.get("_id"),
            "username": member.get("username"),
            "avatarUrl": member.get("avatarUrl"),
            "level": member.get("leveling", {}).get("level"),
            "rankings": {}
        }

        member_rankings = member.get("rankings", {}) or {}
        for ranking in MEMBER_RANKINGS:
            if ranking in member_rankings:
                member_clean["rankings"][ranking] = member_rankings[ranking]

        cleaned_members.append(member_clean)

    cleaned["members"] = cleaned_members
    return cleaned


def clean_data(data):
    entries = normalize_input(data)
    return {
        "mus": [clean_mu_entry(entry) for entry in entries]
    }


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned_data = clean_data(data)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

    mu_count = len(cleaned_data["mus"])
    print(f"Cleaned data for {mu_count} MU(s) saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
