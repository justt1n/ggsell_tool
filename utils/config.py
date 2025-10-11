# utils/config.py
import json
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='settings.env', env_file_encoding='utf-8', extra='ignore')

    # Google Sheets settings
    MAIN_SHEET_ID: str
    MAIN_SHEET_NAME: str
    GOOGLE_KEY_PATH: str
    DIGI_API_KEY: str
    SELLER_ID: int
    # Đọc chuỗi JSON từ .env và chuyển thành list
    HEADER_KEY_COLUMNS_JSON: str = '["CHECK", "Product_name", "product_variant_id"]'
    EXPORT_SHEET_ID: str
    EXPORT_SHEET_NAME: str
    SLEEP_TIME: int = 5
    CURRENCY: str = 'RUB'
    BATCH_SIZE: int = 20

    @property
    def HEADER_KEY_COLUMNS(self) -> List[str]:
        """Chuyển đổi chuỗi JSON của các cột key thành một danh sách Python."""
        return json.loads(self.HEADER_KEY_COLUMNS_JSON)


# Tạo một instance duy nhất để import và sử dụng trong toàn bộ dự án
settings = Settings()
