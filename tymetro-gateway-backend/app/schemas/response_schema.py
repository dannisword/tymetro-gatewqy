from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, computed_field
import math

DataT = TypeVar("DataT")

class PageData(BaseModel, Generic[DataT]):
    source: List[DataT]
    pageIndex: int
    pageSize: int
    total: int
    pageSizes: List[int] = [10, 20, 50, 100, 200, 500]
    
    @computed_field
    @property
    def page(self) -> int:
        return self.pageIndex
        
    @computed_field
    @property
    def totalRows(self) -> int:
        return self.total
        
    @computed_field
    @property
    def totalPages(self) -> int:
        if self.pageSize <= 0:
            return 0
        return math.ceil(self.total / self.pageSize)

    @computed_field
    @property
    def number(self) -> int:
        return self.pageIndex
        
    @computed_field
    @property
    def size(self) -> int:
        return self.pageSize
        
    @computed_field
    @property
    def totalElements(self) -> int:
        return self.total

class ResponseBase(BaseModel, Generic[DataT]):
    success: bool = True
    message: str = "Success"
    data: Optional[DataT] = None

class ResponseList(ResponseBase[PageData[DataT]]):
    pass
