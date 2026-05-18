from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import httpx

_CNINFO_SEARCH = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
_CNINFO_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}


@dataclass
class AnnualReportMeta:
    code: str
    year: int
    doc_id: str
    title: str
    pub_date: str   # ISO date "YYYY-MM-DD"
    pdf_url: str


def fetch_annual_report_meta(code: str, year: int) -> list[AnnualReportMeta]:
    """Return metadata for all annual report PDFs for `code` in `year`."""
    payload = {
        "stock": code,
        "category": "category_ndbg_szsh",
        "pageNum": 1,
        "pageSize": 30,
        "tabName": "fulltext",
        "column": "szse",
        "plate": "sz",
        "seDate": f"{year}-01-01~{year}-12-31",
    }
    resp = httpx.post(_CNINFO_SEARCH, data=payload, headers=_CNINFO_HEADERS, timeout=30)
    resp.raise_for_status()
    items = resp.json().get("announcements", [])
    results: list[AnnualReportMeta] = []
    for item in items:
        pdf_url = f"https://static.cninfo.com.cn/{item.get('adjunctUrl', '')}"
        results.append(AnnualReportMeta(
            code=code,
            year=year,
            doc_id=item.get("announcementId", ""),
            title=item.get("announcementTitle", ""),
            pub_date=item.get("announcementTime", "")[:10],
            pdf_url=pdf_url,
        ))
    return results


def download_pdf(meta: AnnualReportMeta, dest_dir: Path) -> Path:
    """Download PDF to dest_dir; skip if file already exists."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{meta.code}_{meta.year}_{meta.doc_id}.pdf"
    if dest.exists():
        return dest
    with httpx.stream("GET", meta.pdf_url, follow_redirects=True, timeout=60) as r:
        r.raise_for_status()
        dest.write_bytes(b"".join(r.iter_bytes()))
    return dest
