"""Orchestrates scoring, filters, pressure, confidence and explanations into one response."""
from app import config
from app.engine.confidence import card_confidence, data_too_stale, page_confidence, source_freshness
from app.engine.explain import cost_pressure_warning, explain_row, insufficient_data_reason
from app.engine.filters import apply_user_filters, skill_excluded_rows
from app.engine.pressure import cost_pressure, no_pressure_signal
from app.engine.scoring import compute_gap_table, coverage_table

BUDGET_FIT_LABELS = {"fits": "Fits your budget", "lower_end": "Lower end fits your budget"}
OTHER_OPTION_LABEL = "Needs a skill you didn't select"


def _adequate_districts(coverage):
    return coverage.loc[coverage["coverage_flag"] == "adequate", "district"].tolist()


def _suggestions(store, district, adequate):
    neighbours = store.district_neighbours
    names = neighbours.loc[neighbours["district"] == district, "neighbour"]
    return sorted(name for name in names if name in adequate)


def _refusal(store, district, coverage_row, failed_rule, threshold, suggestions, freshness):
    reason = insufficient_data_reason(
        district,
        failed_rule,
        float(coverage_row["per_10k"]),
        threshold,
        int(coverage_row["total_businesses"]),
        int(coverage_row["population"]),
        freshness["osm"]["age_days"],
        coverage_row["coverage_flag"],
    )
    return {
        "status": "insufficient_data",
        "district": district,
        "reason": reason,
        "per_10k": round(float(coverage_row["per_10k"]), 2),
        "failed_rule": failed_rule,
        "min_required": threshold,
        "suggestions": suggestions,
        "freshness": freshness,
    }


def _shared_fields(row):
    return {
        "category_id": row["category_id"],
        "label": row["label"],
        "gap_score": int(row["gap_score"]),
        "cost_min_lkr": int(row["cost_min_lkr"]),
        "cost_max_lkr": int(row["cost_max_lkr"]),
        "budget_fit": row["budget_fit"],
        "budget_fit_label": BUDGET_FIT_LABELS[row["budget_fit"]],
    }


def _result_card(row, district, n_categories, prices, freshness, today):
    if freshness["prices"]["stale"] and row["price_inputs"]:
        pressure = no_pressure_signal(stale=True)
    else:
        pressure = cost_pressure(row, prices, today)
    return {
        **_shared_fields(row),
        "gap_ratio": float(row["gap_ratio"]),
        "demand_share": float(row["demand_share"]),
        "supply_share": float(row["supply_share"]),
        "saturated": bool(row["saturated"]),
        "why": explain_row({**row, "district": district, "n_categories": n_categories}),
        "cost_pressure": {
            **pressure,
            "message": cost_pressure_warning(pressure["pct_change"]) if pressure["warning"] else None,
        },
        "confidence": card_confidence(freshness, bool(row["price_inputs"]), row["supply_visibility"]),
    }


def _other_option(row):
    return {**_shared_fields(row), "needs_skills": row["needs_skills"], "note": OTHER_OPTION_LABEL}


def _message(n_results, n_other):
    if n_results >= config.TOP_N_RESULTS:
        return None
    if n_results > 0:
        kind = "business type matches" if n_results == 1 else "business types match"
        return f"{n_results} {kind} your budget, skills and hours. Adding a skill could show more."
    if n_other > 0:
        return (
            "No business type matches your skills at this budget and these hours. "
            "The options below need a skill you didn't select."
        )
    return "No business type matches your answers yet. Try adding skills, raising your budget, or adding hours."


def recommend(store, district, budget, skills, hours, today):
    coverage = coverage_table(store.district_totals, store.population)
    matches = coverage[coverage["district"] == district]
    if matches.empty:
        raise ValueError(f"Unknown district: {district}")
    coverage_row = matches.iloc[0]

    freshness = source_freshness(store.sources, today)
    adequate = _adequate_districts(coverage)
    if coverage_row["coverage_flag"] != "adequate":
        suggestions = _suggestions(store, district, adequate)
        return _refusal(store, district, coverage_row, coverage_row["failed_rule"], coverage_row["threshold"], suggestions, freshness)
    if data_too_stale(freshness):
        # Staleness applies to every district, so no neighbour would rank either.
        return _refusal(store, district, coverage_row, "stale_data", None, [], freshness)

    gap_table = compute_gap_table(store.supply, store.demand, adequate)
    gap_rows = gap_table[gap_table["district"] == district]
    args = (gap_rows, store.categories, store.startup_costs, budget, skills, hours)
    n_categories = len(store.categories)

    top = apply_user_filters(*args).head(config.TOP_N_RESULTS).to_dict("records")
    results = [_result_card(r, district, n_categories, store.prices, freshness, today) for r in top]

    open_places = config.TOP_N_RESULTS - len(results)
    other = skill_excluded_rows(*args).head(open_places).to_dict("records")
    other_options = [_other_option(r) for r in other]

    return {
        "status": "ok",
        "district": district,
        "profile": {"budget_lkr": budget, "skills": list(skills), "hours": hours},
        "confidence": page_confidence(results),
        "results": results,
        "other_options": other_options,
        "message": _message(len(results), len(other_options)),
        "freshness": freshness,
        "disclaimer": config.DISCLAIMER,
    }
