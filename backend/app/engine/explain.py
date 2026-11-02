"""Template-based plain-language reasons. Every number comes from the values passed in."""
from app import config


def _percent(share):
    """"about 5%", or "almost none" when it would round to 0."""
    rounded = round(share * 100)
    return f"about {rounded}%" if rounded > 0 else "almost none"


def _share_sentence(row):
    label = row["label"].lower()
    supply = _percent(row["supply_share"])
    if row["supply_share"] < row["demand_share"] and supply != "almost none":
        supply = f"only {supply}"
    return (
        f"In {row['district']}, {label} businesses make up {supply} of mapped businesses, "
        f"while this category takes {_percent(row['demand_share'])} of household spending "
        f"across these {row['n_categories']} business types."
    )


def strong_gap_reason(row):
    return f"{_share_sentence(row)} That puts it among the strongest gaps in your area."


def moderate_gap_reason(row):
    return f"{_share_sentence(row)} Household spending is somewhat above what local supply suggests."


def saturated_reason(row):
    return f"{_share_sentence(row)} On the map, many businesses already serve this; the market may be crowded."


def low_visibility_reason(row):
    crowded = " and, on the map, many businesses already serve this; the market may be crowded" if row["saturated"] else ""
    return (
        f"{_share_sentence(row)} OpenStreetMap rarely maps this kind of business, such as home tuition, "
        f"so confidence is low{crowded}."
    )


def explain_row(row):
    """row needs district, label, n_categories, supply_share, demand_share, gap_score, saturated, supply_visibility."""
    if row["supply_visibility"] == "low":
        return low_visibility_reason(row)
    if row["saturated"]:
        return saturated_reason(row)
    if row["gap_score"] >= config.STRONG_GAP_SCORE:
        return strong_gap_reason(row)
    return moderate_gap_reason(row)


def cost_pressure_warning(pct_change):
    return f"Input prices have risen about {round(pct_change * 100)}% over the last three months, so margins may shrink."


def insufficient_data_reason(
    district, failed_rule, per_10k, threshold, total_businesses, population, osm_age_days=None, coverage_flag="insufficient"
):
    if failed_rule == "stale_data":
        age = f"Business data is {osm_age_days} days old and price data is also out of date" if osm_age_days is not None else "Business and price data are out of date"
        return f"We can't rank {district} right now. {age}, so we won't guess."
    opening = "Business mapping here is still incomplete, so we can't rank it yet. " if coverage_flag == "low" else ""
    mapped = f"{opening}Only about {total_businesses:,} businesses are mapped in {district} for roughly {population:,} people"
    if failed_rule == "total_businesses":
        return f"{mapped}, and we need at least {threshold:,} to compare supply with what households spend, so we won't guess."
    return (
        f"{mapped}. That is about {per_10k:.1f} per ten thousand people, and we need at least {threshold} "
        "to compare supply with what households spend, so we won't guess."
    )
