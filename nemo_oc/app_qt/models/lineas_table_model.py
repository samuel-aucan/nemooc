"""Modelo de tabla para lineas del detalle de una OC."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from app.models.linea_oc import LineaOC


class LineasTableModel(QAbstractTableModel):
    columns = [
        ("correlativo", "#"),
        ("codigo_mp", "Cod. MP"),
        ("descripcion", "Descripcion"),
        ("itemcode_sap", "ItemCode"),
        ("descripcion_sap", "Descripcion SAP"),
        ("cantidad", "Cant."),
        ("cantidad_sap", "Cant. SAP"),
        ("factor_empaque", "F.Emp"),
        ("precio_neto", "Precio Neto"),
        ("precio_sap", "Precio SAP"),
        ("unidad", "Unidad"),
        ("total", "Total"),
        ("estado_homologacion", "Estado"),
    ]

    def __init__(self, rows: list[LineaOC] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[LineaOC] = rows or []

    def set_rows(self, rows: list[LineaOC]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def row_at(self, row: int) -> LineaOC | None:
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.columns)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.columns[section][1]
        return str(section + 1)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        row = self._rows[index.row()]
        key = self.columns[index.column()][0]

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display(row, key)

        if role == Qt.ItemDataRole.UserRole + 1:
            return self._sort_value(row, key)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if key in {"correlativo", "cantidad", "cantidad_sap", "factor_empaque"}:
                return int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            if key in {"precio_neto", "precio_sap", "total"}:
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        if role == Qt.ItemDataRole.ToolTipRole:
            if key == "descripcion":
                return (row.especificacion_comprador or row.producto or "").strip()
            if key == "descripcion_sap":
                return (row.descripcion_sap or "").strip()

        if role == Qt.ItemDataRole.ForegroundRole and key == "estado_homologacion":
            return self._status_color(row.estado_homologacion)

        return None

    @staticmethod
    def _display(row: LineaOC, key: str) -> str:
        if key == "descripcion":
            return (row.especificacion_comprador or row.producto or "").strip()
        if key == "total":
            return f"${float(row.total or 0):,.0f}".replace(",", ".")
        if key in {"precio_neto", "precio_sap"}:
            value = getattr(row, key) or 0
            return f"${float(value):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        if key == "cantidad":
            value = float(row.cantidad or 0)
            if value.is_integer():
                return str(int(value))
            return f"{value:.2f}"
        if key == "cantidad_sap":
            value = row.cantidad_sap if row.cantidad_sap is not None else row.cantidad
            value = float(value or 0)
            if value.is_integer():
                return str(int(value))
            return f"{value:.2f}"
        if key == "factor_empaque":
            value = float(row.factor_empaque or 0)
            if value.is_integer():
                return str(int(value))
            return f"{value:.2f}"
        return str(getattr(row, key) or "")

    @staticmethod
    def _status_color(status: str) -> QColor:
        mapping = {
            "homologado": QColor("#10B981"),
            "sugerido": QColor("#38BDF8"),
            "manual": QColor("#A78BFA"),
            "pendiente": QColor("#F59E0B"),
            "sin_homologacion": QColor("#EF4444"),
        }
        return mapping.get(status or "", QColor("#E5EEF9"))

    @staticmethod
    def _sort_value(row: LineaOC, key: str):
        if key in {"correlativo", "cantidad", "total"}:
            return float(getattr(row, key) or 0)
        if key == "descripcion":
            return (row.especificacion_comprador or row.producto or "").casefold()
        return str(getattr(row, key) or "").casefold()
