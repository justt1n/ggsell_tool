from datetime import datetime
from typing import List, Optional, Literal, Dict, Any

from pydantic import BaseModel, Field


class AuthToken(BaseModel):
    token: str
    valid_thru: datetime


class Product(BaseModel):
    id: int = Field(..., alias='id_goods')
    name: str = Field(..., alias='name_goods')
    price: float


class GoodsListResponse(BaseModel):
    return_value: int = Field(..., alias='retval')
    return_description: str = Field(..., alias='retval_desc')
    products: List[Product] = Field(default_factory=list, alias='rows')


class Category(BaseModel):
    id: str
    name: str
    count: str = Field(..., alias='cnt')

    subcategories: Optional[List['Category']] = Field(None, alias='sub')


class CategoryListResponse(BaseModel):
    return_value: int = Field(..., alias='retval')
    return_description: str = Field(..., alias='retdesc')
    categories: List[Category] = Field(default_factory=list, alias='category')


class SaleInfo(BaseModel):
    common_base_price: Optional[float] = None
    common_price_usd: Optional[str] = None
    common_price_rur: Optional[str] = None
    common_price_eur: Optional[str] = None
    common_price_uah: Optional[str] = None
    sale_end: Optional[datetime] = None
    sale_percent: Optional[float] = None


class SellerItem(BaseModel):
    id: int = Field(..., alias='id_goods')
    name: str = Field(..., alias='name_goods')
    info: Optional[str] = Field(None, alias='info_goods')
    additional_info: Optional[str] = Field(None, alias='add_info')
    price: float
    currency: str
    sales_count: int = Field(..., alias='cnt_sell')
    returns_count: int = Field(..., alias='cnt_return')
    good_responses_count: int = Field(..., alias='cnt_goodresponses')
    bad_responses_count: int = Field(..., alias='cnt_badresponses')
    price_usd: float
    price_rur: float
    price_eur: float
    price_uah: float
    in_stock: int
    agent_commission: float = Field(..., alias='commiss_agent')
    visible: int
    has_discount: int
    num_options: int
    sale_info: SaleInfo
    owner_id: int

    num_in_stock: Optional[int] = None

    sales_count_hidden: int = Field(..., alias='cnt_sell_hidden')
    returns_count_hidden: int = Field(..., alias='cnt_return_hidden')
    good_responses_hidden: int = Field(..., alias='cnt_goodresponses_hidden')
    bad_responses_hidden: int = Field(..., alias='cnt_badresponses_hidden')
    release_date: Optional[str] = None


class SellerItemsResponse(BaseModel):
    return_value: int = Field(..., alias='retval')
    return_description: Optional[str] = Field(None, alias='retdesc')
    seller_id: int = Field(..., alias='id_seller')
    seller_name: str = Field(..., alias='name_seller')
    total_goods: int = Field(..., alias='cnt_goods')
    total_pages: int = Field(..., alias='pages')
    current_page: int = Field(..., alias='page')
    order_column: str = Field(..., alias='order_col')
    order_direction: str = Field(..., alias='order_dir')
    items: List[SellerItem] = Field(..., alias='rows')

    seller_rating: float = Field(..., alias='rating_seller')
    show_hidden_mode: int = Field(..., alias='show_hidden')


class ProductPriceVariantUpdate(BaseModel):
    variant_id: int
    rate: float
    type: Optional[Literal['percentplus', 'percentminus', 'priceplus', 'priceminus']] = None
    target_price: float
    price_rounding: int


class ProductPriceUpdate(BaseModel):
    product_id: int
    price: Optional[float] = None
    variants: Optional[List[ProductPriceVariantUpdate]] = None


class BulkPriceUpdateResponse(BaseModel):
    taskId: str = Field(..., alias='taskId')


class BsProduct(BaseModel):
    seller_name: Optional[str] = None
    name: str
    price: Optional[float] = None
    outside_price: str
    sold_count: Optional[str] = None
    link: str
    image_link: str

    def get_price(self) -> Optional[float]:
        if self.price != -1:
            return self.price
        if self.outside_price:
            try:
                price_value = float(self.outside_price.replace(',', '').replace(' ', ''))
                return price_value
            except ValueError:
                return None
        return None


class InsideInfo(BaseModel):
    seller_name: str
    price: float
    order_sold_count: int


class InsideProduct(BaseModel):
    price_text: str
    request_url: str


class LocaleValue(BaseModel):
    locale: Literal["ru-RU", "en-US"]
    value: str


class ApiError(BaseModel):
    code: str
    message: str


class ProductParamsDetail(BaseModel):
    id: int
    type: Literal['textarea', 'checkbox', 'text', 'radio', 'select']
    comment: Optional[List[LocaleValue]] = None
    order: int
    separate_content: int
    modifier_visible: int
    name: List[LocaleValue]


class ProductParamsResponse(BaseModel):
    return_value: int = Field(..., alias='retval')
    return_description: Optional[str] = Field(None, alias='retdesc')
    errors: Optional[List[ApiError]] = None
    content: Optional[List[ProductParamsDetail]] = None


class ParamVariant(BaseModel):
    variant_id: int
    name: List[LocaleValue]
    type: Literal['percentplus', 'percentminus', 'priceplus', 'priceminus']
    rate: float
    is_default: bool
    visible: bool
    order: int


class ParamInformation(BaseModel):
    id: int
    type: Literal['textarea', 'checkbox', 'text', 'radio', 'select']
    name: List[LocaleValue]
    order: int
    comment: Optional[List[LocaleValue]] = None
    no_default: bool
    separate_content: bool
    required: bool
    modifier_visible: bool
    variants: List[ParamVariant]


class ParamInformationResponse(BaseModel):
    return_value: int = Field(..., alias='retval')
    return_description: Optional[str] = Field(None, alias='retdesc')
    errors: Optional[List[ApiError]] = None
    content: Optional[ParamInformation] = None


class SimpleVariant(BaseModel):
    value: int
    text: str
    modify_value: float


class SimpleOption(BaseModel):
    id: int
    label: str
    type: str  # 'radio', 'text', etc.
    variants: Optional[List[SimpleVariant]] = None


class PriceUnit(BaseModel):
    unit_name: Optional[str] = None
    unit_amount: Optional[float] = None
    unit_amount_desc: Optional[str] = None
    unit_currency: Optional[str] = None
    unit_cnt: Optional[int] = None
    unit_cnt_min: Optional[int] = None
    unit_cnt_max: Optional[int] = None
    unit_cnt_desc: Optional[str] = None


class PriceItem(BaseModel):
    usd: float = Field(..., alias='USD')
    rub: float = Field(..., alias='RUB')


class Prices(BaseModel):
    initial: Optional[PriceItem] = None
    default: Optional[PriceItem] = None


class SimpleProductDescription(BaseModel):
    id: int
    name: str
    price: float
    currency: str
    prices_unit: Optional[PriceUnit] = None
    options: List[SimpleOption] = Field(default_factory=list)
    units: Optional[Dict[str, Any]] = None
    prices: Optional[Prices] = None


class ProductDescriptionResponse(BaseModel):
    return_value: int = Field(..., alias='retval')
    product: SimpleProductDescription
