# =============================================================================
# 상품 검색 API (쇼핑몰 검색 구조)
#
#   화면 구조 (나중에 만들 프론트 기준)
#   ┌──────────────────────────────────────────────┐
#   │ [ 상품명 검색창 (1차 검색)         ] [검색]  │  ← keyword
#   ├──────────────────────────────────────────────┤
#   │ [결과 내 재검색 (2차) ]   [정렬 옵션 ▼]      │  ← sub_keyword, sort
#   ├──────────────────────────────────────────────┤
#   │  상품 목록 ...                               │
#   └──────────────────────────────────────────────┘
#
#   1차 검색 : keyword     → 상품명에 이 글자가 들어간 상품
#   2차 검색 : sub_keyword → 1차 결과 "안에서" 한 번 더 걸러낸다 (AND 조건)
#              sort        → 1차(+2차) 결과를 원하는 순서로 정렬
#
#   카테고리 : category_id → 이 카테고리 상품만 (keyword, sub_keyword 와 AND 로 함께 동작)
#              카테고리 목록은 GET /search/categories 로 받는다.
#
#   요청 예시
#     GET /search/products?category_id=2
#     GET /search/products?category_id=2&keyword=오렌지
#     GET /search/products?keyword=주스
#     GET /search/products?keyword=주스&sub_keyword=오렌지
#     GET /search/products?keyword=주스&sort=price_low
#     GET /search/products?keyword=주스&sub_keyword=오렌지&sort=popular&page=1&size=20
#
#   ※ 주소를 /products/search 로 하지 않은 이유
#     main.py 의 GET /products/{product_id} 가 먼저 등록되어 있어서
#     "/products/search" 요청이 그쪽으로 가서 "search 는 정수가 아니다(422)" 오류가 난다.
# =============================================================================

import logging
from enum import Enum

from fastapi import APIRouter, HTTPException, Query

from .database import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


# -----------------------------------------------------------------------------
# 정렬 옵션 (옵션바에서 고르는 값)
#   Enum 으로 정해 두면 이 목록에 없는 값이 오면 FastAPI 가 422 로 자동 거부한다.
# -----------------------------------------------------------------------------
class SortOption(str, Enum):
    recommend = "recommend"     # 추천순 (기본값)
    popular = "popular"         # 판매 인기순
    newest = "newest"           # 신규상품순
    price_low = "price_low"     # 낮은 가격순
    price_high = "price_high"   # 높은 가격순


# 화면 옵션바에 보여 줄 이름
SORT_LABELS = {
    SortOption.recommend: "추천순",
    SortOption.popular: "판매 인기순",
    SortOption.newest: "신규상품순",
    SortOption.price_low: "낮은 가격순",
    SortOption.price_high: "높은 가격순",
}

# -----------------------------------------------------------------------------
# 정렬 옵션 → ORDER BY 문장
#   ORDER BY 의 컬럼 이름은 %s 빈칸(파라미터 바인딩)으로 넣을 수 없다.
#   그래서 사용자가 보낸 글자를 SQL 에 직접 붙이지 않고,
#   "미리 정해 둔 문장 중 하나를 고르는" 방식(화이트리스트)으로 SQL 인젝션을 막는다.
#
#   마지막의 p.id DESC : 값이 같은 상품끼리 순서가 매번 바뀌지 않게 하는 기준 (페이지 넘김 시 중복/누락 방지)
#
#   추천순 기준 (추천 점수 컬럼이 아직 없어서 있는 정보로 계산)
#     1) 재고가 있는 상품 먼저   (p.stock > 0 은 참이면 1, 거짓이면 0)
#     2) 많이 팔린 상품 먼저
#     3) 최근 등록된 상품 먼저
# -----------------------------------------------------------------------------
ORDER_BY_SQL = {
    SortOption.recommend: "(p.stock > 0) DESC, sold_qty DESC, p.created_at DESC, p.id DESC",
    SortOption.popular: "sold_qty DESC, p.id DESC",
    SortOption.newest: "p.created_at DESC, p.id DESC",
    SortOption.price_low: "p.price ASC, p.id DESC",
    SortOption.price_high: "p.price DESC, p.id DESC",
}


def to_like_pattern(text):
    """검색어를 LIKE 용 '%검색어%' 로 만든다.

    사용자가 입력한 % 나 _ 는 LIKE 에서 "아무 글자" 라는 특수 기호라서,
    그대로 두면 "%" 하나만 입력해도 전체 상품이 검색된다.
    앞에 \\ 를 붙여 "진짜 글자 % / _" 로 취급하게 바꾼다. (MariaDB 기본 이스케이프 문자가 \\ 이다)
    """
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def build_where(keyword, sub_keyword, category_id=None):
    """카테고리 / 1차 / 2차 검색 조건으로 WHERE 문장과 값 목록을 만든다.

    조건 문장에는 %s 빈칸만 넣고, 실제 값은 params 리스트로 따로 넘긴다. (파라미터 바인딩)
    """
    conditions = ["p.is_active = 1"]   # 판매 중인 상품만
    params = []

    if category_id is not None:        # 카테고리 필터
        conditions.append("p.category_id = %s")
        params.append(category_id)

    if keyword:                        # 1차 검색 (상단 검색창)
        conditions.append("p.name LIKE %s")
        params.append(to_like_pattern(keyword))

    if sub_keyword:                    # 2차 검색 (결과 내 재검색) → AND 로 한 번 더 좁힌다
        conditions.append("p.name LIKE %s")
        params.append(to_like_pattern(sub_keyword))

    return " AND ".join(conditions), params


def search_products_sql(keyword, sub_keyword, sort, page, size, category_id=None):
    """검색 결과(현재 페이지 상품들)와 전체 건수를 DB 에서 가져온다."""
    where_sql, where_params = build_where(keyword, sub_keyword, category_id)
    order_sql = ORDER_BY_SQL[sort]
    offset = (page - 1) * size

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # ① 전체 건수 : 화면에 "검색 결과 N개" 와 페이지 번호를 보여 주기 위해 필요
            count_sql = f"""
                SELECT COUNT(*) AS total
                FROM products p
                WHERE {where_sql}
            """
            cursor.execute(count_sql, where_params)
            total = cursor.fetchone()["total"]

            # ② 현재 페이지 상품 목록
            #   LEFT JOIN (판매량 집계)
            #     - 결제 완료(PAID) 주문의 상품별 판매 수량 합계를 먼저 구해서 붙인다.
            #     - LEFT JOIN 이라 한 번도 안 팔린 상품도 빠지지 않는다. (그때 sold_qty 는 NULL)
            #     - COALESCE(값, 0) : NULL 이면 0 으로 바꾼다.
            #   {where_sql}, {order_sql} 은 위에서 우리가 만든 고정 문장이라 f-string 으로 붙여도 안전하다.
            #   사용자가 입력한 검색어는 반드시 %s 빈칸으로만 들어간다.
            list_sql = f"""
                SELECT
                    p.id,
                    p.name,
                    p.price,
                    p.stock,
                    p.image_url,
                    p.created_at,
                    p.category_id,
                    c.name AS category_name,
                    COALESCE(s.sold_qty, 0) AS sold_qty
                FROM products p
                -- 카테고리 이름 : LEFT JOIN 이라 카테고리가 없는(NULL) 상품도 빠지지 않는다
                LEFT JOIN categories c ON c.id = p.category_id
                LEFT JOIN (
                    SELECT oi.product_id, SUM(oi.quantity) AS sold_qty
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE o.status = 'PAID'
                    GROUP BY oi.product_id
                ) s ON s.product_id = p.id
                WHERE {where_sql}
                ORDER BY {order_sql}
                LIMIT %s OFFSET %s
            """
            cursor.execute(list_sql, where_params + [size, offset])
            items = cursor.fetchall()

            # SUM 결과는 Decimal 로 오기 때문에 JSON 에서 다루기 쉽게 int 로 바꾼다.
            for item in items:
                item["sold_qty"] = int(item["sold_qty"])

            return total, items
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# 정렬 옵션 목록 API : GET /search/sort-options
#   프론트가 옵션바(드롭다운)를 그릴 때 이 목록을 그대로 쓰면 된다.
# -----------------------------------------------------------------------------
@router.get("/sort-options")
def sort_options():
    return [{"value": opt.value, "label": SORT_LABELS[opt]} for opt in SortOption]


# -----------------------------------------------------------------------------
# 카테고리 목록 API : GET /search/categories
#   프론트가 상단 카테고리 메뉴를 그릴 때 쓴다.
#   product_count : 판매 중인 상품 수 (판매중지 상품은 세지 않는다)
#     → LEFT JOIN 조건에 is_active = 1 을 넣어야 상품이 0개인 카테고리도 목록에 남는다.
#       (WHERE 에 넣으면 상품이 없는 카테고리가 통째로 빠진다)
# -----------------------------------------------------------------------------
@router.get("/categories")
def categories():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT c.id, c.name, COUNT(p.id) AS product_count
                FROM categories c
                LEFT JOIN products p ON p.category_id = c.id AND p.is_active = 1
                GROUP BY c.id, c.name
                ORDER BY c.id
            """)
            return cursor.fetchall()
    except Exception as e:
        logger.error("카테고리 조회 실패: %s", e)
        raise HTTPException(status_code=500, detail="카테고리 조회 에러")
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# 상품 검색 API : GET /search/products
#   category_id : 카테고리 (비우면 전체 카테고리)
#   keyword     : 1차 검색어 (상단 검색창). 비우면 전체 상품
#   sub_keyword : 2차 검색어 (결과 내 재검색)
#   sort        : 정렬 옵션 (기본 추천순)
#   page, size  : 페이지 번호(1부터), 한 페이지 상품 수
# -----------------------------------------------------------------------------
@router.get("/products")
def search_products(
    category_id: int | None = Query(None, ge=1, description="카테고리 id"),
    keyword: str | None = Query(None, max_length=50, description="1차 검색어 (상품명)"),
    sub_keyword: str | None = Query(None, max_length=50, description="2차 검색어 (결과 내 재검색)"),
    sort: SortOption = Query(SortOption.recommend, description="정렬 옵션"),
    page: int = Query(1, ge=1, description="페이지 번호 (1부터)"),
    size: int = Query(20, ge=1, le=100, description="한 페이지 상품 수"),
):
    # 앞뒤 공백 제거. 공백만 입력한 경우는 검색어가 없는 것으로 본다.
    keyword = keyword.strip() if keyword else None
    sub_keyword = sub_keyword.strip() if sub_keyword else None

    try:
        total, items = search_products_sql(keyword, sub_keyword, sort, page, size, category_id)
    except Exception as e:
        logger.error(
            "상품 검색 실패 category_id=%s keyword=%s sub_keyword=%s sort=%s: %s",
            category_id, keyword, sub_keyword, sort.value, e,
        )
        raise HTTPException(status_code=500, detail="상품 검색 에러")

    logger.info(
        "상품 검색 category_id=%s keyword=%s sub_keyword=%s sort=%s page=%s → %s건",
        category_id, keyword, sub_keyword, sort.value, page, total,
    )

    return {
        "category_id": category_id,
        "keyword": keyword,
        "sub_keyword": sub_keyword,
        "sort": sort.value,
        "page": page,
        "size": size,
        "total": total,
        "total_pages": (total + size - 1) // size,   # 올림 나눗셈
        "items": items,
    }
