# models/sheet_models.py
import logging
from typing import Annotated, List, Optional, ClassVar, Type, Dict, Any

from pydantic import BaseModel, ValidationError, computed_field


def _col_to_index(col_name: str) -> int:
    """Convert a column letter (e.g., 'A', 'B', ..., 'Z', 'AA', 'AB', ...) to a zero-based index."""
    index = 0
    for char in col_name.upper():
        index = index * 26 + (ord(char) - ord('A') + 1)
    return index - 1


class BaseGSheetModel(BaseModel):
    row_index: int

    _index_map: ClassVar[Optional[Dict[str, int]]] = None
    _col_map: ClassVar[Optional[Dict[str, str]]] = None

    @classmethod
    def _build_maps_if_needed(cls):
        if cls._index_map is not None and cls._col_map is not None:
            return

        # logging.info("Building column index map for model: " + cls.__name__)
        index_map = {}
        col_map = {}
        for field_name, field_info in cls.model_fields.items():
            if not field_info.metadata:
                continue

            column_letter = field_info.metadata[0]
            if isinstance(column_letter, str):
                index_map[field_name] = _col_to_index(column_letter)
                col_map[field_name] = column_letter

        cls._index_map = index_map
        cls._col_map = col_map
        # logging.info(f"Built index map: {cls._index_map}")

    @classmethod
    def from_row(cls, row_data: List[str], row_index: int) -> Optional['BaseGSheetModel']:
        cls._build_maps_if_needed()

        data_dict = {}
        for field_name, col_index in cls._index_map.items():
            if col_index < len(row_data):
                value = row_data[col_index]
                data_dict[field_name] = value if value != '' else None

        if not any(data_dict.values()):
            return None

        data_dict['row_index'] = row_index

        try:
            return cls.model_validate(data_dict)
        except ValidationError as e:
            product_name_index = cls._index_map.get("product_name")
            name_for_log = ""
            if product_name_index is not None and product_name_index < len(row_data):
                name_for_log = row_data[product_name_index] or f"Hàng {row_index}"
            else:
                name_for_log = f"Hàng {row_index}"

            # logging.warning(f"Ignoring row {row_index} ({name_for_log}) due to validation error: {e}")
            return None


class SheetLocation(BaseModel):
    sheet_id: Optional[str] = None
    sheet_name: Optional[str] = None
    cell: Optional[str] = None


class Payload(BaseGSheetModel):
    is_2lai_enabled_str: Annotated[Optional[str], "A"] = None
    is_check_enabled_str: Annotated[Optional[str], "B"] = None
    product_name: Annotated[str, "C"]
    parameters: Annotated[Optional[str], "D"] = None
    note: Annotated[Optional[str], "E"] = None
    last_update: Annotated[Optional[str], "F"] = None
    product_id: Annotated[Optional[int], "G"] = None
    product_variant_id: Annotated[Optional[int], "H"] = None
    is_compare_enabled_str: Annotated[Optional[str], "I"] = None
    product_compare: Annotated[Optional[str], "J"] = None
    include_keyword: Annotated[Optional[str], "K"] = None
    exclude_keyword: Annotated[Optional[str], "L"] = None
    product_compare2: Annotated[Optional[str], "M"] = None
    min_price_adjustment: Annotated[Optional[float], "N"] = None
    max_price_adjustment: Annotated[Optional[float], "O"] = None
    price_rounding: Annotated[Optional[int], "P"] = None
    order_sold: Annotated[Optional[int], "Q"] = 0
    currency: Annotated[Optional[str], "R"] = None
    idsheet_min: Annotated[Optional[str], "S"] = None
    sheet_min: Annotated[Optional[str], "T"] = None
    cell_min: Annotated[Optional[str], "U"] = None
    idsheet_max: Annotated[Optional[str], "V"] = None
    sheet_max: Annotated[Optional[str], "W"] = None
    cell_max: Annotated[Optional[str], "X"] = None
    idsheet_stock: Annotated[Optional[str], "Y"] = None
    sheet_stock: Annotated[Optional[str], "Z"] = None
    cell_stock: Annotated[Optional[str], "AA"] = None
    idsheet_blacklist: Annotated[Optional[str], "AB"] = None
    sheet_blacklist: Annotated[Optional[str], "AC"] = None
    cell_blacklist: Annotated[Optional[str], "AD"] = None
    relax: Annotated[Optional[str], "AE"] = None
    min_price: Annotated[Optional[str], "AF"] = None

    fetched_min_price: Optional[float] = None
    fetched_max_price: Optional[float] = None
    fetched_stock: Optional[int] = None
    fetched_black_list: Optional[List[str]] = None

    def get_min_price(self) -> float:
        min_price = float(self.min_price.replace(",", ""))
        return min_price

    @computed_field
    @property
    def min_price_location(self) -> SheetLocation:
        return SheetLocation(sheet_id=self.idsheet_min, sheet_name=self.sheet_min, cell=self.cell_min)

    @computed_field
    @property
    def max_price_location(self) -> SheetLocation:
        return SheetLocation(sheet_id=self.idsheet_max, sheet_name=self.sheet_max, cell=self.cell_max)

    @computed_field
    @property
    def stock_location(self) -> SheetLocation:
        return SheetLocation(sheet_id=self.idsheet_stock, sheet_name=self.sheet_stock, cell=self.cell_stock)

    @computed_field
    @property
    def blacklist_location(self) -> SheetLocation:
        return SheetLocation(sheet_id=self.idsheet_blacklist, sheet_name=self.sheet_blacklist, cell=self.cell_blacklist)

    @property
    def is_check_enabled(self) -> bool:
        return self.is_check_enabled_str == '1'

    @property
    def is_2lai_enabled(self) -> bool:
        return self.is_2lai_enabled_str == '1'

    @property
    def is_compare_enabled(self) -> bool:
        return self.is_compare_enabled_str == '1'

    @property
    def is_have_min_price(self) -> bool:
        return self.min_price is not None and self.get_min_price() > 0

    def prepare_update(self, sheet_name: str, updates: Dict[str, Any]) -> List[Dict]:
        """
        Tạo danh sách các yêu cầu cập nhật cho API batchUpdate.

        Args:
            sheet_name (str): Tên của sheet để xây dựng dải ô (ví dụ: 'Gamivo').
            updates (Dict[str, Any]): Một dictionary với key là tên trường model
                                     (ví dụ: 'note') và value là giá trị mới.

        Returns:
            List[Dict]: Một danh sách các dictionary, sẵn sàng để gửi đi.
                        Ví dụ: [{'range': 'Gamivo!D50', 'values': [['Giá trị mới']]}]
        """
        update_requests = []
        for field_name, new_value in updates.items():
            column_letter = self._col_map.get(field_name)

            if not column_letter:
                logging.warning(f"Field '{field_name}' does not have a valid column mapping.")
                continue

            # Build A1, ex: 'Gamivo!D50'
            cell_range = f"{sheet_name}!{column_letter}{self.row_index}"

            update_requests.append({
                'range': cell_range,
                'values': [[str(new_value)]]
            })

        return update_requests
