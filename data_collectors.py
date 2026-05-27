"""
데이터 수집 모듈.

수집 대상:
  1. Google Trends — 키워드별 검색 추세 (미국 기준)
  2. Amazon Movers & Shakers — 카테고리별 급상승 상품
  3. Etsy Best Sellers — 감성 카테고리 (옵션, 차단 시 스킵)

솔직한 한계:
  - Amazon은 봇 차단 강력. User-Agent 위장하지만 가끔 실패
  - Etsy도 마찬가지
  - pytrends는 비공식 라이브러리라 가끔 깨짐
  → 부분 실패해도 보고서는 생성되도록 try/except 처리
"""
from __future__ import annotations

import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# 봇 차단 회피용 User-Agent 풀
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

REQUEST_TIMEOUT = 15


def _get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }


# ============================================================
#  1. Google Trends
# ============================================================

def fetch_google_trends(keywords: list[str], geo: str = "US",
                        timeframe: str = "today 1-m") -> dict[str, dict]:
    """Google Trends에서 키워드별 검색량 추세 수집.

    Returns:
        {keyword: {'mean': float, 'recent': float, 'momentum': float}}
        momentum = recent / mean (1.0 초과면 상승, 미만이면 하락)
    """
    log.info("Google Trends 수집: %d 키워드 (geo=%s)", len(keywords), geo)
    out = {}

    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))
    except Exception as e:
        log.warning("pytrends 초기화 실패: %s", e)
        return out

    # pytrends는 한 번에 최대 5개 키워드. 청크로 나눠서 처리
    chunks = [keywords[i:i+5] for i in range(0, len(keywords), 5)]

    for i, chunk in enumerate(chunks):
        try:
            pytrends.build_payload(chunk, cat=0, timeframe=timeframe, geo=geo, gprop='')
            df = pytrends.interest_over_time()
            if df.empty:
                continue

            for kw in chunk:
                if kw not in df.columns:
                    continue
                values = df[kw].values
                if len(values) == 0:
                    continue

                mean = float(values.mean())
                # 최근 25% 구간 평균
                recent_n = max(1, len(values) // 4)
                recent = float(values[-recent_n:].mean())

                momentum = recent / mean if mean > 0 else 0
                out[kw] = {
                    'mean': round(mean, 1),
                    'recent': round(recent, 1),
                    'momentum': round(momentum, 2),
                }

            # rate limit 회피
            time.sleep(random.uniform(1.5, 3.0))
            log.info("  chunk %d/%d 완료", i+1, len(chunks))
        except Exception as e:
            log.warning("  chunk %d 실패: %s", i+1, e)
            time.sleep(5)
            continue

    log.info("Google Trends 완료: %d/%d 키워드 데이터", len(out), len(keywords))
    return out


def fetch_korea_trends(keywords: list[str]) -> dict[str, dict]:
    """한국 검색량 (KR geo) - 갭 검증용.

    영어 키워드를 한국에서 검색한 결과. 낮으면 한국 미인지 영역.
    """
    return fetch_google_trends(keywords, geo="KR", timeframe="today 3-m")


# ============================================================
#  2. Amazon Movers & Shakers
# ============================================================

# 감성 소비·충동구매 잘 일어나는 카테고리만 선별
AMAZON_CATEGORIES = [
    ("beauty", "https://www.amazon.com/gp/movers-and-shakers/beauty/"),
    ("home_garden", "https://www.amazon.com/gp/movers-and-shakers/home-garden/"),
    ("kitchen", "https://www.amazon.com/gp/movers-and-shakers/kitchen/"),
    ("health_personal_care", "https://www.amazon.com/gp/movers-and-shakers/hpc/"),
    ("pet_supplies", "https://www.amazon.com/gp/movers-and-shakers/pet-supplies/"),
    ("office_products", "https://www.amazon.com/gp/movers-and-shakers/office-products/"),
    ("arts_crafts", "https://www.amazon.com/gp/movers-and-shakers/arts-crafts/"),
]


def fetch_amazon_movers(max_per_category: int = 10) -> list[dict]:
    """Amazon Movers & Shakers 스크래핑.

    솔직한 한계: Amazon은 봇 차단 매우 강력. 자주 실패함.
    실패하면 빈 리스트 반환하고 다른 데이터로 보고서 생성.
    """
    log.info("Amazon Movers & Shakers 수집...")
    out = []

    for category, url in AMAZON_CATEGORIES:
        try:
            resp = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                log.warning("  %s: HTTP %d", category, resp.status_code)
                continue

            soup = BeautifulSoup(resp.text, 'lxml')
            # Movers & Shakers 페이지의 상품은 zg-item 또는 a-link-normal 클래스
            items = soup.select('div[id^="p13n-asin"]')[:max_per_category]
            if not items:
                # fallback selector
                items = soup.select('div.zg-item')[:max_per_category]

            for idx, item in enumerate(items):
                # 상품명 추출
                title_el = item.select_one('div._cDEzb_p13n-sc-css-line-clamp-3_g3dy1') \
                    or item.select_one('div.p13n-sc-truncate') \
                    or item.select_one('span.a-text-normal')
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                # 가격 추출 (옵션)
                price_el = item.select_one('span._cDEzb_p13n-sc-price_3mJ9Z') \
                    or item.select_one('span.p13n-sc-price')
                price = price_el.get_text(strip=True) if price_el else ""

                out.append({
                    'category': category,
                    'rank': idx + 1,
                    'title': title[:200],
                    'price': price,
                    'source': 'amazon_movers',
                })

            time.sleep(random.uniform(2.0, 4.0))  # rate limit
        except Exception as e:
            log.warning("  %s 실패: %s", category, e)
            continue

    log.info("Amazon Movers 완료: %d 상품", len(out))
    return out


# ============================================================
#  3. Etsy Best Sellers (옵션)
# ============================================================

ETSY_CATEGORIES = [
    ("home_living", "https://www.etsy.com/c/home-and-living"),
    ("jewelry", "https://www.etsy.com/c/jewelry"),
    ("paper_party", "https://www.etsy.com/c/paper-and-party-supplies"),
]


def fetch_etsy_bestsellers(max_per_category: int = 10) -> list[dict]:
    """Etsy 인기 상품 스크래핑.

    솔직한 한계: Etsy도 봇 차단 있음. 실패 시 빈 리스트.
    """
    log.info("Etsy 인기 상품 수집...")
    out = []

    for category, url in ETSY_CATEGORIES:
        try:
            resp = requests.get(url, headers=_get_headers(), timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                log.warning("  %s: HTTP %d", category, resp.status_code)
                continue

            soup = BeautifulSoup(resp.text, 'lxml')
            items = soup.select('div[data-listing-id]')[:max_per_category]

            for idx, item in enumerate(items):
                title_el = item.select_one('h3') or item.select_one('a[data-listing-link]')
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                out.append({
                    'category': category,
                    'rank': idx + 1,
                    'title': title[:200],
                    'source': 'etsy',
                })

            time.sleep(random.uniform(2.0, 4.0))
        except Exception as e:
            log.warning("  %s 실패: %s", category, e)
            continue

    log.info("Etsy 완료: %d 상품", len(out))
    return out


# ============================================================
#  통합 수집
# ============================================================

def collect_all_data(seed_keywords: list[str]) -> dict:
    """모든 소스에서 데이터 수집.

    Returns:
        {
          'google_trends_us': {...},
          'google_trends_kr': {...},
          'amazon_movers': [...],
          'etsy_bestsellers': [...],
        }
    """
    log.info("=" * 60)
    log.info("데이터 수집 시작")
    log.info("=" * 60)

    result = {
        'google_trends_us': {},
        'google_trends_kr': {},
        'amazon_movers': [],
        'etsy_bestsellers': [],
    }

    # 병렬 수집 (서로 다른 소스라 충돌 없음)
    with ThreadPoolExecutor(max_workers=4) as ex:
        f_us = ex.submit(fetch_google_trends, seed_keywords, "US", "today 1-m")
        f_kr = ex.submit(fetch_korea_trends, seed_keywords)
        f_amz = ex.submit(fetch_amazon_movers)
        f_etsy = ex.submit(fetch_etsy_bestsellers)

        try:
            result['google_trends_us'] = f_us.result(timeout=300)
        except Exception as e:
            log.warning("Google Trends US 실패: %s", e)

        try:
            result['google_trends_kr'] = f_kr.result(timeout=300)
        except Exception as e:
            log.warning("Google Trends KR 실패: %s", e)

        try:
            result['amazon_movers'] = f_amz.result(timeout=120)
        except Exception as e:
            log.warning("Amazon 실패: %s", e)

        try:
            result['etsy_bestsellers'] = f_etsy.result(timeout=120)
        except Exception as e:
            log.warning("Etsy 실패: %s", e)

    log.info("=" * 60)
    log.info("데이터 수집 완료")
    log.info("  Google Trends US: %d 키워드", len(result['google_trends_us']))
    log.info("  Google Trends KR: %d 키워드", len(result['google_trends_kr']))
    log.info("  Amazon Movers: %d 상품", len(result['amazon_movers']))
    log.info("  Etsy: %d 상품", len(result['etsy_bestsellers']))
    log.info("=" * 60)

    return result
