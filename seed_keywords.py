"""
트렌드 탐지 시드 키워드 — 자체 포함 데이터.

매일 이 키워드들의 Google Trends 변화를 측정하고,
급상승 키워드와 관련된 Amazon/Etsy 상품을 발굴합니다.

카테고리별 영문 키워드 (Google Trends는 영어 검색량이 더 풍부).
"""

# 카테고리별 시드 키워드 — 행동경제학적으로 충동구매·감성소비 가능한 영역 중심
SEED_KEYWORDS = {
    "beauty_tools": [
        "magnetic lashes", "ice roller", "gua sha", "scalp massager",
        "lip mask", "led face mask", "silicone cleanser", "lash serum",
        "hair removal device", "dermaplaning tool",
    ],
    "kitchen_aesthetic": [
        "matcha whisk set", "mushroom diffuser", "ceramic kettle",
        "minimalist kitchen", "japanese knife", "wooden cutting board",
        "stoneware mug", "matte black dishes", "linen apron",
        "vintage glass pitcher",
    ],
    "home_mood": [
        "sunset lamp", "mushroom lamp", "cloud lamp", "moon lamp",
        "diffuser aesthetic", "wall tapestry", "reed diffuser",
        "scented candle gift", "led strip aesthetic", "neon sign room",
    ],
    "wellness_self_care": [
        "weighted blanket", "silk pillowcase", "eye mask heated",
        "shower steamer", "bath salts gift", "mouth tape sleep",
        "magnesium spray", "red light therapy", "pillow spray",
        "journal aesthetic",
    ],
    "tech_lifestyle": [
        "phone stand desk", "ring light selfie", "mini projector",
        "portable blender", "wireless charger stand", "key finder",
        "smart notebook", "magnetic phone wallet", "earbuds case cute",
        "polaroid printer",
    ],
    "pet_premium": [
        "cat water fountain", "dog calming bed", "pet camera treat",
        "slow feeder dog", "cat tree modern", "pet grooming glove",
        "dog snuffle mat", "automatic litter box",
    ],
    "fashion_accessory": [
        "claw clip large", "magnetic necklace", "satin scrunchie",
        "pearl headband", "ribbon bow hair", "stackable rings",
        "tennis bracelet", "heart pendant",
    ],
    "stationery_korean_mz": [
        "sticker book", "washi tape aesthetic", "fountain pen ink",
        "bullet journal supplies", "highlighter pastel", "memo pad cute",
        "planner stickers", "pen case canvas",
    ],
    "kids_gift": [
        "sensory bin", "fidget toy desk", "kinetic sand",
        "magnetic blocks", "wooden toys aesthetic", "play dough natural",
        "stacking rings", "balance board kids",
    ],
    "travel_organize": [
        "packing cubes", "passport holder cute", "neck pillow memory",
        "shoe bag travel", "cosmetic bag clear", "tech organizer",
        "luggage tag aesthetic", "compression socks flight",
    ],
}


def get_all_keywords() -> list[str]:
    """모든 시드 키워드를 평탄하게 반환."""
    out = []
    for cat_keywords in SEED_KEYWORDS.values():
        out.extend(cat_keywords)
    return out


def get_keywords_by_category(category: str) -> list[str]:
    """특정 카테고리의 키워드만 반환."""
    return SEED_KEYWORDS.get(category, [])


def get_category_for_keyword(keyword: str) -> str:
    """키워드가 속한 카테고리 찾기."""
    for cat, kws in SEED_KEYWORDS.items():
        if keyword in kws:
            return cat
    return "unknown"


# 행동경제학·치알디니 요소가 강한 카테고리 (가산점)
HIGH_EMOTION_CATEGORIES = {
    "beauty_tools",       # 자기 표현 욕구
    "home_mood",          # 감정 소비, 호감
    "wellness_self_care", # 자기 보상
    "stationery_korean_mz", # 수집 욕구
}
