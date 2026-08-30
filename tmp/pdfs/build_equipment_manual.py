from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

OUT = r"D:\Temp\設備管理系統_使用手冊_v1.0.pdf"
pdfmetrics.registerFont(UnicodeCIDFont("MSung-Light"))
FONT = "MSung-Light"

styles = getSampleStyleSheet()
base = ParagraphStyle("base", parent=styles["BodyText"], fontName=FONT, fontSize=10.2, leading=17, spaceAfter=7)
title = ParagraphStyle("title", parent=base, fontSize=25, leading=34, alignment=TA_CENTER, textColor=colors.HexColor("17365D"), spaceAfter=14)
subtitle = ParagraphStyle("subtitle", parent=base, fontSize=12, leading=20, alignment=TA_CENTER, textColor=colors.HexColor("666666"))
h1 = ParagraphStyle("h1", parent=base, fontSize=17, leading=25, textColor=colors.HexColor("17365D"), spaceBefore=18, spaceAfter=10)
h2 = ParagraphStyle("h2", parent=base, fontSize=13, leading=21, textColor=colors.HexColor("1F4E79"), spaceBefore=14, spaceAfter=7)
h3 = ParagraphStyle("h3", parent=base, fontSize=11, leading=18, textColor=colors.HexColor("1F4E79"), spaceBefore=10, spaceAfter=5)
quote = ParagraphStyle("quote", parent=base, leftIndent=12, borderColor=colors.HexColor("9DC3E6"), borderWidth=2, borderPadding=7, backColor=colors.HexColor("F3F8FC"), textColor=colors.HexColor("3F3F3F"))
bullet = ParagraphStyle("bullet", parent=base, leftIndent=16, firstLineIndent=-11, spaceAfter=3)
step = ParagraphStyle("step", parent=base, leftIndent=18, firstLineIndent=-18, spaceAfter=4)
code = ParagraphStyle("code", parent=base, fontName="Courier", fontSize=9, leading=14, leftIndent=14, borderColor=colors.HexColor("D9E2F3"), borderWidth=1, borderPadding=7, backColor=colors.HexColor("F7F9FC"))

def P(text, style=base):
    return Paragraph(text, style)

def table(rows, widths):
    data = [[P(cell, base) for cell in row] for row in rows]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("1F4E79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("C9D7E6")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("F6F9FC")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("C9D7E6"))
    canvas.line(doc.leftMargin, 1.25 * cm, A4[0] - doc.rightMargin, 1.25 * cm)
    canvas.setFont(FONT, 8.5)
    canvas.setFillColor(colors.HexColor("666666"))
    canvas.drawString(doc.leftMargin, 0.78 * cm, "設備管理系統（warehouse）使用手冊｜版本 1.0")
    canvas.drawRightString(A4[0] - doc.rightMargin, 0.78 * cm, f"第 {doc.page} 頁")
    canvas.restoreState()

story = []
story += [Spacer(1, 4.2*cm), P("設備管理系統", title), P("使用手冊", title), Spacer(1, 0.5*cm),
          P("系統名稱：設備管理系統（warehouse）<br/>版本：1.0<br/>更新日期：2026-08-30", subtitle), PageBreak()]

story += [P("目錄", h1), P("1. 系統主要功能", base), P("2. 使用方式", base), P("　2.1 儀表板的使用", base), P("　2.2 資料／記錄的輸入方式", base), P("　2.3 自然語言查詢", base), Spacer(1, 12)]
story += [P("1. 系統主要功能", h1), P("設備管理系統是一套管理設備與耗材進出倉的工具，主要解決以下問題：")]
for x in [
    "<b>快速登記進出倉：</b>不再需要手動翻閱手寫單、逐一判讀；系統透過 AI Agent 自動辨識照片內容，經人工確認後即可入帳。",
    "<b>完整物料清單：</b>所有設備（有編號，如鑽機 #21）和耗材（數量管理，如二重管 3M）統一管理。",
    "<b>設備流動軌跡：</b>每台設備經歷過哪些案場、何時出、何時回，一目了然。",
    "<b>儀表板：</b>隨時掌握哪些設備在外沒回、什麼待修、什麼耗材快沒了。",
    "<b>報表匯出：</b>依案號、品名、類型分組統計，可匯出 CSV。",
    "<b>人工調整：</b>所有記錄都可編輯或刪除，並留下修改日誌（audit_log）。",
]: story.append(P("• " + x, bullet))
story += [P("系統三大部分", h2), table([
    ["部分", "說明"], ["中台（本系統）", "網頁介面＋資料庫，所有資料儲存於此。"],
    ["輸入 Agent", "AI 助手，讀手寫單照片→辨識→確認後自動寫入中台。"],
    ["查詢 Agent", "AI 助手，用自然語言問問題，自動查詢中台回答。"],
], [4.2*cm, 11.5*cm]), P("2. 使用方式", h1), P("2.1 儀表板的使用", h2), P("開啟系統後，第一個看到的頁面就是儀表板。")]
story += [P("儀表板看到什麼？", h3), P("儀表板分為四個區塊：")]
story += [P("① 整體概況卡片（頁面最上方）", h3), table([
    ["卡片", "意思", "顏色意義"], ["設備總數", "系統中所有設備的數量", "—"], ["在庫", "目前在倉庫的設備", "綠色"],
    ["在外", "借出未回的設備", "藍色"], ["待修", "故障送修中的設備", "橙色"], ["超過 30 天", "在外超過 30 天，該追回了", "紅色＝需注意"], ["低庫存", "耗材低於安全庫存，該補貨了", "紅色＝需注意"],
], [3.1*cm, 8.1*cm, 4.5*cm]), P("💡 <b>5 秒看法則：</b>首屏掃一眼紅色數字，就知道今天要先處理什麼。", quote)]
for heading, text in [("② 使用最多的器材列表（TOP 10）", "列出異動最頻繁的設備，按異動次數排序。點擊品名可看該設備的歷史軌跡。"), ("③ 耗材本週列表", "顯示本週有進出的耗材：目前庫存、本週進了多少、出了多少。數字紅色＝低於安全庫存。點擊可調整庫存。"), ("④ 最近異動", "最新 10 筆進出記錄，點擊可看原始進出單。")]: story += [P(heading, h3), P(text)]
story += [P("側邊選單", h3), table([
    ["選單", "功能"], ["儀表板", "回到首頁"], ["快速開單", "手動建立進出單"], ["進出單", "查看所有進出單，可搜尋／編輯／刪除"], ["設備", "查看所有設備，可篩選／編輯／刪除"], ["耗材庫存", "查看耗材庫存，可調整／編輯／刪除"], ["異動紀錄", "查看所有異動紀錄，可編輯／刪除"], ["報表", "統計報表，可匯出 CSV"], ["設備設置", "新增器材、設定初始庫存、調整數量"],
], [4.2*cm, 11.5*cm])]

story += [P("2.2 資料／記錄的輸入方式", h2), P("系統有三種方式輸入記錄："), P("方式一：快速開單（手動輸入）", h3), P("適用於：你手上有正式進出單，或現場直接操作時。")]
for i, text in enumerate(["點左側「快速開單」。", "選擇<b>類型</b>：出倉、進倉、回倉、轉移、報廢、送修或修回。", "填寫<b>日期</b>（預設今天）。", "填寫<b>案號</b>（可從清單選，或直接打字）。", "填寫<b>借用人</b>（簽名人）。", "在「明細」區塊，點「＋ 新增明細」。", "在品名欄輸入文字，從清單點選正確品名。", "填數量、編號（設備才需要，耗材不用）、狀況備註（如「故障」「壞」）。", "可重複新增多筆明細。", "點「確認入帳」直接寫入，或「存草稿」稍後再確認。"], 1): story.append(P(f"{i}. {text}", step))
story += [P("⚠ 若選「轉移」，還必須填寫來源案號、目的地案號、移交人及接收人；轉移必須填寫雙方負責人。", quote), P("💡 <b>品名一定要從清單選</b>，不能只直接打字。系統需要知道「洗網機」實際對應到哪個器材。", quote)]
story += [P("方式二：AI Agent 照片輸入（推薦）", h3), P("適用於：現場人員拍照回傳的手寫單。")]
for i, text in enumerate(["收到現場人員傳來的手寫單照片。", "在 AI Agent 平台（opencode）中使用 <font name='Courier'>warehouse-entry</font> 技能。", "把照片交給 Agent。", "確認 Agent 列出的異動類型、品名、數量與編號。", "確認無誤後，Agent 自動呼叫 API 寫入中台。", "Agent 回報單號、每項設備／耗材的變化，以及新開的編號。"], 1): story.append(P(f"{i}. {text}", step))
story += [P("Agent 會自動辨識日期、案號、品名、數量與編號，推斷異動類型，並匹配品名和別名（例如「洗網機」→「洗車機」）。", base), P("⚠ <b>確認步驟很重要：</b>Agent 的異動類型推斷不一定完全準確；請逐一確認。無編號的設備，系統會自動開新編號。", quote), P("💡 同一張照片同時有「出」和「回」時，Agent 會自動拆成兩張單處理。", quote)]
story += [P("方式三：設備設置（初始建檔）", h3)]
for i, text in enumerate(["點左側「設備設置」。", "新增器材：選類型（設備＝個體管理有編號；耗材＝數量管理），填品名、規格、別名、代碼、單位、價格；耗材可設定初始庫存與安全庫存。", "點「建立器材」。", "調整庫存：耗材列表中點數字，可增減（+ 增加／- 減少）。", "編輯器材：點「編輯」可修改任何欄位。", "新增設備個體：編輯設備類器材時，可新增編號（如 #21、#22）。"], 1): story.append(P(f"{i}. {text}", step))
story += [P("編輯與刪除", h3), table([
    ["頁面", "操作"], ["進出單列表", "每列有 ✎ 編輯 和 ✕ 刪除"], ["設備列表", "每列有 ✎ 編輯 和 ✕ 刪除"], ["耗材庫存", "每列有 ± 調整、✎ 編輯、✕ 刪除"], ["異動紀錄", "每列有 ✎ 編輯 和 ✕ 刪除"], ["設備設置", "每列有 編輯 和 ✕ 刪除"],
], [4.2*cm, 11.5*cm]), P("⚠ 所有修改和刪除都會記錄在 audit_log 中（舊值→新值），可事後追溯。", quote)]

story += [P("2.3 自然語言查詢", h2), P("適用於：想查資料但不想在介面上逐一篩選。"), P("如何使用", h3), P("在 AI Agent 平台（opencode）中使用 <font name='Courier'>warehouse-query</font> 技能，直接用口語問問題。"), P("可以問什麼？", h3)]
examples = [
    ("查設備去向", "鑽機#21 上個月去哪了？", "Agent 會找到鑽機#21，列出它最近的異動紀錄。"),
    ("查案場設備", "26-023 這個案場還有哪些設備沒回？", "Agent 列出在 26-023 案場且狀態為「在外」的設備。"),
    ("查耗材庫存", "二重管目前庫存多少？哪些規格低於 5 支？", "Agent 列出所有二重管規格的庫存，標出低於 5 支的。"),
    ("查進出單", "這個月有哪些進出單？", "Agent 列出本月所有進出單。"),
    ("查報表", "今年哪些案場用最多設備？", "Agent 產生按案號分組的統計。"),
    ("查故障設備", "現在有什麼設備在送修？", "Agent 列出所有狀態為「待修」的設備。"),
]
for heading, question, answer in examples:
    story += [P(heading, h3), P(question, code), P("→ " + answer)]
story += [P("查詢特點", h3)]
for x in ["<b>可多輪追問：</b>先問「26-023 有哪些設備」，再問「那其中待修的呢」，Agent 會記住前次條件。", "<b>可用民國年：</b>「113 年 8 月的進出單」會自動轉換。", "<b>回答附行動建議：</b>例如「有 4 台在外超過 30 天，建議追回」。", "<b>查詢不會修改資料：</b>查詢 Agent 只讀不寫，安全無虞。"]: story.append(P("• " + x, bullet))
story += [P("查詢 vs 進出單 vs 異動紀錄的差別", h3), table([
    ["名稱", "是什麼", "用途"], ["進出單", "一張操作憑證（如一張手寫單）", "查某次操作、追溯原始照片"], ["異動紀錄", "每台設備的履歷", "查某設備去過哪些案場"], ["查詢", "用自然語言問問題", "快速得到答案，不用手動篩選"],
], [3.4*cm, 6.0*cm, 6.3*cm]), P("簡單說：進出單是「收據」，異動紀錄是「流水帳」，查詢是「問問題」。", quote)]

doc = SimpleDocTemplate(OUT, pagesize=A4, rightMargin=1.7*cm, leftMargin=1.7*cm, topMargin=1.7*cm, bottomMargin=1.8*cm, title="設備管理系統 使用手冊")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
