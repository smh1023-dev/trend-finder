"""
Claude API를 활용한 트렌드 상품 분석.

수집한 raw 데이터에서:
  1) 6단계 검증 통과 후보 5개 선정
  2) 각 후보별 상세 분석 (왜 뜨는가, 한국 경쟁, 타깃, 심리 분석)
  3) 행동경제학 + 치알디니 요소 매칭

전체 1번 호출(선정) + 5번 호출(상세) = 6번 API 호출.
일일 비용: Haiku 4.5 기준 약 $0.05~0.10
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

log = logging.getLogger(__name__)

MODEL_NAME = "claude-haiku-4-5"
MAX_TOKENS_SELECTION = 2000
MAX_TOKENS_DETAIL = 2000
TIMEOUT_SECONDS = 60


# ============================================================
#  Step 1. 후보 5개 선정
# ============================================================

SELECTION_PROMPT = """당신은 글로벌 이커머스 트렌드 분석가입니다.

아래 데이터를 분석하여 **한국 진입에 유리한 후보 상품 5개**를 선정하세요.

선정 기준 (6단계 검증):
1. 수요 증가 — 미국 검색량 momentum >= 1.2 (상승) 또는 Amazon Movers 등장
2. 한국 갭 — 한국 검색량(KR momentum) 낮거나 데이터 없음
3. 콘텐츠화 가능 — 시각적/스토리텔링 가능 카테고리
4. 저위험 — 소형/경량 추정, 2~5만원대 가능 추정
5. 심리 자극 — 행동경제학·치알디니 요소 2개 이상 활용 가능
6. 충동·반복 구매 가능 — 감성 소비/자기보상 영역

[수집 데이터]

미국 Google Trends (key: 키워드, value: momentum 1.0 초과 = 상승):
{us_trends}

한국 Google Trends (한국에서 얼마나 알려졌는지 — 낮을수록 갭):
{kr_trends}

Amazon Movers & Shakers (현재 급상승 상품):
{amazon}

Etsy 인기 상품 (감성 소비):
{etsy}

다음 JSON 형식으로만 답변하세요. 다른 텍스트 금지.

{{
  "candidates": [
    {{
      "product_name_ko": "한국어 제품명 (마케팅 친화적)",
      "product_name_en": "영문 제품명 (소싱용 키워드)",
      "category": "카테고리 (예: 뷰티툴, 홈무드, 펫프리미엄)",
      "trend_signal": "왜 이 상품을 선정했는가 한 줄 (구체적 데이터 인용)",
      "korea_gap_signal": "왜 한국에서 갭이 있는가 한 줄"
    }},
    ... 총 5개
  ]
}}

⚠️ 주의:
- 반드시 한국에서 아직 대중화되지 않은 것
- 흔한 카테고리(에어팟, 일반 다이어트 보조제 등) 금지
- 감성·자기보상·충동구매 가능한 영역 우선
- 시각적 후킹 강한 것 우선"""


def select_candidates(collected_data: dict, client) -> list[dict]:
    """Claude로 후보 5개 선정."""
    # 데이터를 LLM에 보내기 좋게 포맷
    us = collected_data.get('google_trends_us', {})
    kr = collected_data.get('google_trends_kr', {})

    # 상승 키워드만 (momentum >= 1.0)
    us_rising = {k: v['momentum'] for k, v in us.items() if v.get('momentum', 0) >= 0.8}
    us_str = "\n".join(f"  {k}: momentum={m}" for k, m in sorted(us_rising.items(), key=lambda x: -x[1])[:30])

    kr_str = "\n".join(f"  {k}: momentum={v['momentum']}" for k, v in kr.items() if v.get('momentum', 0) > 0)[:2000]
    if not kr_str:
        kr_str = "(한국 검색량 데이터 거의 없음 - 갭 가능성 큼)"

    amz = collected_data.get('amazon_movers', [])
    amz_str = "\n".join(f"  [{a['category']}] {a['title']}" for a in amz[:30])
    if not amz_str:
        amz_str = "(Amazon 데이터 수집 실패)"

    etsy = collected_data.get('etsy_bestsellers', [])
    etsy_str = "\n".join(f"  [{e['category']}] {e['title']}" for e in etsy[:20])
    if not etsy_str:
        etsy_str = "(Etsy 데이터 없음)"

    prompt = SELECTION_PROMPT.format(
        us_trends=us_str[:3000],
        kr_trends=kr_str[:1500],
        amazon=amz_str[:3000],
        etsy=etsy_str[:1500],
    )

    try:
        message = client.messages.create(
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS_SELECTION,
            messages=[{"role": "user", "content": prompt}],
            timeout=TIMEOUT_SECONDS,
        )
        text = message.content[0].text.strip()

        # JSON 추출
        if '```' in text:
            parts = text.split('```')
            for p in parts:
                p = p.strip()
                if p.startswith('json'):
                    p = p[4:].strip()
                if p.startswith('{'):
                    text = p
                    break
        if not text.startswith('{'):
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                text = text[start:end+1]

        data = json.loads(text)
        candidates = data.get('candidates', [])
        if not isinstance(candidates, list):
            return []

        # 5개로 자르기
        return candidates[:5]
    except Exception as e:
        log.error("후보 선정 실패: %s", e)
        return []


# ============================================================
#  Step 2. 각 후보 상세 분석
# ============================================================

DETAIL_PROMPT = """당신은 글로벌 이커머스 트렌드 분석가 + 행동경제학 마케팅 전략가입니다.

다음 상품에 대해 한국 시장 진입 관점에서 상세 분석하세요.

상품: {product_name_ko} ({product_name_en})
카테고리: {category}
선정 사유: {trend_signal}
한국 갭 사유: {korea_gap_signal}

다음 JSON 형식으로만 답변하세요. 다른 텍스트 금지.

{{
  "why_trending": {{
    "overseas_reason": "해외에서 뜨는 구체적 이유 (100-150자)",
    "search_growth_reason": "검색량 증가의 심리적 원인 (80-120자)",
    "consumer_response": "소비자가 왜 반응하는가 (80-120자)"
  }},
  "korea_gap": {{
    "supply_shortage": "한국 공급 부족 구체적 이유 (80-120자)",
    "branding_gap": "감성 브랜딩 부족 요소 (80-120자)",
    "content_gap": "릴스/쇼츠 콘텐츠 부족 요소 (80-120자)"
  }},
  "target": {{
    "age_gender": "주 타깃 (예: 20대 후반~30대 초반 여성)",
    "purchase_context": "구매 상황 (예: 자기보상, 친구 선물)",
    "emotional_trigger": "핵심 감정 포인트 (예: 자기만족, 우월감)"
  }},
  "psychology": {{
    "cialdini_elements": ["희소성", "사회적 증거"],
    "cialdini_explanation": "치알디니 요소가 어떻게 작동하는지 (100-150자)",
    "kahneman_elements": ["손실회피", "감정소비"],
    "kahneman_explanation": "행동경제학 요소가 어떻게 작동하는지 (100-150자)",
    "save_share_trigger": "왜 저장/공유하고 싶어지는가 (80-120자)"
  }},
  "reels_hooks": {{
    "first_second_hook": "첫 1초 후킹 문구 (15자 이내, 강렬)",
    "stop_scroll": "스크롤 멈추게 하는 문구 (20자 이내)",
    "save_trigger": "저장 유도 문구 (25자 이내)",
    "comment_trigger": "댓글 유도 문구 (25자 이내, 질문형)",
    "purchase_urge": "구매 충동 문구 (25자 이내)",
    "cta": "행동 유도 문구 (20자 이내)"
  }},
  "estimated": {{
    "selling_price_krw": "예상 판매가 (예: 28,000~38,000원)",
    "estimated_cost_krw": "예상 원가 (예: 4,000~7,000원)",
    "margin_percent": "예상 마진율 (예: 65~75%)",
    "korea_success_score": 7
  }}
}}

⚠️ 주의:
- 모든 문구는 한국어로
- 후킹 문구는 짧고 감정적으로 (예: "이건 왜 한국에 아직 없는 거지?", "선물하면 무조건 물어봄")
- 일반론 금지. 이 상품에 특화된 분석
- korea_success_score는 1~10 정수"""


def analyze_product_detail(candidate: dict, client) -> dict:
    """후보 1개에 대해 상세 분석."""
    prompt = DETAIL_PROMPT.format(**candidate)

    try:
        message = client.messages.create(
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS_DETAIL,
            messages=[{"role": "user", "content": prompt}],
            timeout=TIMEOUT_SECONDS,
        )
        text = message.content[0].text.strip()

        if '```' in text:
            parts = text.split('```')
            for p in parts:
                p = p.strip()
                if p.startswith('json'):
                    p = p[4:].strip()
                if p.startswith('{'):
                    text = p
                    break
        if not text.startswith('{'):
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                text = text[start:end+1]

        return json.loads(text)
    except Exception as e:
        log.error("상세 분석 실패 (%s): %s", candidate.get('product_name_ko'), e)
        return _fallback_detail(candidate)


def _fallback_detail(candidate: dict) -> dict:
    """API 실패 시 빈 구조."""
    return {
        "why_trending": {
            "overseas_reason": "데이터 부족 - API 호출 실패",
            "search_growth_reason": "추후 분석 필요",
            "consumer_response": "추후 분석 필요",
        },
        "korea_gap": {
            "supply_shortage": "추후 분석 필요",
            "branding_gap": "추후 분석 필요",
            "content_gap": "추후 분석 필요",
        },
        "target": {
            "age_gender": "—",
            "purchase_context": "—",
            "emotional_trigger": "—",
        },
        "psychology": {
            "cialdini_elements": [],
            "cialdini_explanation": "—",
            "kahneman_elements": [],
            "kahneman_explanation": "—",
            "save_share_trigger": "—",
        },
        "reels_hooks": {
            "first_second_hook": "—",
            "stop_scroll": "—",
            "save_trigger": "—",
            "comment_trigger": "—",
            "purchase_urge": "—",
            "cta": "—",
        },
        "estimated": {
            "selling_price_krw": "—",
            "estimated_cost_krw": "—",
            "margin_percent": "—",
            "korea_success_score": 0,
        }
    }


# ============================================================
#  통합 진입점
# ============================================================

def analyze_all(collected_data: dict) -> list[dict]:
    """수집 데이터 → 후보 선정 → 상세 분석.

    Returns:
        [{candidate + detail_analysis}, ...] 최대 5개
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        log.error("ANTHROPIC_API_KEY 없음 - 분석 불가")
        return []

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        log.info("✓ Anthropic 클라이언트 준비 완료 (%s)", MODEL_NAME)
    except Exception as e:
        log.error("Anthropic 초기화 실패: %s", e)
        return []

    # Step 1: 후보 5개 선정
    log.info("Step 1: 후보 5개 선정...")
    candidates = select_candidates(collected_data, client)
    if not candidates:
        log.error("후보 선정 실패")
        return []
    log.info("✓ 후보 %d개 선정됨", len(candidates))
    for c in candidates:
        log.info("  - %s (%s)", c.get('product_name_ko'), c.get('category'))

    # Step 2: 각 후보 상세 분석
    log.info("Step 2: 각 후보 상세 분석...")
    out = []
    for i, candidate in enumerate(candidates, 1):
        log.info("  [%d/%d] %s", i, len(candidates), candidate.get('product_name_ko'))
        detail = analyze_product_detail(candidate, client)
        out.append({**candidate, 'detail': detail, 'rank': i})

    log.info("✓ 분석 완료: %d개", len(out))
    return out
