"""Refresh and validate A-share AIDC report data.

Important data-quality rules:
- Tradeable A-share quote, market-cap, PE, and 1/3-month return fields come from
  Tencent quote/kline endpoints in one refresh pass.
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
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_HTML = ROOT / "aidc_report.html"
CHINA_MD = ROOT / "data_china_aidc.md"
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


def fetch_json(url: str, retries: int = 3) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
            )
        },
    )
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - depends on external network
            last_error = exc
            if attempt < retries:
                time.sleep(attempt)
    if last_error is None:  # pragma: no cover - defensive only
        raise RuntimeError("Tencent quote request failed without an exception")
    raise last_error


def fetch_tencent_stock(meta: StockMeta, end: date | None = None) -> RefreshedStock:
    if meta.code is None:
        return RefreshedStock(meta, None, None, None, None, None, None, None)

    end_date = end or date.today()
    begin_date = end_date - timedelta(days=130)
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
    one_month_return = calculate_return(kline, quote_time.date(), 30)
    three_month_return = calculate_return(kline, quote_time.date(), 90)

    return RefreshedStock(
        meta=meta,
        price=price,
        one_month_return=one_month_return,
        three_month_return=three_month_return,
        market_cap_yi=market_cap_yi,
        dynamic_pe=dynamic_pe,
        quote_time=quote_time,
        target=target_for(meta.code),
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
    if not base_candidates:
        return None
    base_close = base_candidates[-1][1]
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


def format_market_cap(value: float | None) -> str:
    if value is None:
        return "N/A"
    if value >= 10_000:
        return f"{value / 10_000:.2f}万亿"
    return f"{round(value):.0f}亿"


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


def update_html(rows: list[RefreshedStock], refresh_date: date, path: Path = REPORT_HTML) -> None:
    text = path.read_text(encoding="utf-8")
    active_rows = [row for row in rows if row.meta.active]
    cn_data = ",\n".join(
        "  " + json.dumps(html_row(row), ensure_ascii=False) for row in active_rows
    )
    text = re.sub(r"var CN=\[[\s\S]*?\];", f"var CN=[\n{cn_data}\n];", text)
    text = re.sub(r"数据截止：\d{4}-\d{2}-\d{2}", f"数据截止：{refresh_date:%Y-%m-%d}", text)
    text = re.sub(
        r"A股股价与总市值已按腾讯证券收盘行情刷新；近一月/近三月涨跌幅和目标价仍需后续用同一历史行情源重算。",
        "A股股价、总市值、动态PE、近一月/近三月涨跌幅已按腾讯证券行情与复权日K刷新。",
        text,
    )
    old_target_note = (
        r"目标价来源：Goldman Sachs、Morgan Stanley、UBS、Bernstein、中信证券、"
        r"中金公司、华泰证券、国泰君安等机构2026Q1-Q2研报（仅供参考）。"
    )
    new_target_note = (
        "目标价规则：A股仅保留 2026-01-01 之后已核验研报目标价；"
        "未核验或早于该日期的目标价留空。"
    )
    text = re.sub(old_target_note, new_target_note, text)
    path.write_text(text, encoding="utf-8")


def md_table(rows: list[RefreshedStock]) -> str:
    header = (
        "| 领域 | 细分版块 | 细分龙头 | 股票代码 | 目前股价(¥) | 近一月涨跌幅 | 近三月涨跌幅 | "
        "目前市值 | 动态市盈率 | 一季度财报总结 | 行业排行 | 产品紧缺度 | "
        "投研目标股价 | 投资价值评级 |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
    )
    lines = [header]
    for row in rows:
        meta = row.meta
        values = html_row(row)
        code = meta.code or "未上市"
        values = values[:3] + [code] + values[3:]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def update_markdown(rows: list[RefreshedStock], refresh_date: date, path: Path = CHINA_MD) -> None:
    active_rows = [row for row in rows if row.meta.active]
    target_note = (
        "当前未登记可核验的 2026-01-01 之后 A股券商目标价；为避免旧研报目标价误导，"
        "投研目标股价列已对可交易 A 股留空。"
    )
    content = f"""# 中国 AIDC 产业链核心标的数据表

> **数据截止：{refresh_date:%Y-%m-%d}**  
> 股价、总市值、动态PE、近一月/近三月涨跌幅已按腾讯证券行情刷新；  
> 行情源为 `web.ifzq.gtimg.cn` 收盘行情与前复权日 K。  
> 目标价规则：仅保留研报日期在 2026-01-01 之后且已核验来源的投研目标价；  
> 未核验或早于该日期的目标价留空。  
> {target_note}  
> 一季度财报指 2026 年 1-3 月（2026Q1）数据。  
> 动态市盈率取腾讯行情接口 PE 字段；亏损或负 PE 显示为“亏损”。

---

## 中国 AIDC 产业链核心标的

> 领域排序按当前大A轮动热度维护：光通信 → 内存/半导体 → 算力/芯片 → PCB →
> 上游材料 → AI服务器 → 半导体设备/封测 → 散热/液冷 → 电源系统；
> AI网络已标记 Deprecated，不进入研报主表。

{md_table(active_rows)}

---

## 数据说明与风险提示

### 价格数据备注

- {refresh_date:%Y-%m-%d} 收盘价、总市值、动态PE来自腾讯证券行情接口；
  近一月/近三月涨跌幅来自同源前复权日 K。
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


def refresh_rows() -> list[RefreshedStock]:
    return [fetch_tencent_stock(meta) for meta in STOCKS]


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
        update_html(rows, refresh_date)
        update_markdown(rows, refresh_date)
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
