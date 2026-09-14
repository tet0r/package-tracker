from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, pipeline, schemas
from ..db import get_db

router = APIRouter()


@router.get("", response_model=list[schemas.PackageOut])
def list_packages(include_archived: bool = False, db: Session = Depends(get_db)):
    query = db.query(models.Package)
    if not include_archived:
        query = query.filter_by(archived=False)
    return query.order_by(models.Package.created_at.desc()).all()


@router.get("/{package_id}", response_model=schemas.PackageDetailOut)
def get_package(package_id: int, db: Session = Depends(get_db)):
    package = db.get(models.Package, package_id)
    if package is None:
        raise HTTPException(404, "Package not found")
    return package


@router.post("", response_model=schemas.PackageOut, status_code=201)
def create_package(payload: schemas.PackageCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Package).filter_by(tracking_number=payload.tracking_number).first()
    if existing:
        raise HTTPException(409, "Tracking number already tracked")
    package = models.Package(
        tracking_number=payload.tracking_number,
        item_name=payload.item_name,
        carrier=payload.carrier,
        status="unknown",
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


@router.patch("/{package_id}", response_model=schemas.PackageOut)
def update_package(package_id: int, payload: schemas.PackageUpdate, db: Session = Depends(get_db)):
    package = db.get(models.Package, package_id)
    if package is None:
        raise HTTPException(404, "Package not found")
    if payload.item_name is not None:
        package.item_name = payload.item_name
    if payload.archived is not None:
        package.archived = payload.archived
    db.commit()
    db.refresh(package)
    return package


@router.delete("/{package_id}", status_code=204)
def delete_package(package_id: int, db: Session = Depends(get_db)):
    package = db.get(models.Package, package_id)
    if package is None:
        raise HTTPException(404, "Package not found")
    db.delete(package)
    db.commit()


@router.post("/scan-now")
def scan_now():
    pipeline.run_email_scan()
    return {"status": "ok"}


@router.post("/refresh-now")
def refresh_now():
    pipeline.run_tracking_refresh()
    return {"status": "ok"}
