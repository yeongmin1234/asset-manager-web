from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.asset import Asset, AssetStatus
from app.models.category import Category
from app.models.department import Department
from app.models.history import AssetActionType, AssetHistory
from app.schemas.stats import (
    AssetStatsSummary,
    CategoryAssetStats,
    DepartmentAssetStats,
    MonthlyAssetStats,
)


def get_asset_stats_summary(db: Session) -> AssetStatsSummary:
    row = db.execute(
        select(
            func.count(Asset.id).label("total_assets"),
            func.coalesce(
                func.sum(case((Asset.status == AssetStatus.IN_USE, 1), else_=0)),
                0,
            ).label("in_use_assets"),
            func.coalesce(
                func.sum(case((Asset.status == AssetStatus.UNUSED, 1), else_=0)),
                0,
            ).label("unused_assets"),
            func.coalesce(
                func.sum(case((Asset.status == AssetStatus.DISPOSED, 1), else_=0)),
                0,
            ).label("disposed_assets"),
            func.coalesce(func.sum(Asset.purchase_price), 0).label(
                "total_purchase_amount"
            ),
        ).where(Asset.deleted_at.is_(None))
    ).one()

    return AssetStatsSummary(
        total_assets=int(row.total_assets or 0),
        in_use_assets=int(row.in_use_assets or 0),
        unused_assets=int(row.unused_assets or 0),
        disposed_assets=int(row.disposed_assets or 0),
        total_purchase_amount=int(row.total_purchase_amount or 0),
    )


def get_asset_stats_by_category(db: Session) -> list[CategoryAssetStats]:
    rows = db.execute(
        select(
            Category.name.label("category_name"),
            func.count(Asset.id).label("asset_count"),
        )
        .join(Category, Asset.category_id == Category.id)
        .where(Asset.deleted_at.is_(None))
        .group_by(Category.name)
        .order_by(func.count(Asset.id).desc(), Category.name.asc())
    ).all()

    return [
        CategoryAssetStats(
            category_name=row.category_name,
            asset_count=int(row.asset_count or 0),
        )
        for row in rows
    ]


def get_asset_stats_by_department(db: Session) -> list[DepartmentAssetStats]:
    department_label = func.coalesce(
        func.nullif(Asset.department_name, ""),
        Department.name,
        "부서 미지정",
    )
    rows = db.execute(
        select(
            department_label.label("department_name"),
            func.count(Asset.id).label("asset_count"),
        )
        .outerjoin(Department, Asset.department_id == Department.id)
        .where(Asset.deleted_at.is_(None))
        .group_by(department_label)
        .order_by(func.count(Asset.id).desc(), department_label.asc())
    ).all()

    return [
        DepartmentAssetStats(
            department_name=row.department_name,
            asset_count=int(row.asset_count or 0),
        )
        for row in rows
    ]


def get_asset_stats_monthly(db: Session) -> list[MonthlyAssetStats]:
    months = get_recent_month_labels()
    first_month = months[0]
    registered_month = func.to_char(
        func.date_trunc("month", Asset.created_at),
        "YYYY-MM",
    )

    registered_rows = db.execute(
        select(
            registered_month.label("month"),
            func.count(Asset.id).label("registered_count"),
        )
        .where(
            Asset.deleted_at.is_(None),
            registered_month >= first_month,
        )
        .group_by(registered_month)
    ).all()

    disposal_history_month = func.to_char(
        func.date_trunc("month", AssetHistory.changed_at),
        "YYYY-MM",
    )
    disposed_history_rows = db.execute(
        select(
            disposal_history_month.label("month"),
            func.count(func.distinct(AssetHistory.asset_id)).label("disposed_count"),
        )
        .where(
            disposal_history_month >= first_month,
            (
                (AssetHistory.action_type == AssetActionType.DISPOSED)
                | (
                    (AssetHistory.action_type == AssetActionType.STATUS_CHANGED)
                    & (AssetHistory.new_value == AssetStatus.DISPOSED.value)
                )
            ),
        )
        .group_by(disposal_history_month)
    ).all()

    assets_with_disposal_history = select(AssetHistory.asset_id).where(
        (AssetHistory.action_type == AssetActionType.DISPOSED)
        | (
            (AssetHistory.action_type == AssetActionType.STATUS_CHANGED)
            & (AssetHistory.new_value == AssetStatus.DISPOSED.value)
        )
    )
    fallback_disposed_month = func.to_char(
        func.date_trunc("month", Asset.updated_at),
        "YYYY-MM",
    )
    fallback_disposed_rows = db.execute(
        select(
            fallback_disposed_month.label("month"),
            func.count(Asset.id).label("disposed_count"),
        )
        .where(
            Asset.status == AssetStatus.DISPOSED,
            fallback_disposed_month >= first_month,
            Asset.id.notin_(assets_with_disposal_history),
        )
        .group_by(fallback_disposed_month)
    ).all()

    registered_by_month = {
        row.month: int(row.registered_count or 0) for row in registered_rows
    }
    disposed_by_month: dict[str, int] = {month: 0 for month in months}
    for row in [*disposed_history_rows, *fallback_disposed_rows]:
        disposed_by_month[row.month] = disposed_by_month.get(row.month, 0) + int(
            row.disposed_count or 0
        )

    return [
        MonthlyAssetStats(
            month=month,
            registered_count=registered_by_month.get(month, 0),
            disposed_count=disposed_by_month.get(month, 0),
        )
        for month in months
    ]


def get_recent_month_labels(month_count: int = 3) -> list[str]:
    today = datetime.now()
    month_start = datetime(today.year, today.month, 1)
    labels = []
    for offset in range(month_count - 1, -1, -1):
        year = month_start.year
        month = month_start.month - offset
        while month <= 0:
            month += 12
            year -= 1
        labels.append(f"{year:04d}-{month:02d}")
    return labels
