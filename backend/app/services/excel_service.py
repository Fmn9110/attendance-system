import io
from typing import List, Tuple
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

from ..schemas.student_schema import PreviewRow, PreviewResult

REQUIRED_HEADERS = {"学号", "姓名"}
OPTIONAL_HEADERS = {"电话"}


def _norm(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def parse_roster(file_bytes: bytes, filename: str) -> PreviewResult:
    """解析花名册 Excel，返回预览结果。"""
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ("xlsx", "xlsm", "xls"):
        return PreviewResult(total_rows=0, valid_count=0, error_count=0, rows=[], missing_columns=[])

    if ext == "xls":
        try:
            import xlrd  # type: ignore
        except ImportError:
            raise ValueError("当前服务器未安装 .xls 支持，请使用 .xlsx")
        book = xlrd.open_workbook(file_contents=file_bytes)
        sh = book.sheet_by_index(0)
        if sh.nrows == 0:
            return PreviewResult(total_rows=0, valid_count=0, error_count=0, rows=[])
        header = [_norm(sh.cell_value(0, c)) for c in range(sh.ncols)]
        data_iter = ([_norm(sh.cell_value(r, c)) for c in range(sh.ncols)] for r in range(1, sh.nrows))
        total_rows = sh.nrows - 1
    else:
        book = load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
        sh = book.active
        rows = sh.iter_rows(values_only=True)
        try:
            header_row = next(rows)
        except StopIteration:
            return PreviewResult(total_rows=0, valid_count=0, error_count=0, rows=[])
        header = [_norm(v) for v in header_row]
        data_iter = ([_norm(v) for v in row] for row in rows)
        total_rows = sh.max_row - 1

    lower_header = {h: i for i, h in enumerate(header)}
    missing = [h for h in REQUIRED_HEADERS if h not in lower_header]
    if missing:
        return PreviewResult(total_rows=0, valid_count=0, error_count=0, rows=[], missing_columns=missing)

    num_idx = lower_header["学号"]
    name_idx = lower_header["姓名"]
    phone_idx = lower_header.get("电话")

    rows_out: List[PreviewRow] = []
    seen_numbers: set[str] = set()
    valid = 0
    errors = 0

    for i, row in enumerate(data_iter, start=2):  # Excel 行号从 2 开始
        number = _norm(row[num_idx]) if num_idx < len(row) else ""
        name = _norm(row[name_idx]) if name_idx < len(row) else ""
        phone = _norm(row[phone_idx]) if phone_idx is not None and phone_idx < len(row) else ""

        # 全空行忽略
        if not number and not name and not phone:
            continue

        errs: List[str] = []
        if not number:
            errs.append("学号为空")
        if not name:
            errs.append("姓名为空")
        if number and number in seen_numbers:
            errs.append("学号重复")
        if number:
            seen_numbers.add(number)

        if errs:
            errors += 1
        else:
            valid += 1
        rows_out.append(PreviewRow(
            row_index=i,
            student_number=number,
            name=name,
            phone=phone or None,
            errors=errs,
        ))

    return PreviewResult(
        total_rows=total_rows,
        valid_count=valid,
        error_count=errors,
        rows=rows_out,
    )


def _style_sheet(ws, ncols: int, nrows: int) -> None:
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF")
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"
    # 自动列宽
    for c in range(1, ncols + 1):
        max_len = 0
        col_letter = get_column_letter(c)
        for r in range(1, min(nrows + 1, 500)):
            v = ws.cell(row=r, column=c).value
            if v is None:
                continue
            ln = sum(2 if ord(ch) > 127 else 1 for ch in str(v))
            if ln > max_len:
                max_len = ln
        ws.column_dimensions[col_letter].width = min(max(max_len + 2, 10), 40)


STATUS_FILL = {
    "已到": "C6EFCE",
    "迟到": "FFEB9C",
    "已请假": "BDD7EE",
    "其他": "E4DFEC",
    "未点名": "D9D9D9",
}


def export_single_session(
    filename: str,
    class_name: str,
    started_at,
    finished_at,
    rows: List[dict],
) -> None:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "点名明细"
    headers = ["序号", "学号", "姓名", "电话", "到课状态", "备注", "点名开始时间", "点名结束时间", "点名日期"]
    ws.append(headers)
    for idx, r in enumerate(rows, start=1):
        ws.append([
            idx,
            str(r["student_number"]),
            r["name"],
            str(r["phone"] or ""),
            r["status_text"],
            r.get("remark") or "",
            started_at.strftime("%Y-%m-%d %H:%M:%S") if started_at else "",
            finished_at.strftime("%Y-%m-%d %H:%M:%S") if finished_at else "",
            started_at.strftime("%Y-%m-%d") if started_at else "",
        ])
        # 状态着色
        fill = STATUS_FILL.get(r["status_text"])
        if fill:
            ws.cell(row=idx + 1, column=5).fill = PatternFill("solid", fgColor=fill)
        # 学号/电话设为文本
        ws.cell(row=idx + 1, column=2).number_format = "@"
        ws.cell(row=idx + 1, column=4).number_format = "@"
    _style_sheet(ws, len(headers), len(rows) + 1)
    wb.save(filename)


def export_batch(
    filename: str,
    detail_rows: List[dict],
    summary_rows: List[dict],
    student_stat_rows: List[dict],
) -> None:
    from openpyxl import Workbook
    wb = Workbook()

    ws1 = wb.active
    ws1.title = "点名明细"
    h1 = ["序号", "第几次", "点名日期", "开始时间", "结束时间", "班级", "学号", "姓名", "电话", "到课状态", "备注"]
    ws1.append(h1)
    for idx, r in enumerate(detail_rows, start=1):
        ws1.append([
            idx,
            r.get("seq", ""),
            r["date"],
            r["started_at"],
            r["finished_at"],
            r["class_name"],
            str(r["student_number"]),
            r["name"],
            str(r["phone"] or ""),
            r["status_text"],
            r.get("remark") or "",
        ])
        fill = STATUS_FILL.get(r["status_text"])
        if fill:
            ws1.cell(row=idx + 1, column=10).fill = PatternFill("solid", fgColor=fill)
        ws1.cell(row=idx + 1, column=7).number_format = "@"
        ws1.cell(row=idx + 1, column=9).number_format = "@"
    _style_sheet(ws1, len(h1), len(detail_rows) + 1)

    ws2 = wb.create_sheet("点名汇总")
    h2 = ["第几次", "点名日期", "开始时间", "结束时间", "耗时", "总人数", "已到", "迟到", "已请假", "其他", "未点名"]
    ws2.append(h2)
    for r in summary_rows:
        ws2.append([
            r.get("seq", ""), r["date"], r["started_at"], r["finished_at"], r["duration"],
            r["total"], r["present"], r["late"], r["sick_leave"], r["other"], r["pending"],
        ])
    _style_sheet(ws2, len(h2), len(summary_rows) + 1)

    ws3 = wb.create_sheet("学生统计")
    h3 = ["学号", "姓名", "总点名次数", "已到次数", "迟到次数", "已请假次数", "其他次数"]
    ws3.append(h3)
    for r in student_stat_rows:
        ws3.append([
            str(r["student_number"]), r["name"], r["total"],
            r["present"], r["late"], r["sick_leave"], r["other"],
        ])
        ws3.cell(row=ws3.max_row, column=1).number_format = "@"
    _style_sheet(ws3, len(h3), len(student_stat_rows) + 1)

    wb.save(filename)
