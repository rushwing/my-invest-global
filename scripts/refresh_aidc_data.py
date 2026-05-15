"""Refresh and validate A-share AIDC report data.

Important data-quality rules:
- Tradeable A-share quote, market-cap, PE, and 1/3-month return fields come from
  Tencent quote/kline endpoints in one refresh pass.
- Product-line revenue/profit mix comes from Eastmoney F10 BusinessAnalysis PageAjax
  when available. Eastmoney labels the profit field as main-business profit, which
  is a gross-profit style segment metric rather than audited attributable net profit.
- Target prices are allowed only when the report date is on or after 2026-01-01
  and the source is explicitly recorded in VERIFIED_TARGETS.
- Missing or unverified post-2026 target prices stay blank.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_HTML = ROOT / "aidc_report.html"
CN_DIR = ROOT / "data" / "agent_input" / "cn"
CHINA_MD = CN_DIR / "data_china_aidc.md"
STOCKS_YAML = CN_DIR / "stocks.yaml"
TARGET_CUTOFF = date(2026, 1, 1)


@dataclass(frozen=True)
class StockMeta:
    sector: str
    subsector: str
    name: str
    code: str | None
    summary: str
    rank: str
    scarcity: str
    rating: str
    active: bool = True
    category_id: str = ""
    source_file: str = ""
    exchange: str = ""
    board: str = ""
    product_mix: str = "待获取"
    valuation_signal: str = ""
    davis_signal: str = ""


@dataclass(frozen=True)
class TargetPrice:
    value: float
    broker: str
    report_date: date


@dataclass(frozen=True)
class RefreshedStock:
    meta: StockMeta
    price: float | None
    one_month_return: float | None
    three_month_return: float | None
    market_cap_yi: float | None
    dynamic_pe: float | None
    quote_time: datetime | None
    target: TargetPrice | None
    daily_return: float | None = None
    six_month_return: float | None = None
    one_year_return: float | None = None
    volume_lot: float | None = None
    amount_wan: float | None = None
    product_mix: str = "待获取"


# Add entries here only after verifying the original report date is >= TARGET_CUTOFF.
VERIFIED_TARGETS: dict[str, TargetPrice] = {}

STOCKS: list[StockMeta] = [
    StockMeta(
        "光通信",
        "光模块/CPO",
        "中际旭创",
        "300308",
        "Q1营收194.96亿+192%，净利57.35亿+262%，毛利率46%创新高；800G/1.6T放量，CPO量产在即",
        "#1全球",
        "极高",
        "强烈推荐",
    ),
    StockMeta(
        "光通信",
        "光模块/CPO",
        "新易盛",
        "300502",
        'Q1营收约55亿+85%（估），800G出货加速；基金抱团后估值承压，被部分机构列"坑王"，需持续跟踪验证',
        "#2国内",
        "极高",
        "推荐",
    ),
    StockMeta(
        "光通信",
        "CPO/光无源",
        "天孚通信",
        "300394",
        "Q1利润承压，CPO产品验证进展是核心看点，部分公募止损导致短期压力，长期CPO逻辑不变",
        "#1光无源",
        "极高",
        "推荐",
    ),
    StockMeta(
        "光通信",
        "激光器/探测器",
        "光迅科技",
        "002281",
        "Q1数据中心激光器营收占比提升至60%+，下游AI服务器需求旺盛，毛利率改善",
        "#1国内激光器",
        "高",
        "推荐",
    ),
    StockMeta(
        "光通信",
        "激光器/探测器",
        "华工科技",
        "000988",
        "Q1激光业务同比+50%，工业激光+通信激光双轮驱动，通信业务受益AIDC扩建",
        "#2国内激光器",
        "高",
        "推荐",
    ),
    StockMeta(
        "光通信",
        "OCS光交换",
        "剑桥科技",
        "603083",
        "Q1切入OCS光交换赛道，传统业务+新品布局，成长属性突出，长期受益AI光互联需求",
        "#2 OCS",
        "极高",
        "推荐",
    ),
    StockMeta(
        "光通信",
        "光无源器件",
        "太辰光",
        "300570",
        "原表误写为 300003；300003 实为乐普医疗。太辰光行情已按 300570 刷新",
        "#2光无源",
        "中",
        "中性",
    ),
    StockMeta(
        "光通信",
        "光纤光缆",
        "长飞光纤",
        "601869",
        "Q1光纤量价齐升，海外订单增加；数据中心光纤耗量大幅增加带动整体需求回暖",
        "#1国内光纤",
        "中",
        "推荐",
    ),
    StockMeta(
        "光通信",
        "光纤光缆",
        "中天科技",
        "600522",
        "Q1营收约100亿，海缆+陆缆均衡布局，AIDC园区光缆需求稳增，估值偏低",
        "#2国内光纤",
        "中",
        "中性",
    ),
    StockMeta(
        "光通信",
        "光纤光缆",
        "亨通光电",
        "600487",
        "Q1海外订单增长显著，国际化战略推进，海底光缆业务景气高，出口型受益全球AIDC建设",
        "#3国内光纤",
        "中",
        "中性",
    ),
    StockMeta(
        "内存/半导体",
        "内存接口芯片",
        "澜起科技",
        "688008",
        "Q1内存接口芯片出货量暴增，DDR5/RCD5供不应求；AI服务器内存需求带动业绩大幅超预期",
        "#1全球内存接口",
        "极高",
        "强烈推荐",
    ),
    StockMeta(
        "内存/半导体",
        "企业级存储/模组",
        "江波龙",
        "301308",
        "企业级SSD与存储模组受益AI服务器本地存储扩容，弹性高但周期属性较强",
        "#1存储模组",
        "高",
        "推荐",
    ),
    StockMeta(
        "内存/半导体",
        "存储芯片/模组",
        "佰维存储",
        "688525",
        "AI终端与服务器存储升级带来高弹性，需跟踪存储价格周期和企业级产品占比",
        "#2存储模组",
        "高",
        "推荐",
    ),
    StockMeta(
        "算力/芯片",
        "AI训练芯片",
        "寒武纪-U",
        "688256",
        "Q1营收高增，920系列获政府/SOE采购，短期利润弹性仍需验证；长期为国产AI芯片核心量产平台",
        "#1国产AI芯片",
        "极高",
        "推荐",
    ),
    StockMeta(
        "算力/芯片",
        "CPU/GPGPU",
        "海光信息",
        "688041",
        "国产高端处理器与协处理器平台，受益信创算力与国产AI集群建设，弹性弱于纯AI芯片",
        "#1国产高端CPU",
        "高",
        "推荐",
    ),
    StockMeta(
        "PCB",
        "AI高速PCB",
        "深南电路",
        "002916",
        "Q1 AI服务器PCB订单暴增，高层数PCB产线扩产中，毛利率持续提升；国内AI高速PCB核心供应商",
        "#1国内AI PCB",
        "高",
        "强烈推荐",
    ),
    StockMeta(
        "PCB",
        "AI高速PCB",
        "沪电股份",
        "002463",
        "Q1高层数AI PCB产能爬坡，背板类订单来自国内外AI服务器厂商，营收同比+35%",
        "#2国内AI PCB",
        "高",
        "推荐",
    ),
    StockMeta(
        "PCB",
        "AI高速PCB",
        "胜宏科技",
        "300476",
        "AI服务器高多层PCB与显卡板需求提升，海外AI客户链条弹性高，需跟踪订单兑现",
        "#3国内AI PCB",
        "高",
        "推荐",
    ),
    StockMeta(
        "上游材料",
        "高频覆铜板CCL",
        "生益科技",
        "600183",
        "高频高速CCL为AI服务器PCB上游核心材料，价格与产品结构升级共同驱动利润弹性",
        "#1国内CCL",
        "高",
        "推荐",
    ),
    StockMeta(
        "上游材料",
        "高端电子树脂",
        "东材科技",
        "601208",
        "高端电子树脂/膜材料切入高速PCB与封装材料链条，是AI PCB上游国产替代观察重点",
        "#1电子树脂",
        "高",
        "推荐",
    ),
    StockMeta(
        "上游材料",
        "电子树脂/特种材料",
        "圣泉集团",
        "605589",
        "电子级树脂与特种材料受益高频高速基材升级，适合作为PCB材料扩散线跟踪",
        "#2电子树脂",
        "中",
        "中性",
    ),
    StockMeta(
        "上游材料",
        "光学晶体/旋光片",
        "福晶科技",
        "002222",
        "旋光片属于光通信上游器件观察点，但公司已提示该业务占比极小，暂不作为主线龙头处理",
        "#1非线性晶体",
        "中",
        "观察",
    ),
    StockMeta(
        "AI服务器",
        "AI服务器整机",
        "浪潮信息",
        "000977",
        "Q1营收354.7亿（-24.3%）但净利6.05亿（+30.7%），营收下降系大客户结构调整，盈利能力反而改善；全年AI服务器出货量国内第一",
        "#1国内AI服务器",
        "高",
        "推荐",
    ),
    StockMeta(
        "AI服务器",
        "AI服务器整机",
        "中科曙光",
        "603019",
        "Q1超算+AI服务器业务双线增长，政府采购受益度高，液冷服务器布局领先同行",
        "#2国内AI服务器",
        "高",
        "推荐",
    ),
    StockMeta(
        "AI服务器",
        "算力租赁",
        "利通电子",
        "603629",
        "算力租赁热度高，但公司曾澄清部分市场传闻；应按真实租赁规模和回款质量跟踪",
        "#1算力租赁弹性",
        "高",
        "推荐",
    ),
    StockMeta(
        "AI服务器",
        "算力租赁/边缘算力",
        "协创数据",
        "300857",
        "服务器再制造、数据存储与算力服务叙事共振，偏主题弹性，需跟踪业务收入占比",
        "#2算力租赁弹性",
        "高",
        "推荐",
    ),
    StockMeta(
        "半导体设备/封测",
        "半导体设备",
        "北方华创",
        "002371",
        "Q1订单持续爆满，国产替代加速背景下刻蚀/CVD/PVD设备全线扩产，营收同比+40%+",
        "#1国产设备",
        "高",
        "推荐",
    ),
    StockMeta(
        "半导体设备/封测",
        "半导体设备",
        "中微公司",
        "688012",
        "Q1刻蚀机+薄膜设备双线扩产，AI芯片制造端国产设备渗透率持续提升，海外拓展超预期",
        "#2国产设备",
        "高",
        "推荐",
    ),
    StockMeta(
        "半导体设备/封测",
        "先进封装/封测",
        "长电科技",
        "600584",
        "先进封装与高性能封测受益国产算力芯片放量，是设备之后更贴近AI芯片量产的环节",
        "#1国内封测",
        "高",
        "推荐",
    ),
    StockMeta(
        "半导体设备/封测",
        "先进封装/封测",
        "通富微电",
        "002156",
        "高性能计算芯片封测与客户结构改善带来弹性，适合跟踪国产GPU/CPU放量节奏",
        "#2国内封测",
        "高",
        "推荐",
    ),
    StockMeta(
        "散热/液冷",
        "液冷设备",
        "英维克",
        "002837",
        "Q1液冷设备订单增速强劲，但股价受机构止损压力；长期液冷渗透率提升趋势不变，冷板式液冷市场份额第一",
        "#1国内液冷",
        "极高",
        "推荐",
    ),
    StockMeta(
        "散热/液冷",
        "精密空调",
        "申菱环境",
        "301018",
        "Q1数据中心精密空调订单大增，浸没式液冷+风冷混合解决方案出货；国内数据中心精密温控第二大玩家",
        "#2液冷/精空",
        "高",
        "推荐",
    ),
    StockMeta(
        "散热/液冷",
        "冷源系统",
        "高澜股份",
        "300499",
        "Q1冷却塔+冷水机组订单持续增长，AIDC冷源系统需求爆发；市值较小，弹性较大",
        "#2冷源系统",
        "高",
        "推荐",
    ),
    StockMeta(
        "散热/液冷",
        "金刚石散热",
        "沃尔德",
        "688028",
        "金刚石热管理处于早期主题阶段，适合作为高热流密度芯片散热观察线，不宜等同液冷主线",
        "#1金刚石散热观察",
        "中",
        "观察",
    ),
    StockMeta(
        "电源系统",
        "SST/干式变压器",
        "金盘科技",
        "688676",
        "干式变压器、数字化电力设备和SST/HVDC布局契合AIDC供配电升级，是电源系统新增核心",
        "#1 AIDC电力设备",
        "高",
        "推荐",
    ),
    StockMeta(
        "电源系统",
        "UPS/模块电源",
        "科华数据",
        "002335",
        "Q1 UPS+储能双业务增长，数据中心UPS订单稳定增长，估值合理，成长性不及Tier-1",
        "#2 UPS",
        "中",
        "中性",
    ),
    StockMeta(
        "电源系统",
        "模块化电源",
        "科士达",
        "002518",
        "Q1模块化UPS出货量同比+30%，进军海外市场逐步取得突破，国内数据中心客户持续拓展",
        "#3电源",
        "中",
        "中性",
    ),
    StockMeta(
        "电源系统",
        "HVDC直流供电",
        "动力源",
        "600405",
        "Q1 HVDC直流电源订单小幅增长，体量较小，受益AIDC高压直流供电需求，弹性有限",
        "#3 HVDC",
        "低",
        "中性",
    ),
    StockMeta(
        "AI网络",
        "以太网交换机",
        "锐捷网络",
        "301165",
        "Deprecated：网络设备暂从AIDC研报主表移除，数据保留用于后续恢复或横向比较",
        "#2国内交换机",
        "高",
        "强烈推荐",
        False,
    ),
    StockMeta(
        "AI网络",
        "InfiniBand替代/RoCE",
        "星融元（未上市观察）",
        None,
        "Deprecated：星融元尚未 IPO，不能进入可交易 A 股池，仅保留产业链观察数据",
        "#1国产RoCE",
        "极高",
        "观察（不可交易）",
        False,
    ),
    StockMeta(
        "机柜/基建",
        "IDC集成/综合布线",
        "神州数码",
        "000034",
        "Q1 IDC集成服务稳增，受益数据中心建设潮，综合布线业务量价稳定，估值合理",
        "#1 IDC集成",
        "低",
        "中性",
    ),
]


def parse_simple_yaml_lists(path: Path) -> dict[str, Any]:
    """Parse the small stocks.yaml schema without adding a runtime dependency."""

    data: dict[str, Any] = {}
    current_section: str | None = None
    current_item: dict[str, Any] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if not raw_line.startswith(" "):
            key, _, value = raw_line.partition(":")
            key = key.strip()
            value = value.strip()
            if value == "":
                data[key] = []
                current_section = key
                current_item = None
            else:
                data[key] = parse_yaml_scalar(value)
                current_section = None
                current_item = None
            continue
        if raw_line.startswith("  - "):
            if current_section is None:
                continue
            current_item = {}
            data.setdefault(current_section, []).append(current_item)
            rest = raw_line[4:].strip()
            if rest:
                key, _, value = rest.partition(":")
                current_item[key.strip()] = parse_yaml_scalar(value.strip())
            continue
        if raw_line.startswith("    ") and current_item is not None:
            key, _, value = raw_line.strip().partition(":")
            current_item[key.strip()] = parse_yaml_scalar(value.strip())
    return data


def parse_yaml_scalar(value: str) -> Any:
    if value == "null":
        return None
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    try:
        return int(value)
    except ValueError:
        return value


def split_md_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def read_existing_row_data() -> dict[str, dict[str, str]]:
    """Read mutable per-stock fields from existing markdown before refreshing."""

    rows: dict[str, dict[str, str]] = {}
    paths = [
        path
        for path in CN_DIR.glob("*.md")
        if path.name not in {"README.md"} and path.is_file()
    ]
    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if not line.startswith("| 领域 |"):
                continue
            headers = split_md_row(line)
            for row_line in lines[i + 2 :]:
                if not row_line.startswith("|"):
                    break
                values = split_md_row(row_line)
                if len(values) != len(headers):
                    continue
                row = dict(zip(headers, values, strict=True))
                code = row.get("股票代码")
                if code and code != "未上市":
                    rows[code] = row
    return rows


def normalize_product_mix_text(value: str) -> str:
    return re.sub(r"/\+([0-9])", r"/\1", value)


def default_summary(name: str) -> str:
    return f"待补：{name}为新增自选观察标的，需补充2026Q1、订单、客户、产能和利润率数据。"


def load_stocks_from_yaml(path: Path = STOCKS_YAML) -> list[StockMeta]:
    if not path.exists():
        return STOCKS

    stock_yaml = parse_simple_yaml_lists(path)
    existing_rows = read_existing_row_data()
    metas: list[StockMeta] = []
    seen_codes: set[str] = set()
    for item in stock_yaml.get("stocks", []):
        code = item.get("code")
        if code in seen_codes:
            continue
        if code is not None:
            seen_codes.add(code)
        row = existing_rows.get(code or "", {})
        name = str(item["name"])
        davis_observation = (row.get("戴维斯双击观察") or "").replace(
            "扭亏时间线",
            "扭亏拐点",
        )
        product_mix = normalize_product_mix_text(row.get("产品线营收/净利份额比例") or "待获取")
        metas.append(
            StockMeta(
                sector=str(item.get("source_category") or item.get("category") or ""),
                subsector=str(item.get("sub_sector") or ""),
                name=name,
                code=code,
                summary=row.get("一季度财报总结") or default_summary(name),
                rank=row.get("行业排行") or "待核验",
                scarcity=row.get("产品紧缺度") or "待核验",
                rating=row.get("投资价值评级") or "观察",
                active=bool(item.get("category_id") != "out_of_scope"),
                category_id=str(item.get("category_id") or ""),
                source_file=str(item.get("source_file") or ""),
                exchange=str(item.get("exchange") or ""),
                board=str(item.get("board") or ""),
                product_mix=product_mix,
                valuation_signal=row.get("估值/业绩弹性") or "",
                davis_signal=davis_observation,
            )
        )
    return metas


def market_symbol(code: str) -> str:
    """Return Tencent market symbol for an A-share code."""

    return ("sh" if code.startswith(("6", "9")) else "sz") + code


def parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fetch_json(url: str, retries: int = 3, timeout: int = 20) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
            )
        },
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with opener.open(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - depends on external network
            last_error = exc
            if attempt < retries:
                time.sleep(attempt)
    if last_error is None:  # pragma: no cover - defensive only
        raise RuntimeError("Tencent quote request failed without an exception")
    raise last_error


def eastmoney_code(code: str) -> str:
    return ("SH" if code.startswith(("6", "9")) else "SZ") + code


def fetch_eastmoney_business_analysis(code: str) -> dict[str, Any]:
    url = (
        "https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax"
        f"?code={eastmoney_code(code)}"
    )
    return fetch_json(url, retries=1, timeout=20)


def format_money_yuan(value: float | None) -> str:
    if value is None:
        return "N/A"
    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.2f}亿"
    if abs(value) >= 10_000:
        return f"{value / 10_000:.2f}万"
    return f"{value:.0f}"


def format_product_mix(payload: dict[str, Any]) -> str:
    rows = payload.get("zygcfx") or []
    product_rows = [
        row for row in rows if str(row.get("MAINOP_TYPE")) == "2" and row.get("ITEM_NAME")
    ]
    if not product_rows:
        product_rows = [
            row for row in rows if str(row.get("MAINOP_TYPE")) == "1" and row.get("ITEM_NAME")
        ]
    if not product_rows:
        return "待获取"

    latest_date = max(str(row.get("REPORT_DATE") or "")[:10] for row in product_rows)
    latest_rows = [
        row for row in product_rows if str(row.get("REPORT_DATE") or "")[:10] == latest_date
    ]
    latest_rows.sort(key=lambda row: float(row.get("MAIN_BUSINESS_INCOME") or 0), reverse=True)

    parts: list[str] = []
    for row in latest_rows[:6]:
        name = str(row.get("ITEM_NAME") or "").replace("|", "/")
        income = format_money_yuan(parse_float(str(row.get("MAIN_BUSINESS_INCOME") or "")))
        mbi_ratio = parse_float(str(row.get("MBI_RATIO") or ""))
        income_ratio = format_share_percent(None if mbi_ratio is None else mbi_ratio * 100)
        profit = format_money_yuan(parse_float(str(row.get("MAIN_BUSINESS_RPOFIT") or "")))
        mbr_ratio = parse_float(str(row.get("MBR_RATIO") or ""))
        profit_ratio = format_share_percent(None if mbr_ratio is None else mbr_ratio * 100)
        parts.append(f"{name}:收入{income}/{income_ratio},利润{profit}/{profit_ratio}")
    return f"{latest_date}；" + "；".join(parts)


def product_mix_for(meta: StockMeta) -> str:
    if meta.code is None:
        return "未上市"
    product_mix = format_product_mix(fetch_eastmoney_business_analysis(meta.code))
    return product_mix if product_mix != "待获取" else (meta.product_mix or "待获取")


def fetch_product_mixes(metas: list[StockMeta], max_workers: int = 16) -> dict[str, str]:
    product_mixes: dict[str, str] = {}
    tradeable = [meta for meta in metas if meta.code is not None]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(product_mix_for, meta): meta for meta in tradeable}
        for future in as_completed(futures):
            meta = futures[future]
            try:
                product_mixes[meta.code or ""] = future.result()
            except Exception:
                product_mixes[meta.code or ""] = meta.product_mix or "待获取"
    return product_mixes


def fetch_tencent_stock(meta: StockMeta, end: date | None = None) -> RefreshedStock:
    if meta.code is None:
        return RefreshedStock(meta, None, None, None, None, None, None, None)

    end_date = end or date.today()
    begin_date = end_date - timedelta(days=420)
    symbol = market_symbol(meta.code)
    url = (
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        f"?param={symbol},day,{begin_date:%Y-%m-%d},{end_date:%Y-%m-%d},200,qfq"
    )
    payload = fetch_json(url)
    data = payload["data"][symbol]
    quote = data["qt"][symbol]
    kline = data.get("qfqday") or data.get("day") or []

    price = parse_float(quote[3])
    market_cap_yi = parse_float(quote[45])
    dynamic_pe = parse_float(quote[39])
    quote_time = datetime.strptime(quote[30], "%Y%m%d%H%M%S")
    daily_return = parse_float(quote[32])
    one_month_return = calculate_return(kline, quote_time.date(), 30)
    three_month_return = calculate_return(kline, quote_time.date(), 90)
    six_month_return = calculate_return(kline, quote_time.date(), 180)
    one_year_return = calculate_return(kline, quote_time.date(), 365)
    volume_lot = parse_float(quote[36])
    amount_wan = parse_float(quote[57]) or parse_float(quote[37])

    return RefreshedStock(
        meta=meta,
        price=price,
        one_month_return=one_month_return,
        three_month_return=three_month_return,
        market_cap_yi=market_cap_yi,
        dynamic_pe=dynamic_pe,
        quote_time=quote_time,
        target=target_for(meta.code),
        daily_return=daily_return,
        six_month_return=six_month_return,
        one_year_return=one_year_return,
        volume_lot=volume_lot,
        amount_wan=amount_wan,
        product_mix=meta.product_mix,
    )


def target_for(code: str | None) -> TargetPrice | None:
    if code is None:
        return None
    target = VERIFIED_TARGETS.get(code)
    if target is None or target.report_date < TARGET_CUTOFF:
        return None
    return target


def calculate_return(kline: list[list[Any]], end_date: date, lookback_days: int) -> float | None:
    closes = [(date.fromisoformat(row[0]), float(row[2])) for row in kline if len(row) >= 3]
    if not closes:
        return None
    target_date = end_date - timedelta(days=lookback_days)
    base_candidates = [
        (trade_date, close) for trade_date, close in closes if trade_date <= target_date
    ]
    base_close = base_candidates[-1][1] if base_candidates else closes[0][1]
    last_close = closes[-1][1]
    if base_close <= 0:
        return None
    return (last_close / base_close - 1) * 100


def validate_refreshed_rows(rows: list[RefreshedStock]) -> list[str]:
    issues: list[str] = []
    for row in rows:
        meta = row.meta
        label = f"{meta.name}({meta.code or '未上市'})"
        if meta.code is None:
            if any(value is not None for value in (row.price, row.market_cap_yi, row.dynamic_pe)):
                issues.append(f"{label}: unlisted company must not have quote fields")
            continue

        if not re.fullmatch(r"\d{6}", meta.code):
            issues.append(f"{label}: invalid stock code")
        if row.price is None or row.price <= 0:
            issues.append(f"{label}: missing or invalid price")
        if row.market_cap_yi is None or row.market_cap_yi <= 0:
            issues.append(f"{label}: missing or invalid market cap")
        if row.dynamic_pe is None:
            issues.append(f"{label}: missing dynamic PE")
        if row.one_month_return is None:
            issues.append(f"{label}: missing one-month return")
        if row.three_month_return is None:
            issues.append(f"{label}: missing three-month return")
        if row.daily_return is None:
            issues.append(f"{label}: missing daily return")
        if row.volume_lot is None:
            issues.append(f"{label}: missing trading volume")
        if row.amount_wan is None:
            issues.append(f"{label}: missing trading amount")

        if row.target is not None:
            if row.target.report_date < TARGET_CUTOFF:
                issues.append(f"{label}: target price report is older than {TARGET_CUTOFF}")
            if row.price is not None and row.target.value < row.price:
                issues.append(f"{label}: target price is below current price")
    return issues


def format_price(price: float | None) -> str:
    return "N/A" if price is None else f"¥{price:.2f}"


def format_return(value: float | None) -> str:
    if value is None:
        return "N/A"
    rounded = round(value, 1)
    if rounded == 0:
        return "0%"
    return f"{rounded:+.1f}%"


def format_share_percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    rounded = round(value, 1)
    if rounded == 0:
        return "0%"
    return f"{rounded:.1f}%"


def format_market_cap(value: float | None) -> str:
    if value is None:
        return "N/A"
    if value >= 10_000:
        return f"{value / 10_000:.2f}万亿"
    return f"{round(value):.0f}亿"


def format_volume_lot(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.0f}"


def format_amount_wan(value: float | None) -> str:
    if value is None:
        return "N/A"
    yi = value / 10_000
    if abs(yi) >= 1:
        return f"{yi:.2f}亿"
    return f"{value:.0f}万"


def format_pe(value: float | None) -> str:
    if value is None:
        return "N/A"
    if value <= 0:
        return "亏损"
    if value >= 100:
        return f"{value:.0f}x"
    return f"{value:.1f}x"


def format_target(target: TargetPrice | None) -> str:
    if target is None:
        return ""
    return f"¥{target.value:g}({target.broker}/{target.report_date:%Y-%m-%d})"


def display_name(meta: StockMeta) -> str:
    if meta.code is None:
        return meta.name
    return f"{meta.name}({meta.code})"


def valuation_signal(row: RefreshedStock) -> str:
    if row.meta.valuation_signal:
        return row.meta.valuation_signal
    pe = row.dynamic_pe
    if pe is None:
        return "估值待取数"
    if pe <= 0:
        return "亏损/扭亏弹性待验证"
    if pe >= 150:
        return "高PE，需盈利上修消化估值"
    if pe >= 80:
        return "中高PE，订单兑现决定弹性"
    if pe <= 50:
        return "PE相对可消化，关注业绩上修"
    return "估值中性，跟踪订单与利润率"


def davis_signal(row: RefreshedStock) -> str:
    if row.meta.davis_signal:
        return row.meta.davis_signal
    if row.dynamic_pe is None:
        return "待估值数据确认"
    if row.dynamic_pe <= 0:
        return "先看扭亏拐点，暂不判双击"
    medium_momentum = (row.three_month_return or 0) > 20 or (row.six_month_return or 0) > 35
    strong_momentum = (row.six_month_return or 0) > 80 or (row.one_year_return or 0) > 120
    if strong_momentum and row.dynamic_pe >= 100:
        return "价格已先行，需盈利继续上修"
    if medium_momentum and row.dynamic_pe <= 80:
        return "动量+估值可消化，双击观察"
    if medium_momentum:
        return "动量确认，等待盈利上修匹配"
    return "等待盈利/估值同向确认"


def html_row(row: RefreshedStock) -> list[str]:
    meta = row.meta
    return [
        meta.sector,
        meta.subsector,
        display_name(meta),
        format_price(row.price),
        format_return(row.one_month_return),
        format_return(row.three_month_return),
        format_market_cap(row.market_cap_yi),
        "未上市" if meta.code is None else format_pe(row.dynamic_pe),
        meta.summary,
        meta.rank,
        meta.scarcity,
        "N/A" if meta.code is None else format_target(row.target),
        meta.rating,
    ]


def html_cn_row(row: RefreshedStock) -> list[str]:
    meta = row.meta
    return [
        meta.sector,
        meta.subsector,
        display_name(meta),
        format_price(row.price),
        format_return(row.daily_return),
        format_return(row.one_month_return),
        format_return(row.three_month_return),
        format_return(row.six_month_return),
        format_return(row.one_year_return),
        format_volume_lot(row.volume_lot),
        format_amount_wan(row.amount_wan),
        format_market_cap(row.market_cap_yi),
        "未上市" if meta.code is None else format_pe(row.dynamic_pe),
        meta.summary,
        row.product_mix,
        meta.rank,
        meta.scarcity,
        "N/A" if meta.code is None else format_target(row.target),
        valuation_signal(row),
        davis_signal(row),
        meta.rating,
    ]


def markdown_row(row: RefreshedStock) -> list[str]:
    meta = row.meta
    code = meta.code or "未上市"
    return [
        meta.sector,
        meta.subsector,
        display_name(meta),
        code,
        format_price(row.price),
        format_return(row.daily_return),
        format_return(row.one_month_return),
        format_return(row.three_month_return),
        format_return(row.six_month_return),
        format_return(row.one_year_return),
        format_volume_lot(row.volume_lot),
        format_amount_wan(row.amount_wan),
        format_market_cap(row.market_cap_yi),
        "未上市" if meta.code is None else format_pe(row.dynamic_pe),
        meta.summary,
        row.product_mix,
        meta.rank,
        meta.scarcity,
        "N/A" if meta.code is None else format_target(row.target),
        valuation_signal(row),
        davis_signal(row),
        meta.rating,
    ]


def update_html(rows: list[RefreshedStock], refresh_date: date, path: Path = REPORT_HTML) -> None:
    text = path.read_text(encoding="utf-8")
    active_rows = [row for row in rows if row.meta.active]
    cn_data = ",\n".join(
        "  " + json.dumps(html_cn_row(row), ensure_ascii=False) for row in active_rows
    )
    text = re.sub(r"var CN=\[[\s\S]*?\];", f"var CN=[\n{cn_data}\n];", text)
    text = re.sub(r"数据截止：\d{4}-\d{2}-\d{2}", f"数据截止：{refresh_date:%Y-%m-%d}", text)
    text = re.sub(
        r"A股股价、总市值、动态PE、近一月/近三月涨跌幅已按腾讯证券行情与复权日K刷新。",
        "A股股价、当日涨跌幅、成交量、成交额、总市值、动态PE、近一月/近三月/近半年/近一年涨跌幅已按腾讯证券行情与复权日K刷新。",
        text,
    )
    text = re.sub(
        r"A股股价、总市值、动态PE、近一月/近三月/近半年/近一年涨跌幅已按腾讯证券行情与复权日K刷新。",
        "A股股价、当日涨跌幅、成交量、成交额、总市值、动态PE、近一月/近三月/近半年/近一年涨跌幅已按腾讯证券行情与复权日K刷新。",
        text,
    )
    text = re.sub(
        r"A股股价与总市值已按腾讯证券收盘行情刷新；近一月/近三月涨跌幅和目标价仍需后续用同一历史行情源重算。",
        "A股股价、当日涨跌幅、成交量、成交额、总市值、动态PE、近一月/近三月/近半年/近一年涨跌幅已按腾讯证券行情与复权日K刷新。",
        text,
    )
    product_mix_note = (
        "<p>产品线营收/净利份额比例来自东方财富 F10 主营构成；"
        "其中“利润”为主营利润/毛利口径，不等同归母净利。</p>"
    )
    market_data_note = (
        f"<p>数据截止：{refresh_date:%Y-%m-%d}。"
        "A股股价、当日涨跌幅、成交量、成交额、总市值、动态PE、"
        "近一月/近三月/近半年/近一年涨跌幅已按腾讯证券行情与复权日K刷新。</p>"
    )
    if product_mix_note not in text:
        text = text.replace(market_data_note, f"{market_data_note}\n  {product_mix_note}")
    old_target_note = (
        r"目标价来源：Goldman Sachs、Morgan Stanley、UBS、Bernstein、中信证券、"
        r"中金公司、华泰证券、国泰君安等机构2026Q1-Q2研报（仅供参考）。"
    )
    new_target_note = (
        "目标价规则：A股仅保留 2026-01-01 之后已核验研报目标价；"
        "未核验或早于该日期的目标价留空。"
    )
    text = re.sub(old_target_note, new_target_note, text)
    text = re.sub(
        r"中美两市\d+家核心标的",
        f"中美两市{len(active_rows) + 18}家核心标的",
        text,
    )
    text = re.sub(
        r"覆盖中美两市 \d+ 家核心标的 · 9 大主线 \+ 基建观察 · \d+ 列关键指标",
        f"覆盖中美两市 {len(active_rows) + 18} 家核心标的 · 9 大主线 + 基建观察 · 21 列关键指标",
        text,
    )
    path.write_text(text, encoding="utf-8")


def md_table(rows: list[RefreshedStock]) -> str:
    header = (
        "| 领域 | 细分版块 | 细分龙头 | 股票代码 | 目前股价(¥) | 当日涨跌幅 | 近一月涨跌幅 | "
        "近三月涨跌幅 | 近半年涨跌幅 | 近一年涨跌幅 | 成交量(手) | 成交额 | "
        "目前市值 | 动态市盈率 | "
        "一季度财报总结 | 产品线营收/净利份额比例 | 行业排行 | 产品紧缺度 | 投研目标股价 | "
        "估值/业绩弹性 | 戴维斯双击观察 | 投资价值评级 |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
    )
    lines = [header]
    for row in rows:
        lines.append("| " + " | ".join(markdown_row(row)) + " |")
    return "\n".join(lines)


def update_markdown(rows: list[RefreshedStock], refresh_date: date, path: Path = CHINA_MD) -> None:
    active_rows = [row for row in rows if row.meta.active]
    target_note = (
        "当前未登记可核验的 2026-01-01 之后 A股券商目标价；为避免旧研报目标价误导，"
        "投研目标股价列已对可交易 A 股留空。"
    )
    content = f"""# 中国 AIDC 产业链核心标的数据表

> **数据截止：{refresh_date:%Y-%m-%d}**  
> 股价、当日涨跌幅、成交量、成交额、总市值、动态PE、
> 近一月/近三月/近半年/近一年涨跌幅已按腾讯证券行情刷新；  
> 行情源为 `web.ifzq.gtimg.cn` 收盘行情与前复权日 K。  
> 产品线营收/净利份额比例来自东方财富 F10 主营构成；
> 其中“利润”为主营利润/毛利口径，不等同归母净利。  
> 目标价规则：仅保留研报日期在 2026-01-01 之后且已核验来源的投研目标价；  
> 未核验或早于该日期的目标价留空。  
> {target_note}  
> 一季度财报指 2026 年 1-3 月（2026Q1）数据。  
> 动态市盈率取腾讯行情接口 PE 字段；亏损或负 PE 显示为“亏损”。  
> 新股上市不足完整观察周期时，区间涨跌幅按可得最早前复权日 K 估算。

---

## 中国 AIDC 产业链核心标的

> 领域排序按当前大A轮动热度维护：光通信 → 内存/半导体 → 算力/芯片 → PCB →
> 上游材料 → AI服务器 → 半导体设备/封测 → 散热/液冷 → 电源系统；
> AI网络已标记 Deprecated，不进入研报主表。

{md_table(active_rows)}

---

## 数据说明与风险提示

### 价格数据备注

- {refresh_date:%Y-%m-%d} 收盘价、当日涨跌幅、成交量、成交额、总市值、动态PE来自腾讯证券行情接口；
  近一月/近三月/近半年/近一年涨跌幅来自同源前复权日 K。
- “产品线营收/净利份额比例”来自东方财富 F10 `BusinessAnalysis/PageAjax` 的按产品分类；
  其中利润字段为主营利润/毛利口径，不等同归母净利。
- “估值/业绩弹性”“戴维斯双击观察”为人工/agent 后续维护字段；
  脚本仅在字段为空时按 PE 与价格动量给出粗粒度观察，不替代财报和研报核验。
- 代码核验保留：太辰光正确代码为 300570，原表 300003 实为乐普医疗；
  星融元尚未 IPO，原表误配的 688616 实为西力科技且与 RoCE 逻辑不匹配。
- AI网络板块已标记为 Deprecated，脚本保留源数据但不渲染到研报主表。
- 目标价不再用 `[待更新]` 占位；无法确认 2026 年研报日期的目标价直接留空，
  避免出现“推荐但目标价低于现价”的伪信号。
- 每次刷新后运行 `uv run python scripts/refresh_aidc_data.py --check` 做基础一致性校验。

### 投资评级说明

| 评级 | 含义 |
|---|---|
| 强烈推荐 | 未来12个月预期涨幅>30%，基本面强，稀缺度极高 |
| 推荐 | 未来12个月预期涨幅15%—30%，基本面良好 |
| 中性 | 未来12个月预期涨幅0%—15%，建议等待更好买点 |
| 回避 | 估值过高或基本面存在重大风险 |

*本表格仅供投资研究参考，不构成投资建议。股市有风险，入市需谨慎。*
"""
    path.write_text(content, encoding="utf-8")


def update_category_markdowns(rows: list[RefreshedStock], refresh_date: date) -> None:
    stock_yaml = parse_simple_yaml_lists(STOCKS_YAML)
    categories = stock_yaml.get("categories", [])
    for category in categories:
        filename = category.get("file")
        if not filename:
            continue
        category_id = category.get("id")
        category_rows = [row for row in rows if row.meta.category_id == category_id]
        title = str(category.get("name") or category.get("source_category") or category_id)
        if category_id == "out_of_scope":
            title = "源表中未归入截图 9 大领域的条目"
        prefix = [
            f"# {title}",
            "<!-- Auto-generated by scripts/refresh_aidc_data.py from stocks.yaml. -->",
            "",
            f"- 数据截止：`{refresh_date:%Y-%m-%d}`",
            "- 来源文件：`data_china_aidc.md`",
            f"- 源表领域：`{category.get('source_category', '')}`",
            f"- 标的数量：{len(category_rows)}",
        ]
        if category_id == "out_of_scope":
            prefix.append("- 这些条目保留用于溯源，不进入截图定义的 9 大领域分类。")
        prefix.append("")
        content = "\n".join(prefix) + md_table(category_rows) + "\n"
        (CN_DIR / str(filename)).write_text(content, encoding="utf-8")


STOCKS = load_stocks_from_yaml()


def refresh_rows() -> list[RefreshedStock]:
    product_mixes = fetch_product_mixes(STOCKS)
    rows = [fetch_tencent_stock(meta) for meta in STOCKS]
    return [
        replace(row, product_mix=product_mixes.get(row.meta.code or "", row.product_mix))
        for row in rows
    ]


def current_refresh_date(rows: list[RefreshedStock]) -> date:
    dates = [row.quote_time.date() for row in rows if row.quote_time is not None]
    return max(dates) if dates else date.today()


def run(check: bool) -> int:
    rows = refresh_rows()
    issues = validate_refreshed_rows(rows)
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}", file=sys.stderr)
        return 1

    refresh_date = current_refresh_date(rows)
    if not check:
        update_markdown(rows, refresh_date)
        update_category_markdowns(rows, refresh_date)
        update_html(rows, refresh_date)
    active_count = sum(1 for row in rows if row.meta.active)
    print(
        f"Validated {len(rows)} China AIDC rows "
        f"({active_count} active) as of {refresh_date:%Y-%m-%d}."
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh A-share AIDC report data.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fetch and validate data without writing report files.",
    )
    args = parser.parse_args()
    raise SystemExit(run(check=args.check))


if __name__ == "__main__":
    main()
