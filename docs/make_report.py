# -*- coding: utf-8 -*-
"""게런티 함수 보고서 PDF 생성 — 연매출 100억·순수익 50억, 3/5/7개사 비교"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont("Nanum", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"))
pdfmetrics.registerFont(TTFont("NanumB", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"))

EOK = 100_000_000
REVENUE = 100 * EOK      # 연매출
NET = 50 * EOK           # 순수익 (분배 재원)
FEE_BPS = 300            # 3%

# ------------------------------------------------------------------
# 게런티 함수 (guarantee-distribution.mjs 와 동일 규칙, arrears 없음 가정)
# ------------------------------------------------------------------
def settle(partners, revenue, fee_bps):
    fee = revenue * fee_bps // 10_000
    budget = revenue - fee
    total_g = sum(p["g"] for p in partners)
    rows = []
    if budget >= total_g:
        surplus = budget - total_g
        total_w = sum(p["w"] for p in partners)
        dist = 0
        for i, p in enumerate(partners):
            s = surplus * p["w"] // total_w
            if i == len(partners) - 1:
                s = surplus - dist
            dist += s
            rows.append({**p, "gpaid": p["g"], "spaid": s, "arrear": 0})
    else:
        paid = 0
        for i, p in enumerate(partners):
            gp = budget * p["g"] // total_g
            if i == len(partners) - 1:
                gp = budget - paid
            paid += gp
            rows.append({**p, "gpaid": gp, "spaid": 0, "arrear": p["g"] - gp})
    return fee, budget, rows

SCENARIOS = {
    "3개사": [
        {"id": "아티스트A", "g": 5*EOK, "w": 3},
        {"id": "아티스트B", "g": 3*EOK, "w": 2},
        {"id": "기획·운영", "g": 2*EOK, "w": 5},
    ],
    "5개사": [
        {"id": "아티스트A", "g": 5*EOK, "w": 3},
        {"id": "아티스트B", "g": 3*EOK, "w": 2},
        {"id": "아티스트C", "g": 2*EOK, "w": 2},
        {"id": "콘텐츠제작D", "g": 2*EOK, "w": 2},
        {"id": "기획·운영", "g": 2*EOK, "w": 5},
    ],
    "7개사": [
        {"id": "아티스트A", "g": 5*EOK, "w": 3},
        {"id": "아티스트B", "g": 3*EOK, "w": 2},
        {"id": "아티스트C", "g": 2*EOK, "w": 2},
        {"id": "콘텐츠제작D", "g": 2*EOK, "w": 2},
        {"id": "유통E", "g": 1.5*EOK, "w": 1.5},
        {"id": "기술F", "g": 1.5*EOK, "w": 1.5},
        {"id": "기획·운영", "g": 2*EOK, "w": 5},
    ],
}
for sc in SCENARIOS.values():
    for p in sc:
        p["g"] = int(p["g"])

def eok(v, nd=2):
    s = f"{v/EOK:,.{nd}f}".rstrip("0").rstrip(".")
    return s + "억"

# ------------------------------------------------------------------
# 스타일
# ------------------------------------------------------------------
INK = colors.HexColor("#1a1a1a")
ACCENT = colors.HexColor("#7a5c3e")
LIGHT = colors.HexColor("#f3ede4")
LINE = colors.HexColor("#d8cfc2")

def st(name, **kw):
    base = dict(fontName="Nanum", fontSize=10, leading=16, textColor=INK)
    base.update(kw)
    return ParagraphStyle(name, **base)

S_TITLE = st("t", fontName="NanumB", fontSize=20, leading=28)
S_SUB   = st("s", fontSize=10.5, textColor=colors.HexColor("#666666"))
S_H1    = st("h1", fontName="NanumB", fontSize=14, leading=20, spaceBefore=8,
             textColor=ACCENT)
S_H2    = st("h2", fontName="NanumB", fontSize=11.5, leading=17)
S_BODY  = st("b")
S_FORM  = st("f", fontName="NanumB", fontSize=11, leading=20,
             backColor=LIGHT, borderPadding=8)
S_NOTE  = st("n", fontSize=8.5, leading=13, textColor=colors.HexColor("#777777"))

def table_style(header_rows=1):
    return TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "Nanum"),
        ("FONTNAME", (0,0), (-1,header_rows-1), "NanumB"),
        ("FONTSIZE", (0,0), (-1,-1), 9.5),
        ("BACKGROUND", (0,0), (-1,header_rows-1), LIGHT),
        ("TEXTCOLOR", (0,0), (-1,-1), INK),
        ("LINEBELOW", (0,0), (-1,header_rows-1), 0.8, ACCENT),
        ("LINEBELOW", (0,header_rows), (-1,-2), 0.3, LINE),
        ("LINEABOVE", (0,-1), (-1,-1), 0.8, ACCENT),
        ("FONTNAME", (0,-1), (-1,-1), "NanumB"),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ])

doc = SimpleDocTemplate(
    "/home/user/ryun_ir/docs/게런티함수_수익배분_비교보고서.pdf",
    pagesize=A4, topMargin=18*mm, bottomMargin=18*mm,
    leftMargin=18*mm, rightMargin=18*mm,
    title="게런티 함수 기반 수익배분 비교 보고서",
)
E = []

E.append(Paragraph("게런티 함수 기반 수익배분 비교 보고서", S_TITLE))
E.append(Spacer(1, 4))
E.append(Paragraph("연매출 100억 · 순수익 50억 기준 — 파트너 3·5·7개사 시나리오 | RYUN · 2026. 7.", S_SUB))
E.append(Spacer(1, 14))

# ------------------------------------------------------------------
# 1. 게런티 함수 (최우선 배치)
# ------------------------------------------------------------------
E.append(Paragraph("1. 게런티 함수", S_H1))
E.append(Spacer(1, 4))
E.append(Paragraph(
    "정산 예산 &nbsp;B = R × (1 - f) &nbsp;&nbsp;(R: 회차 수익, f: 플랫폼 수수료율)<br/>"
    "<br/>"
    "① 미지급 상환 &nbsp;&nbsp;pay<sub>i</sub> = min(B, ΣA) × A<sub>i</sub> / ΣA<br/>"
    "② 게런티 지급 &nbsp;&nbsp;pay<sub>i</sub> = min(B′, ΣG) × G<sub>i</sub> / ΣG, &nbsp;"
    "부족분 (G<sub>i</sub> - pay<sub>i</sub>) → A<sub>i</sub> 누적<br/>"
    "③ 초과 배분 &nbsp;&nbsp;pay<sub>i</sub> = S × w<sub>i</sub> / Σw &nbsp;&nbsp;(S = B′ - ΣG)",
    S_FORM))
E.append(Spacer(1, 8))
E.append(Paragraph("정의", S_H2))
E.append(Paragraph(
    "게런티 함수는 회차 수익을 세 단계 우선순위로 배분하는 규칙이다. "
    "G<sub>i</sub>는 파트너 i의 회차당 최소 보장금(게런티), w<sub>i</sub>는 초과 수익 분배 "
    "가중치(N값), A<sub>i</sub>는 예산 부족으로 지급하지 못해 누적된 미지급 게런티다. "
    "조정 가능한 것은 이 세 파라미터와 수수료율뿐이며, 배분 절차 자체는 변경할 수 없다.",
    S_BODY))
E.append(Spacer(1, 6))
E.append(Paragraph("설명", S_H2))
E.append(Paragraph(
    "예산이 게런티 총액에 미달하는 회차에는 게런티를 비례 배분하고, 못 받은 차액은 "
    "소멸하지 않고 블록체인에 부채(A<sub>i</sub>)로 기록되어 다음 회차에 최우선 상환된다. "
    "예산이 충분한 회차에는 게런티를 전액 지급한 뒤 남는 초과 수익을 가중치에 비례해 "
    "전액 배분하므로, 매출(유통)이 커질수록 파트너 몫도 함께 커진다. "
    "모든 지급 내역이 스마트 컨트랙트 이벤트로 공개 기록되어 누구나 검증할 수 있고, "
    "플랫폼 수수료는 코드에서 상한 5%로 강제된다 — 독점 티켓팅 플랫폼 구조에 대한 대안이다.",
    S_BODY))
E.append(Spacer(1, 12))

# ------------------------------------------------------------------
# 2. 공통 전제
# ------------------------------------------------------------------
E.append(Paragraph("2. 공통 전제", S_H1))
E.append(Spacer(1, 4))
fee_preview = NET * FEE_BPS // 10_000
E.append(Paragraph(
    f"연매출 100억 원 중 순수익 50억 원을 연 1회 정산의 분배 재원으로 투입한다. "
    f"플랫폼 수수료 3%({eok(fee_preview)})를 차감한 {eok(NET - fee_preview)}이 정산 예산이며, "
    f"미지급 누적(A)은 0에서 시작한다. 게런티·가중치는 예시 구성이며 실제 계약값으로 교체 가능하다.",
    S_BODY))
E.append(Spacer(1, 12))

# ------------------------------------------------------------------
# 3. 시나리오별 표
# ------------------------------------------------------------------
E.append(Paragraph("3. 파트너 수별 배분 결과", S_H1))
E.append(Spacer(1, 6))

summary = []
for idx, (name, partners) in enumerate(SCENARIOS.items()):
    fee, budget, rows = settle(partners, NET, FEE_BPS)
    total_g = sum(r["gpaid"] for r in rows)
    total_s = sum(r["spaid"] for r in rows)
    data = [["파트너", "게런티(G)", "가중치(N)", "게런티 지급", "초과 배분", "합계", "비중"]]
    for r in rows:
        tot = r["gpaid"] + r["spaid"]
        data.append([r["id"], eok(r["g"]), f'{r["w"]:g}', eok(r["gpaid"]),
                     eok(r["spaid"]), eok(tot), f"{tot/NET*100:.1f}%"])
    data.append(["합계 (수수료 포함 50억)", eok(sum(r['g'] for r in rows)),
                 f'{sum(r["w"] for r in rows):g}',
                 eok(total_g), eok(total_s), eok(total_g + total_s),
                 f"{(total_g+total_s)/NET*100:.1f}%"])
    tbl = Table(data, colWidths=[38*mm, 22*mm, 20*mm, 24*mm, 24*mm, 24*mm, 18*mm])
    tbl.setStyle(table_style())
    block = [Paragraph(f"3-{idx+1}. {name} 구성", S_H2), Spacer(1, 4), tbl,
             Spacer(1, 2),
             Paragraph(f"수수료 {eok(fee)} 차감 후 예산 {eok(budget)} = "
                       f"게런티 {eok(total_g)} + 초과 배분 {eok(total_s)}", S_NOTE),
             Spacer(1, 10)]
    E.append(KeepTogether(block))
    summary.append((name, len(rows), sum(r["g"] for r in rows), total_s,
                    max(rows, key=lambda r: r["gpaid"]+r["spaid"]),
                    min(rows, key=lambda r: r["gpaid"]+r["spaid"])))

# ------------------------------------------------------------------
# 4. 비교 요약
# ------------------------------------------------------------------
E.append(Paragraph("4. 비교 요약", S_H1))
E.append(Spacer(1, 4))
data = [["구분", "3개사", "5개사", "7개사"]]
rows3 = {name: settle(p, NET, FEE_BPS)[2] for name, p in SCENARIOS.items()}
line = lambda label, fn: data.append([label] + [fn(rows3[n]) for n in SCENARIOS])
line("게런티 총액(ΣG)", lambda rs: eok(sum(r["g"] for r in rs)))
line("초과 배분 재원(S)", lambda rs: eok(sum(r["spaid"] for r in rs)))
line("최대 수령 파트너", lambda rs: (lambda m: f'{m["id"]} {eok(m["gpaid"]+m["spaid"])}')(max(rs, key=lambda r: r["gpaid"]+r["spaid"])))
line("최소 수령 파트너", lambda rs: (lambda m: f'{m["id"]} {eok(m["gpaid"]+m["spaid"])}')(min(rs, key=lambda r: r["gpaid"]+r["spaid"])))
line("파트너당 평균 수령", lambda rs: eok(sum(r["gpaid"]+r["spaid"] for r in rs)//len(rs)))
line("아티스트A 수령액", lambda rs: eok(next(r["gpaid"]+r["spaid"] for r in rs if r["id"]=="아티스트A")))
tbl = Table(data, colWidths=[46*mm, 42*mm, 42*mm, 42*mm])
ts = table_style()
ts.add("ALIGN", (1,1), (-1,-1), "RIGHT")
ts.add("FONTNAME", (0,-1), (-1,-1), "Nanum")
tbl.setStyle(ts)
E.append(tbl)
E.append(Spacer(1, 8))
E.append(Paragraph(
    "파트너가 늘수록 게런티 총액(하방 보장)이 커지는 대신 초과 배분 재원이 줄어, "
    "기존 파트너의 몫은 완만하게 감소한다(아티스트A 기준 16.55억 → 12.39억 → 10.56억). "
    "순수익 50억 규모에서는 세 구성 모두 게런티가 전액 지급되고 미지급 누적이 발생하지 "
    "않으므로, 실질 배분은 가중치(N값) 설계가 좌우한다.",
    S_BODY))
E.append(Spacer(1, 10))
E.append(Paragraph(
    "본 보고서의 수치는 contracts/RyunGuaranteeDistribution.sol 의 정산 규칙과 동일한 "
    "계산으로 산출되었다. 게런티·가중치는 예시값이며, 실제 계약 조건 입력 시 동일 함수로 재계산된다.",
    S_NOTE))

doc.build(E)
print("PDF written")
