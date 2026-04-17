"""Modelo de tabla para cabeceras de OCs en la bandeja principal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from app.models.orden_compra import OrdenCompra


@dataclass
class OcTableRow:
    oc: OrdenCompra
    cartera: str = ""
    region: str = ""


class OcTableModel(QAbstractTableModel):
    """Modelo base para la tabla principal de OCs."""

    columns = [
        ("estado_interno", "Estado"),
        ("codigo_oc", "Codigo OC"),
        ("fecha_envio", "Fecha"),
        ("nombre_organismo", "Cliente"),
        ("cliente_sap_sugerido", "Cliente SAP"),
        ("cartera", "Cartera"),
        ("tipo_oc", "Tipo"),
        ("estado_mp", "Estado MP"),
        ("cantidad_lineas", "Lineas"),
        ("total", "Total"),
    ]

    def __init__(self, rows: list[OcTableRow] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[OcTableRow] = rows or []

    def set_rows(self, rows: list[OcTableRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

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
        column_key = self.columns[index.column()][0]
        value = self._get_value(row, column_key)

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_value(column_key, value)

        if role == Qt.ItemDataRole.UserRole:
            return row

        if role == Qt.ItemDataRole.UserRole + 1:
            return self._sort_value(column_key, value)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if column_key in {"total"}:
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if column_key in {"fecha_envio", "tipo_oc", "cartera", "cantidad_lineas"}:
                return int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        if role == Qt.ItemDataRole.ToolTipRole:
            return self._tooltip(row, column_key)

        if role == Qt.ItemDataRole.ForegroundRole and column_key == "estado_interno":
            return self._status_color(row.oc.estado_interno)

        return None

    def row_at(self, row: int) -> OcTableRow | None:
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def _get_value(self, row: OcTableRow, key: str) -> Any:
        if key == "cartera":
            return row.cartera
        if key == "region":
            return row.region
        return getattr(row.oc, key)

    @staticmethod
    def _display_value(key: str, value: Any) -> str:
        if key == "total":
            try:
                return f"${float(value):,.0f}".replace(",", ".")
            except Exception:
                return "$0"
        if key == "cantidad_lineas":
            try:
                return str(int(value or 0))
            except Exception:
                return "0"
        if key == "fecha_envio":
            if not value:
                return ""
            text = str(value)
            try:
                dt = datetime.fromisoformat(text)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                return text[:10]
        return str(value or "")

    @staticmethod
    def _sort_value(key: str, value: Any) -> Any:
        if key in {"total", "cantidad_lineas"}:
            try:
                return float(value or 0)
            except Exception:
                return 0.0
        if key == "fecha_envio":
            return str(value or "")
        return str(value or "").casefold()

    @staticmethod
    def _tooltip(row: OcTableRow, key: str) -> str:
        if key == "nombre_organismo":
            return row.oc.nombre_organismo or ""
        if key == "estado_mp":
            return row.oc.estado_mp or ""
        if key == "cantidad_lineas":
            return f"{int(row.oc.cantidad_lineas or 0)} linea(s) registradas en la OC"
        if key == "total":
            return f"Moneda: {row.oc.moneda or 'CLP'}"
        return ""

    @staticmethod
    def _status_color(status: str):
        from PySide6.QtGui import QColor

        colors = {
            "Pendiente": QColor("#F59E0B"),
            "Nueva": QColor("#38BDF8"),
            "Revisada": QColor("#A78BFA"),
            "Lista para SAP": QColor("#F97316"),
            "Ingresada": QColor("#10B981"),
            "Con error": QColor("#EF4444"),
        }
        return colors.get(status or "", QColor("#E5EEF9"))
