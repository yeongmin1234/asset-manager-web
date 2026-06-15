from pydantic import BaseModel


class AssetStatsSummary(BaseModel):
    total_assets: int = 0
    in_use_assets: int = 0
    unused_assets: int = 0
    disposed_assets: int = 0
    total_purchase_amount: int = 0


class CategoryAssetStats(BaseModel):
    category_name: str
    asset_count: int = 0


class DepartmentAssetStats(BaseModel):
    department_name: str
    asset_count: int = 0


class MonthlyAssetStats(BaseModel):
    month: str
    registered_count: int = 0
    disposed_count: int = 0
