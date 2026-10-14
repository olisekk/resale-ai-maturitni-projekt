"""
products/ai_engine.py
Private AI listing generation logic — includes condition, eBay verdict.
"""
import random

HIGH_DEMAND_KEYWORDS = [
    "sneaker", "jordan", "nike", "adidas", "yeezy", "dunk",
    "vintage", "streetwear", "supreme", "bape", "palace",
    "off-white", "travis", "retro", "collab", "limited",
]

CONDITION_COPY = {
    "New":       "Nové zboží s původními štítky.",
    "Like New":  "Téměř nepoužité, s minimálními známkami opotřebení.",
    "Very Good": "Velmi dobrý stav s drobnými známkami používání.",
    "Good":      "Dobrý použitý stav s běžnými známkami opotřebení.",
    "Fair":      "Používané, ale funkční; stav odpovídá popisu.",
}

CONDITION_PRICE_MULTIPLIER = {
    "New":       1.0,
    "Like New":  0.92,
    "Very Good": 0.80,
    "Good":      0.65,
    "Fair":      0.45,
}

CATEGORY_HOOKS = {
    "Sneakers":        "Tenisky pro zájemce o značkovou obuv z druhé ruky.",
    "Streetwear":      "Streetwearový kousek pro fanoušky současné módy.",
    "Vintage":         "Vintage kousek se specifickým stylem a původem.",
    "Fashion":         "Módní kousek vhodný pro další nošení.",
    "Electronics":     "Elektronika, u které je dobré uvést funkčnost a příslušenství.",
    "Gaming":          "Herní vybavení pro dalšího hráče.",
    "Watches":         "Hodinky; v popisu uveď značku, funkčnost a případné příslušenství.",
    "Collectibles":    "Sběratelský předmět s důrazem na stav a úplnost.",
    "Sports":          "Sportovní vybavení připravené k dalšímu použití.",
    "Home & Lifestyle":"Vybavení do domácnosti pro další využití.",
}


def calculate_demand_score(product_name: str, category: str) -> str:
    """Určí orientační úroveň zájmu podle názvu a kategorie položky."""
    combined = (product_name + " " + category).lower()
    for kw in HIGH_DEMAND_KEYWORDS:
        if kw in combined:
            return "High"
    return "Medium"


def calculate_estimated_price(
    original_price: int,
    condition: str,
    description: str = "",
    ebay_avg: int | None = None,
    ebay_lowest: int | None = None,
    ebay_highest: int | None = None,
) -> int:
    """Odhadne cenu podle stavu; dostupné aktivní nabídky eBay mají přednost."""
    premium_words = ("rare", "limited", "collector", "mint", "authentic", "deadstock", "vintage", "box", "sealed")
    description_text = (description or "").lower()
    premium_boost = 1.03 if any(word in description_text for word in premium_words) else 1.0

    if ebay_avg:
        market_floor = max(1, ebay_lowest or int(ebay_avg * 0.9))
        market_ceiling = max(market_floor + 1, ebay_highest or int(ebay_avg * 1.1))

        condition_adjustment = {
            "New": 1.02,
            "Like New": 1.00,
            "Very Good": 0.97,
            "Good": 0.93,
            "Fair": 0.87,
        }.get(condition, 0.93)

        estimate = int(round(ebay_avg * condition_adjustment * premium_boost))
        # Výsledek držíme v rozsahu pozorovaných nabídkových cen.
        return max(market_floor, min(market_ceiling, estimate))

    multiplier = CONDITION_PRICE_MULTIPLIER.get(condition, 0.7)
    base = original_price * multiplier
    margin = random.randint(8, 35)
    estimate = int(round(base + margin))
    if premium_boost > 1:
        estimate = int(round(estimate * premium_boost))
    return max(estimate, original_price + 5)


def generate_title(product_name: str, demand_score: str, condition: str) -> str:
    """Sestaví návrh titulku z názvu, stavu a orientační poptávky."""
    cond_short = {
        "New":       "Brand New",
        "Like New":  "Like New",
        "Very Good": "Very Good",
        "Good":      "Good Condition",
        "Fair":      "Fair Condition",
    }.get(condition, condition)

    if demand_score == "High":
        suffixes = [
            f"| {cond_short} – vysoký zájem",
            f"| {cond_short} – připraveno k prodeji",
            f"| {cond_short} – žádaný kousek",
        ]
    else:
        suffixes = [
            f"| {cond_short} – připraveno k prodeji",
            f"| {cond_short} – rychlé odeslání",
            f"| {cond_short} – dobrý stav",
        ]
    return f"{product_name} {random.choice(suffixes)}"


def generate_description(
    product_name: str,
    category: str,
    condition: str,
    demand_score: str,
    estimated_price: int,
    original_price: int,
) -> str:
    """Vytvoří upravitelný návrh popisu nabídky."""
    hook        = CATEGORY_HOOKS.get(category, "Quality item with solid resale potential.")
    cond_copy   = CONDITION_COPY.get(condition, "Used condition.")
    margin      = estimated_price - original_price
    tag         = category.lower().replace(" ", "").replace("&", "")
    demand_tip  = (
        "Orientační signál poptávky je vysoký. Před vystavením porovnej cenu s aktuální nabídkou."
        if demand_score == "High"
        else "Před vystavením porovnej cenu a stav s podobnými nabídkami."
    )

    return (
        f"{hook}\n\n"
        f"📦 Condition: {cond_copy}\n\n"
        f"• Orientační signál poptávky: {demand_score}\n"
        f"• Odhadovaná cena: {estimated_price} € (rozdíl před poplatky: {margin} €)\n"
        f"• Text uprav podle pravidel zvolené platformy\n\n"
        f"{demand_tip}\n\n"
        f"#resale #{tag} #secondhand #resaleai"
    )


def generate_price_verdict(
    original_price: int,
    estimated_price: int,
    ebay_avg: int | None,
) -> tuple[str, str]:
    """Porovná odhad s aktivními cenami eBay nebo vysvětlí jejich nedostupnost."""
    if ebay_avg:
        diff = ebay_avg - estimated_price
        pct  = round((diff / ebay_avg) * 100) if ebay_avg else 0

        if diff >= 10:
            return (
                "great",
                f"Orientační cena je pod průměrnou cenou aktivních nabídek eBay ({ebay_avg} €) "
                f"o přibližně {abs(pct)} %. Jde o nabídkové, nikoli dokončené prodeje."
            )
        elif diff >= -15:
            return (
                "fair",
                f"Orientační cena je blízko průměrné ceně aktivních nabídek eBay ({ebay_avg} €). "
                f"Jde o nabídkové, nikoli dokončené prodeje."
            )
        else:
            return (
                "high",
                f"Orientační cena je nad průměrnou cenou aktivních nabídek eBay ({ebay_avg} €) "
                f"o přibližně {abs(pct)} %. Zvaž porovnání stavu a příslušenství."
            )
    else:
        margin_pct = round(((estimated_price - original_price) / original_price) * 100) if original_price else 0
        return (
            "unknown",
            f"Nejsou dostupné ceny aktivních nabídek eBay. Odhad vychází pouze ze stavu a pořizovací ceny; "
            f"rozdíl proti pořizovací ceně je {margin_pct} % před poplatky."
        )


def run_ai_generation(
    product_name: str,
    category: str,
    condition: str,
    original_price: int,
    ebay_avg: int | None = None,
    ebay_lowest: int | None = None,
    ebay_highest: int | None = None,
    description: str = "",
) -> dict:
    """Spustí lokální cenový odhad a sestaví návrh titulku, textu i verdiktu."""
    demand_score           = calculate_demand_score(product_name, category)
    estimated_resale_price = calculate_estimated_price(
        original_price,
        condition,
        description=description,
        ebay_avg=ebay_avg,
        ebay_lowest=ebay_lowest,
        ebay_highest=ebay_highest,
    )
    ai_title               = generate_title(product_name, demand_score, condition)
    ai_description         = generate_description(
        product_name, category, condition,
        demand_score, estimated_resale_price, original_price,
    )
    verdict_key, verdict_message = generate_price_verdict(
        original_price, estimated_resale_price, ebay_avg,
    )

    return {
        "demand_score":           demand_score,
        "estimated_resale_price": estimated_resale_price,
        "ai_title":               ai_title,
        "ai_description":         ai_description,
        "price_verdict":          verdict_key,
        "verdict_message":        verdict_message,
    }
