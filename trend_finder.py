#!/usr/bin/env python3
"""
Trend Finder — Daily Generator

매일 자동 실행:
  1. Google Trends + Amazon Movers + Etsy 데이터 수집
  2. Claude API로 후보 5개 선정 + 상세 분석
  3. HTML 리포트 6개 생성 (index + 상품별 5개)

출력 파일:
  - index.html
  - 1번_상품명_트렌드리포트.html
  - 2번_상품명_트렌드리포트.html
  - ... (총 5개 상품 리포트)
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
import warnings
from datetime import datetime, timezone, timedelta
from pathlib import Path

warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)


def sanitize_filename(name: str) -> str:
    """파일명에 쓸 수 없는 문자 제거."""
    # 한글/영문/숫자만 유지
    name = re.sub(r'[^\w가-힣]', '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip('_')[:50]


def render_template(template_name: str, **kwargs) -> str:
    from jinja2 import Environment, FileSystemLoader
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
    return env.get_template(template_name).render(**kwargs)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--limit-keywords", type=int, default=0,
                        help="시드 키워드 수 제한 (테스트용, 0=전체)")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst)
    timestamp_str = today.strftime("%Y년 %m월 %d일 %H:%M KST")
    date_str = today.strftime("%Y년 %m월 %d일")

    log.info("=" * 60)
    log.info("  글로벌 트렌드 상품 탐지")
    log.info("  %s", timestamp_str)
    log.info("=" * 60)

    # 1. 시드 키워드
    from seed_keywords import get_all_keywords, get_category_for_keyword
    seed_keywords = get_all_keywords()
    if args.limit_keywords > 0:
        seed_keywords = seed_keywords[:args.limit_keywords]
    log.info("시드 키워드: %d개", len(seed_keywords))

    # 2. 데이터 수집
    from data_collectors import collect_all_data
    collected = collect_all_data(seed_keywords)

    # 3. Claude 분석
    from product_analyzer import analyze_all
    candidates = analyze_all(collected)

    if not candidates:
        log.error("후보 분석 실패 - 빈 리포트 생성")
        # 빈 인덱스라도 생성
        index_html = render_template(
            "index_template.html",
            timestamp_str=timestamp_str, date_str=date_str,
            candidates=[],
            error_message="오늘 데이터 수집 또는 분석에 실패했습니다. ANTHROPIC_API_KEY 등록 여부와 API 잔액을 확인하세요.",
        )
        (args.output_dir / "index.html").write_text(index_html, encoding='utf-8')
        return 1

    # 4. 각 상품별 HTML 생성
    log.info("HTML 리포트 생성...")
    product_files = []
    for c in candidates:
        rank = c['rank']
        name_ko = c.get('product_name_ko', f'상품{rank}')
        safe_name = sanitize_filename(name_ko)
        filename = f"{rank}번_{safe_name}_트렌드리포트.html"

        html = render_template(
            "product_template.html",
            timestamp_str=timestamp_str,
            date_str=date_str,
            product=c,
        )
        (args.output_dir / filename).write_text(html, encoding='utf-8')

        # 메인 카드용 핵심 링크 3개 (Amazon, 네이버, 1688)
        links = c.get('links', {})
        quick_links = []
        if links.get('us'):
            quick_links.append(links['us'][0])  # Amazon
        if links.get('kr'):
            quick_links.append(links['kr'][0])  # 네이버
        if links.get('sourcing'):
            quick_links.append(links['sourcing'][0])  # 1688

        product_files.append({
            'rank': rank,
            'name_ko': name_ko,
            'name_en': c.get('product_name_en', ''),
            'category': c.get('category', ''),
            'filename': filename,
            'trend_signal': c.get('trend_signal', ''),
            'korea_gap_signal': c.get('korea_gap_signal', ''),
            'score': c.get('detail', {}).get('estimated', {}).get('korea_success_score', 0),
            'quick_links': quick_links,
        })
        log.info("  ✓ %s (%d bytes)", filename, (args.output_dir / filename).stat().st_size)

    # 5. 인덱스 HTML
    index_html = render_template(
        "index_template.html",
        timestamp_str=timestamp_str, date_str=date_str,
        candidates=product_files,
        error_message=None,
    )
    (args.output_dir / "index.html").write_text(index_html, encoding='utf-8')
    log.info("  ✓ index.html")

    log.info("=" * 60)
    log.info("  완료. 후보 %d개 / 출력 %s", len(candidates), args.output_dir)
    log.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
