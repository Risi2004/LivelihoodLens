# Reference data

Hand-maintained tables, committed to git. Open them in a text editor: Excel can turn hours values such as `10-20` into dates.

## categories.csv
The 12 business categories from `CLAUDE.md`. `skills` and `price_inputs` are `|`-separated.

## osm_category_map.csv
Maps an OpenStreetMap tag to a category. Each `osm_key,osm_value` pair appears once, and tags not listed here are left out of the supply count.

- Some values are rare or non-standard tags (such as `shop=fish`) kept so local mapping habits are still caught.
- `shop=mobile_phone`, `electronics` and `computer` mostly sell goods rather than repair them. They count as supply for `electronics_repair` because few repair shops are tagged separately.
- `shop=clothes` counts as tailoring supply because the category covers tailoring and clothing.
- Footwear, jewellery and furniture are left out. `hies_item_map.csv` must treat those items the same way, so demand and supply cover the same goods.
- Generic tags such as `shop=yes` and `shop=repair` are left out because they don't identify a category.

## startup_costs.csv
Placeholder estimates, marked `team estimate - verify`. Replace each row and its `source` when a real figure is found. Only tailoring, beauty and bakery ranges come from the proposal, and those are estimates too.

## district_neighbours.csv
Districts sharing a land border, with one row in each direction. Used for refusal suggestions. Derived from the geoBoundaries gbOpen LKA ADM2 polygons (ODbL): a pair is kept if the shared border is about 2 km or more, so a corner touch doesn't count. That rule drops one pair, Jaffna and Mullaitivu.
