from typing import Optional

from pydantic import BaseModel


class Button(BaseModel):
    id: str
    name: str
    price: Optional[float] = None