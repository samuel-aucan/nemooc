"""Proxy de filtros para la tabla principal de OCs."""

from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt

from app_qt.models.oc_table_model import OcTableModel, OcTableRow


class OcTableProxyModel(QSortFilterProxyModel):
    """Filtro por texto y por estados/tipo/cartera para la bandeja principal."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._search_text = ""
        self._estado = "Todos"
        self._estado_mp = "Todos"
        self._tipo = "Todos"
        self._cartera = "Todas"
        self.setSortRole(Qt.ItemDataRole.UserRole + 1)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_search_text(self, text: str) -> None:
        self._search_text = (text or "").strip().casefold()
        self.invalidateFilter()

    def set_estado(self, value: str) -> None:
        self._estado = value or "Todos"
        self.invalidateFilter()

    def set_estado_mp(self, value: str) -> None:
        self._estado_mp = value or "Todos"
        self.invalidateFilter()

    def set_tipo(self, value: str) -> None:
        self._tipo = value or "Todos"
        self.invalidateFilter()

    def set_cartera(self, value: str) -> None:
        self._cartera = value or "Todas"
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        model = self.sourceModel()
        if not isinstance(model, OcTableModel):
            return True

        row: OcTableRow | None = model.row_at(source_row)
        if row is None:
            return False

        oc = row.oc

        if self._estado != "Todos" and oc.estado_interno != self._estado:
            return False
        if self._estado_mp != "Todos" and oc.estado_mp != self._estado_mp:
            return False
        if self._tipo != "Todos" and oc.tipo_oc != self._tipo:
            return False
        if self._cartera != "Todas" and row.cartera != self._cartera:
            return False

        if self._search_text:
            blob = " ".join(
                [
                    oc.codigo_oc or "",
                    oc.nombre_organismo or "",
                    oc.cliente_sap_sugerido or "",
                    oc.estado_mp or "",
                    oc.tipo_oc or "",
                    str(oc.cantidad_lineas or ""),
                    row.cartera or "",
                    row.region or "",
                ]
            ).casefold()
            if self._search_text not in blob:
                return False

        return True
