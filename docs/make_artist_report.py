# -*- coding: utf-8 -*-
"""륜 게런티 함수(수기 원본) 보고서 PDF — 부산·서울 아티스트, 티켓 수별 비교"""
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

MAN = 10_000
BASE_BUSAN, BASE_SEOUL, PER_TICKET = 10*MAN, 20*MAN, 2*MAN
M, MP = 5, 2  # 부산 5인, 서울 2인

def guarantee(tickets, music=0):
    n = M + MP
    alpha = PER_TICKET * tickets / n
    ms = music / n
    return {
        "alpha": alpha, "ms": ms,
        "busan": BASE_BUSAN + alpha + ms,
        "seoul": BASE_SEOUL + alpha + ms,
        "P": (BASE_BUSAN + alpha) * M,
        "S": (BASE_SEOUL + alpha) * MP,
        "total": (BASE_BUSAN + alpha) * M + (BASE_SEOUL + alpha) * MP + music,
    }

def man(v):
    s = f"{v/MAN:,.2f}".rstrip("0").rstrip(".")
    return s + "만"

INK = colors.HexColor("#1a1a1a"); ACCENT = colors.HexColor("#7a5c3e")
LIGHT = colors.HexColor("#f3ede4"); LINE = colors.HexColor("#d8cfc2")

def st(name, **kw):
    base = dict(fontName="Nanum", fontSize=10, leading=16, textColor=INK)
    base.update(kw); return ParagraphStyle(name, **base)

S_TITLE = st("t", fontName="NanumB", fontSize=20, leading=28)
S_SUB   = st("s", fontSize=10.5, textColor=colors.HexColor("#666666"))
S_H1    = st("h1", fontName="NanumB", fontSize=14, leading=20, spaceBefore=8, textColor=ACCENT)
S_H2    = st("h2", fontName="NanumB", fontSize=11.5, leading=17)
S_BODY  = st("b")
S_FORM  = st("f", fontName="NanumB", fontSize=11, leading=20, backColor=LIGHT, borderPadding=8)
S_NOTE  = st("n", fontSize=8.5, leading=13, textColor=colors.HexColor("#777777"))

def tstyle(hdr=1):
    return TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "Nanum"),
        ("FONTNAME", (0,0), (-1,hdr-1), "NanumB"),
        ("FONTSIZE", (0,0), (-1,-1), 9.5),
        ("BACKGROUND", (0,0), (-1,hdr-1), LIGHT),
        ("LINEBELOW", (0,0), (-1,hdr-1), 0.8, ACCENT),
        ("LINEBELOW", (0,hdr), (-1,-2), 0.3, LINE),
        ("LINEABOVE", (0,-1), (-1,-1), 0.8, ACCENT),
        ("FONTNAME", (0,-1), (-1,-1), "NanumB"),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ])

doc = SimpleDocTemplate(
    "/home/user/ryun_ir/docs/륜_게런티함수_보고서.pdf",
    pagesize=A4, topMargin=18*mm, bottomMargin=18*mm, leftMargin=18*mm, rightMargin=18*mm,
    title="륜 게런티 함수 보고서",
)
E = []
E.append(Paragraph("륜 게런티 함수 보고서", S_TITLE))
E.append(Spacer(1, 4))
E.append(Paragraph("부산 5인 · 서울 2인 아티스트 — 티켓 수별 수익배분 | RYUN · 2026. 7.", S_SUB))
E.append(Spacer(1, 14))

# 1. 게런티 함수 (원본)
E.append(Paragraph("1. 게런티 함수 (원본)", S_H1))
E.append(Spacer(1, 4))
E.append(Paragraph(
    "Ⅰ. 기본 지출 항목<br/>"
    "&nbsp;&nbsp;&nbsp;P(부산) = 10만원 × m + m·α &nbsp;&nbsp;(m = 부산 아티스트 수 = 5)<br/>"
    "&nbsp;&nbsp;&nbsp;S(서울) = 20만원 × m′ + m′·α &nbsp;&nbsp;(m′ = 서울 아티스트 수 = 2)<br/>"
    "&nbsp;&nbsp;&nbsp;P + S = 기본 지출 합계<br/>"
    "<br/>"
    "Ⅱ. α (러닝 게런티) = 2만원 × n″ ÷ (m + m′) &nbsp;&nbsp;(n″ = 티케팅 수)<br/>"
    "<br/>"
    "Ⅲ. 음원 판매 수익 = 별도 수익 풀, 아티스트 균등 분배",
    S_FORM))
E.append(Spacer(1, 8))
E.append(Paragraph("정의", S_H2))
E.append(Paragraph(
    "아티스트 1인의 수령액은 <b>지역별 기본 게런티</b>(부산 10만원, 서울 20만원)에 "
    "<b>러닝 게런티 α</b>를 더한 값이다. α는 티켓 1장당 2만원씩 적립된 재원을 전체 아티스트 "
    "수(m + m′)로 나눈 균등 분배액으로, 티켓 판매량에 정비례해 커진다. "
    "음원 판매 수익(Ⅲ)이 발생하면 같은 방식으로 균등하게 더해진다.",
    S_BODY))
E.append(Spacer(1, 6))
E.append(Paragraph("설명", S_H2))
E.append(Paragraph(
    "기본 게런티는 티켓이 한 장도 팔리지 않아도 보장되는 하방선이고, 러닝 게런티는 "
    "흥행 성과를 모든 출연 아티스트가 동일하게 나누는 상방 참여분이다. 지역별 기본액 차이는 "
    "이동·체류 비용을 반영한다. 이 규칙은 블록체인 스마트 컨트랙트 "
    "(contracts/RyunArtistGuarantee.sol)로 구현되어, 정산 즉시 모든 지급 내역이 공개 기록되고 "
    "파라미터(기본액·티켓 단가)만 조정할 수 있다 — 공식 자체는 누구도 임의로 바꿀 수 없다.",
    S_BODY))
E.append(Spacer(1, 12))

# 2. 티켓 수별 배분
E.append(Paragraph("2. 티켓 수별 배분 결과", S_H1))
E.append(Spacer(1, 6))
data = [["티켓 수", "α(1인)", "부산 1인", "서울 1인", "P(부산 5인)", "S(서울 2인)", "총 지출"]]
for t in [0, 100, 200, 300, 500]:
    r = guarantee(t)
    data.append([f"{t}장", man(r["alpha"]), man(r["busan"]), man(r["seoul"]),
                 man(r["P"]), man(r["S"]), man(r["total"])])
tbl = Table(data, colWidths=[20*mm, 24*mm, 25*mm, 25*mm, 28*mm, 28*mm, 24*mm])
tbl.setStyle(tstyle())
E.append(tbl)
E.append(Spacer(1, 4))
E.append(Paragraph("단위: 만원. 총 지출 = 90만원(기본) + 2만원 × 티켓 수 — 티켓 수에 정비례.", S_NOTE))
E.append(Spacer(1, 12))

# 3. 음원 수익 포함
E.append(Paragraph("3. 음원 판매 수익 포함 (티켓 300장 기준)", S_H1))
E.append(Spacer(1, 6))
data = [["음원 수익", "1인 추가분", "부산 1인", "서울 1인", "총 지출"]]
for music in [0, 35*MAN, 70*MAN, 140*MAN]:
    r = guarantee(300, music)
    data.append([man(music) if music else "없음", man(r["ms"]),
                 man(r["busan"]), man(r["seoul"]), man(r["total"])])
tbl = Table(data, colWidths=[30*mm, 30*mm, 30*mm, 30*mm, 30*mm])
tbl.setStyle(tstyle())
E.append(tbl)
E.append(Spacer(1, 12))

# 4. 해설
E.append(Paragraph("4. 해설", S_H1))
E.append(Spacer(1, 4))
E.append(Paragraph(
    "티켓 100장이면 α는 28.57만원으로 부산 아티스트 수령액(38.57만원)이 기본 게런티의 약 4배가 "
    "되고, 300장이면 서울·부산 모두 100만원 안팎에 도달한다. 성과가 커질수록 지역별 기본액 "
    "차이(10만원)의 비중은 줄어들어 사실상 균등 분배에 수렴한다 — 흥행의 과실을 전원이 "
    "동일하게 나누는 구조다. 모든 수치는 컨트랙트의 preview() 함수로 정산 전에 확인할 수 있다.",
    S_BODY))
E.append(Spacer(1, 10))
E.append(Paragraph(
    "본 보고서의 수치는 contracts/RyunArtistGuarantee.sol · ryun-guarantee-function.mjs 와 동일한 "
    "계산으로 산출되었다. 기본 게런티(10만·20만원)와 티켓 단가(2만원)는 파라미터로 조정 가능하다.",
    S_NOTE))

doc.build(E)
print("PDF written")
