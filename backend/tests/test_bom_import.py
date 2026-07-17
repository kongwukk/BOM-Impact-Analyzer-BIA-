from io import BytesIO

import pandas as pd

from app.services.bom_import import _match_column, _read_bom_sheets


def _workbook_bytes() -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                ["智能安桌整灯BOM", None, None, None, None],
                ["序号", "编号", "名称", "物料描述", "数量"],
                [1, "X015010026", "WF模块", "IXC32-18-XHHIX-313-E08", 1],
            ]
        ).to_excel(writer, sheet_name="智能安桌整灯BOM", header=False, index=False)
        pd.DataFrame(
            [
                ["序号", "物料编码", "物料名称", "物料描叙（规格）", "默认数量", "位号", "厂家"],
                [1, "X005030099", None, "电源板 AC 220V", 2, "PS1", "示例厂商"],
            ]
        ).to_excel(writer, sheet_name="电源BOM", header=False, index=False)
        pd.DataFrame([["说明"], ["此页没有BOM数据"]]).to_excel(
            writer, sheet_name="说明", header=False, index=False
        )
    return output.getvalue()


def test_reads_all_bom_sheets_and_finds_non_first_header_row() -> None:
    frame, skipped = _read_bom_sheets(_workbook_bytes())

    assert frame["part_number"].tolist() == [
        "IXC32-18-XHHIX-313-E08",
        "电源板 AC 220V",
    ]
    assert frame["material_code"].tolist() == ["X015010026", "X005030099"]
    assert frame["quantity"].tolist() == [1, 2]
    assert frame["description"].iloc[0] == "WF模块"
    assert frame["_sheet_name"].tolist() == ["智能安桌整灯BOM", "电源BOM"]
    assert skipped == ["说明"]


def test_material_code_and_model_description_are_separate_fields() -> None:
    assert _match_column("编号") == "material_code"
    assert _match_column("物料描叙（规格）") == "part_number"
    assert _match_column("序号") is None
