# clients/google_sheets_client.py
import logging
from typing import List, Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsClient:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    def __init__(self, key_path: str):
        try:
            creds = service_account.Credentials.from_service_account_file(key_path, scopes=self.SCOPES)
            self.service = build('sheets', 'v4', credentials=creds)
            # logging.info("Đã kết nối thành công tới Google Sheets API.")
        except FileNotFoundError:
            logging.error(
                f"Không tìm thấy file key tại: '{key_path}'. Vui lòng kiểm tra lại đường dẫn trong file settings.env.")
            raise
        except Exception as e:
            logging.error(f"Lỗi khi khởi tạo GoogleSheetsClient: {e}")
            raise

    def get_data(self, spreadsheet_id: str, range_name: str) -> List[List[str]]:
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name
            ).execute()
            values = result.get('values', [])
            # logging.info(f"Đã lấy thành công {len(values)} hàng từ dải ô '{range_name}'.")
            return values
        except HttpError as error:
            logging.error(f"Đã xảy ra lỗi API khi lấy dữ liệu: {error}")
            return []

    def batch_update(self, spreadsheet_id: str, data: List[dict]):
        try:
            body = {'data': data, 'valueInputOption': 'USER_ENTERED'}
            result = self.service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id, body=body
            ).execute()
            # logging.info(f"{result.get('totalUpdatedCells')} ô đã được cập nhật.")
        except HttpError as error:
            logging.error(f"Đã xảy ra lỗi API khi cập nhật dữ liệu: {error}")

    def batch_get_data(self, spreadsheet_id: str, ranges: List[str]) -> Dict[str, Any]:
        """
        Lấy dữ liệu từ nhiều dải ô trong cùng một spreadsheet.
        Trả về một dictionary map từ dải ô (range) tới giá trị (value).
        """
        if not spreadsheet_id or not ranges:
            return {}

        try:
            result = self.service.spreadsheets().values().batchGet(
                spreadsheetId=spreadsheet_id, ranges=ranges, valueRenderOption='UNFORMATTED_VALUE'
            ).execute()

            value_map = {}
            for value_range in result.get('valueRanges', []):
                response_range = value_range.get('range')
                if not response_range:
                    continue

                sheet_name, cell_range = response_range.split('!')
                normalized_sheet_name = sheet_name.strip("'")
                normalized_key = f"'{normalized_sheet_name}'!{cell_range}"

                values = value_range.get('values')

                value_map[normalized_key] = values

            return value_map

        except HttpError as error:
            logging.error(f"Lỗi API khi batchGet dữ liệu từ {spreadsheet_id}: {error}")
            return {}

    def clear_sheet(self, spreadsheet_id: str, range_name: str):
        """Xóa toàn bộ dữ liệu trong một dải ô hoặc toàn bộ sheet."""
        try:
            self.service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                body={}
            ).execute()
            logging.info(f"Đã xóa thành công dữ liệu trong dải ô '{range_name}'.")
        except HttpError as error:
            logging.error(f"Lỗi API khi xóa dữ liệu: {error}")
            raise

    def update_data(self, spreadsheet_id: str, range_name: str, values: List[List[Any]]):
        """Ghi đè dữ liệu vào một dải ô, bắt đầu từ ô đầu tiên của dải ô đó."""
        try:
            body = {'values': values}
            result = self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            logging.info(f"{result.get('updatedCells')} ô đã được ghi tại dải ô '{range_name}'.")
        except HttpError as error:
            logging.error(f"Lỗi API khi ghi dữ liệu: {error}")
            raise
