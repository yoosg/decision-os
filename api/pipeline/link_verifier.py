"""학습 경로 리소스의 외부 링크 생존을 검증하고, 죽은 링크를 검색 링크로 교체한다.

브라우저에서는 CORS 때문에 타 도메인 링크 생존을 확인할 수 없어, 학습 경로 생성 시점에
서버에서 검증한다. 멀쩡한 링크를 검색으로 잘못 교체하는 오검출을 피하려고 '깨짐' 판정은
404/410/네트워크 실패로만 보수적으로 한정한다(403 등 봇 차단·일시 장애는 유지).
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus

import httpx

_log = logging.getLogger(__name__)

# 검색 쿼리에 붙일 자료유형 라벨(검색어 최적화용).
_SEARCH_LABELS = {
    "official_docs": "공식 문서",
    "core_material": "핵심 자료",
    "github": "github",
    "practice_example": "실습 예제",
}

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# 확실히 사라진 경우만 깨짐으로 본다.
_DEAD_STATUS = {404, 410}


def build_http_client() -> httpx.Client:
    """링크 검증용 httpx.Client. 리다이렉트를 따라가고 브라우저 UA를 사용한다."""
    return httpx.Client(follow_redirects=True, headers={"User-Agent": BROWSER_UA})


def _search_url(technology_name: str, resource_type: str) -> str:
    label = _SEARCH_LABELS.get(resource_type, "")
    query = f"{technology_name} {label}".strip()
    return f"https://www.google.com/search?q={quote_plus(query)}"


def _is_alive(client: httpx.Client, url: str, timeout: float) -> bool:
    """살아있으면 True. 404/410/네트워크 실패면 False. 그 외(403 등)는 True(보수적)."""
    try:
        resp = client.get(url, timeout=timeout)
    except httpx.HTTPError:
        return False
    return resp.status_code not in _DEAD_STATUS


def verify_and_fix_links(
    resources: list[dict],
    technology_name: str,
    client: httpx.Client,
    timeout: float,
) -> list[dict]:
    """URL이 있는 리소스의 생존을 동시 검증해, 죽은 링크는 검색 링크로 교체한 새 리스트를 반환.

    반환 리스트는 입력과 같은 길이·순서·type을 유지하고, url이 빈 리소스는 건드리지 않는다.
    """
    targets = [i for i, r in enumerate(resources) if (r.get("url") or "").strip()]
    if not targets:
        return [dict(r) for r in resources]

    with ThreadPoolExecutor(max_workers=len(targets)) as executor:
        alive_flags = list(
            executor.map(lambda i: _is_alive(client, resources[i]["url"], timeout), targets)
        )
    dead = {i for i, alive in zip(targets, alive_flags) if not alive}

    result = []
    for i, r in enumerate(resources):
        new_r = dict(r)
        if i in dead:
            new_r["url"] = _search_url(technology_name, r.get("type", ""))
            new_r["is_search_fallback"] = True
            _log.info("dead link replaced with search: type=%s", r.get("type"))
        result.append(new_r)
    return result
