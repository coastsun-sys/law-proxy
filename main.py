import os
import requests
import xmltodict

from fastapi import FastAPI, Query
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Law Proxy API")

LAW_API_OC = os.getenv("LAW_API_OC")
BASE_URL = "https://www.law.go.kr/DRF"


@app.get("/")
def home():
    return {"message": "law proxy is running"}


@app.get("/laws/search")
def search_laws(
    query: str = Query(..., description="검색할 법령명"),
    display: int = Query(10, description="검색 결과 수"),
):
    response = requests.get(
        f"{BASE_URL}/lawSearch.do",
        params={
            "OC": LAW_API_OC,
            "target": "law",
            "type": "XML",
            "query": query,
            "display": display,
        },
        timeout=10,
    )

    data = xmltodict.parse(response.text)

    law_search = data.get("LawSearch", {})
    laws = law_search.get("law", [])

    if isinstance(laws, dict):
        laws = [laws]

    return {
        "query": query,
        "total_count": law_search.get("totalCnt"),
        "laws": [
            {
                "mst": law.get("법령일련번호"),
                "name": law.get("법령명한글"),
                "law_id": law.get("법령ID"),
                "department": law.get("소관부처명"),
                "law_type": law.get("법령구분명"),
                "effective_date": law.get("시행일자"),
                "detail_link": law.get("법령상세링크"),
            }
            for law in laws
        ],
    }


@app.get("/laws/detail")
def get_law_detail(
    mst: str = Query(..., description="법령일련번호 MST"),
):
    response = requests.get(
        f"{BASE_URL}/lawService.do",
        params={
            "OC": LAW_API_OC,
            "target": "law",
            "type": "XML",
            "MST": mst,
        },
        timeout=10,
    )

    data = xmltodict.parse(response.text)

    return {
        "mst": mst,
        "result": data,
    }
@app.get("/laws/search-articles")
def search_articles(
    mst: str = Query(..., description="법령일련번호 MST"),
    keyword: str = Query(..., description="찾을 키워드"),
):
    response = requests.get(
        f"{BASE_URL}/lawService.do",
        params={
            "OC": LAW_API_OC,
            "target": "law",
            "type": "XML",
            "MST": mst,
        },
        timeout=10,
    )

    data = xmltodict.parse(response.text)

    law = data.get("법령", {})
    articles = law.get("조문", {}).get("조문단위", [])

    if isinstance(articles, dict):
        articles = [articles]

    matches = []

    for article in articles:
        article_text = article.get("조문내용", "") or ""
        article_title = article.get("조문제목", "") or ""
        article_no = article.get("조문번호", "") or ""

        full_text_parts = [article_text]

        paragraphs = article.get("항", [])

        if isinstance(paragraphs, dict):
            paragraphs = [paragraphs]

        for paragraph in paragraphs:
            paragraph_text = paragraph.get("항내용", "") or ""
            full_text_parts.append(paragraph_text)

            items = paragraph.get("호", [])

            if isinstance(items, dict):
                items = [items]

            for item in items:
                item_text = item.get("호내용", "") or ""
                full_text_parts.append(item_text)

                subitems = item.get("목", [])

                if isinstance(subitems, dict):
                    subitems = [subitems]

                for subitem in subitems:
                    subitem_text = subitem.get("목내용", "") or ""
                    full_text_parts.append(subitem_text)

        full_text = "\n".join(full_text_parts)

        if keyword in full_text:
            matches.append(
                {
                    "article_no": article_no,
                    "article_title": article_title,
                    "article_text": full_text,
                }
            )

    return {
        "mst": mst,
        "keyword": keyword,
        "match_count": len(matches),
        "matches": matches,
    }
@app.get("/laws/find-basis")
def find_basis(
    mst: str = Query(..., description="법령일련번호 MST"),
    question: str = Query(..., description="의원이 물어본 질문 문장"),
):
    keywords = []

    candidate_keywords = [
        "행정사무감사",
        "행정사무",
        "감사",
        "조사",
        "자료",
        "서류제출",
        "출석",
        "답변",
        "질의",
        "본회의",
        "위원회",
        "의결",
        "조례",
        "청원",
        "의안",
        "발의",
        "전문위원",
    ]

    for keyword in candidate_keywords:
        if keyword in question:
            keywords.append(keyword)

    if not keywords:
        keywords = [question]

    response = requests.get(
        f"{BASE_URL}/lawService.do",
        params={
            "OC": LAW_API_OC,
            "target": "law",
            "type": "XML",
            "MST": mst,
        },
        timeout=10,
    )

    data = xmltodict.parse(response.text)

    law = data.get("법령", {})
    articles = law.get("조문", {}).get("조문단위", [])

    if isinstance(articles, dict):
        articles = [articles]

    matches = []

    for article in articles:
        article_text = article.get("조문내용", "") or ""
        article_title = article.get("조문제목", "") or ""
        article_no = article.get("조문번호", "") or ""

        full_text_parts = [article_text]

        paragraphs = article.get("항", [])
        if isinstance(paragraphs, dict):
            paragraphs = [paragraphs]

        for paragraph in paragraphs:
            full_text_parts.append(paragraph.get("항내용", "") or "")

            items = paragraph.get("호", [])
            if isinstance(items, dict):
                items = [items]

            for item in items:
                full_text_parts.append(item.get("호내용", "") or "")

                subitems = item.get("목", [])
                if isinstance(subitems, dict):
                    subitems = [subitems]

                for subitem in subitems:
                    full_text_parts.append(subitem.get("목내용", "") or "")

        full_text = "\n".join(full_text_parts)

        matched_keywords = [
            keyword for keyword in keywords
            if keyword in full_text
        ]

        if matched_keywords:
            score = 0

            # 키워드 많이 맞을수록 점수 증가
            score += len(matched_keywords) * 10

            # 제목에 키워드 있으면 가산점
            for keyword in matched_keywords:
                if keyword in article_title:
                    score += 30

            # 긴 키워드 우선
            for keyword in matched_keywords:
                if len(keyword) >= 4:
                    score += 10

            matches.append(
                {
                    "article_no": article_no,
                    "article_title": article_title,
                    "matched_keywords": matched_keywords,
                    "score": score,
                    "article_text": full_text,
                }
            )

    matches = sorted(matches, key=lambda x: x["score"], reverse=True)

    return {
        "mst": mst,
        "question": question,
        "keywords": keywords,
        "match_count": len(matches),
        "matches": matches,
    }

@app.get("/find-legal-basis")
def find_legal_basis(
    question: str = Query(..., description="의원이 물어본 질문 문장"),
):
    selected_law = {
        "법령명한글": "지방자치법"
    }

    mst = "276357"

    keywords = []

    candidate_keywords = [
        "행정사무감사",
        "행정사무",
        "감사",
        "조사",
        "자료",
        "자료제출",
        "서류제출",
        "출석",
        "답변",
        "질의",
        "본회의",
        "위원회",
        "의결",
        "조례",
        "청원",
        "의안",
        "발의",
        "전문위원",
    ]

    for keyword in candidate_keywords:
        if keyword in question:
            keywords.append(keyword)

    if not keywords:
        keywords = [question]

    detail_response = requests.get(
        f"{BASE_URL}/lawService.do",
        params={
            "OC": LAW_API_OC,
            "target": "law",
            "type": "XML",
            "MST": mst,
        },
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )

    detail_data = xmltodict.parse(detail_response.text)

    law = detail_data.get("법령", {})
    articles = law.get("조문", {}).get("조문단위", [])

    if isinstance(articles, dict):
        articles = [articles]

    matches = []

    for article in articles:
        article_text = article.get("조문내용", "") or ""
        article_title = article.get("조문제목", "") or ""
        article_no = article.get("조문번호", "") or ""

        full_text_parts = [article_text]

        paragraphs = article.get("항", [])
        if isinstance(paragraphs, dict):
            paragraphs = [paragraphs]

        for paragraph in paragraphs:
            full_text_parts.append(paragraph.get("항내용", "") or "")

            items = paragraph.get("호", [])
            if isinstance(items, dict):
                items = [items]

            for item in items:
                full_text_parts.append(item.get("호내용", "") or "")

                subitems = item.get("목", [])
                if isinstance(subitems, dict):
                    subitems = [subitems]

                for subitem in subitems:
                    full_text_parts.append(subitem.get("목내용", "") or "")

        full_text = "\n".join(full_text_parts)

        matched_keywords = [
            keyword for keyword in keywords
            if keyword in full_text
        ]

        if matched_keywords:
            score = 0
            score += len(matched_keywords) * 10

            for keyword in matched_keywords:
                if keyword in article_title:
                    score += 30

            for keyword in matched_keywords:
                if len(keyword) >= 4:
                    score += 10

            matches.append(
                {
                    "law_name": selected_law.get("법령명한글"),
                    "mst": mst,
                    "article_no": article_no,
                    "article_title": article_title,
                    "matched_keywords": matched_keywords,
                    "score": score,
                    "article_text": full_text,
                }
            )

    matches = sorted(matches, key=lambda x: x["score"], reverse=True)

    return {
        "question": question,
        "selected_law": selected_law.get("법령명한글"),
        "mst": mst,
        "keywords": keywords,
        "match_count": len(matches),
        "matches": matches[:1],
    }