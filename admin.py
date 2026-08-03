from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session, joinedload

from database import get_db
import models
import schemas
from security import hash_password, require_role

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_user_or_404(db: Session, user_id: int) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


def _get_subject_or_404(db: Session, subject_id: int) -> models.Subject:
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    return subject


def _check_subject_name_unique(db: Session, name: str, exclude_id: Optional[int] = None) -> None:
    q = db.query(models.Subject).filter(models.Subject.name == name)
    if exclude_id:
        q = q.filter(models.Subject.id != exclude_id)
    if q.first():
        raise HTTPException(status_code=400, detail="La materia ya existe")


# ---------------------------------------------------------------------------
# Admin dashboard summary
# ---------------------------------------------------------------------------
@router.get("/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    return {
        "students": db.query(models.User).filter(models.User.role == models.RoleEnum.STUDENT).count(),
        "tutors": db.query(models.User).filter(models.User.role == models.RoleEnum.TUTOR).count(),
        "subjects": db.query(models.Subject).count(),
        "bookings": db.query(models.Booking).count(),
    }


# ---------------------------------------------------------------------------
# STUDENTS
# ---------------------------------------------------------------------------
@router.get("/students", response_model=List[schemas.UserOut])
def list_admin_students(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    return db.query(models.User).filter(models.User.role == models.RoleEnum.STUDENT).order_by(models.User.created_at.desc()).all()


@router.get("/students/{student_id}", response_model=schemas.UserOut)
def get_admin_student(
    student_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    user = _get_user_or_404(db, student_id)
    if user.role != models.RoleEnum.STUDENT:
        raise HTTPException(status_code=400, detail="El usuario no es un estudiante")
    return user


@router.post("/students", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_admin_student(
    payload: schemas.UserAdminCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    user = models.User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=models.RoleEnum.STUDENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(models.StudentProfile(user_id=user.id))
    db.commit()
    return user


@router.put("/students/{student_id}", response_model=schemas.UserOut)
def update_admin_student(
    student_id: int,
    payload: schemas.UserAdminUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    user = _get_user_or_404(db, student_id)
    if user.role != models.RoleEnum.STUDENT:
        raise HTTPException(status_code=400, detail="El usuario no es un estudiante")
    if payload.email and payload.email != user.email:
        if db.query(models.User).filter(models.User.email == payload.email, models.User.id != user.id).first():
            raise HTTPException(status_code=400, detail="El correo ya está registrado")
        user.email = payload.email
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_student(
    student_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    user = _get_user_or_404(db, student_id)
    if user.role != models.RoleEnum.STUDENT:
        raise HTTPException(status_code=400, detail="El usuario no es un estudiante")
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# TUTORS
# ---------------------------------------------------------------------------
@router.get("/tutors", response_model=List[schemas.UserOut])
def list_admin_tutors(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    return db.query(models.User).filter(models.User.role == models.RoleEnum.TUTOR).order_by(models.User.created_at.desc()).all()


@router.get("/tutors/{tutor_id}", response_model=schemas.TutorProfileOut)
def get_admin_tutor(
    tutor_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    user = _get_user_or_404(db, tutor_id)
    if user.role != models.RoleEnum.TUTOR:
        raise HTTPException(status_code=400, detail="El usuario no es un tutor")
    profile = db.query(models.TutorProfile).options(joinedload(models.TutorProfile.subjects)).filter(
        models.TutorProfile.user_id == user.id
    ).first()
    if not profile:
        profile = models.TutorProfile(user_id=user.id, hourly_rate=0)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.post("/tutors", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_admin_tutor(
    payload: schemas.UserAdminCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")

    user = models.User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=models.RoleEnum.TUTOR,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(models.TutorProfile(user_id=user.id, hourly_rate=0))
    db.commit()
    return user


@router.put("/tutors/{tutor_id}", response_model=schemas.UserOut)
def update_admin_tutor(
    tutor_id: int,
    payload: schemas.UserAdminUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    user = _get_user_or_404(db, tutor_id)
    if user.role != models.RoleEnum.TUTOR:
        raise HTTPException(status_code=400, detail="El usuario no es un tutor")
    if payload.email and payload.email != user.email:
        if db.query(models.User).filter(models.User.email == payload.email, models.User.id != user.id).first():
            raise HTTPException(status_code=400, detail="El correo ya está registrado")
        user.email = payload.email
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/tutors/{tutor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_tutor(
    tutor_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    user = _get_user_or_404(db, tutor_id)
    if user.role != models.RoleEnum.TUTOR:
        raise HTTPException(status_code=400, detail="El usuario no es un tutor")
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# SUBJECTS
# ---------------------------------------------------------------------------
@router.get("/subjects", response_model=List[schemas.SubjectOut])
def list_admin_subjects(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    return db.query(models.Subject).order_by(models.Subject.name).all()


@router.post("/subjects", response_model=schemas.SubjectOut, status_code=status.HTTP_201_CREATED)
def create_admin_subject(
    payload: schemas.SubjectCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    _check_subject_name_unique(db, payload.name)
    subject = models.Subject(name=payload.name)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.put("/subjects/{subject_id}", response_model=schemas.SubjectOut)
def update_admin_subject(
    subject_id: int,
    payload: schemas.SubjectCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    subject = _get_subject_or_404(db, subject_id)
    _check_subject_name_unique(db, payload.name, exclude_id=subject.id)
    subject.name = payload.name
    db.commit()
    db.refresh(subject)
    return subject


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    subject = _get_subject_or_404(db, subject_id)
    db.delete(subject)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# BOOKINGS
# ---------------------------------------------------------------------------
@router.get("/bookings", response_model=List[schemas.BookingOut])
def list_admin_bookings(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    return db.query(models.Booking).order_by(models.Booking.created_at.desc()).all()


@router.get("/bookings/{booking_id}", response_model=schemas.BookingOut)
def get_admin_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return booking


@router.post("/bookings", response_model=schemas.BookingOut, status_code=status.HTTP_201_CREATED)
def create_admin_booking(
    payload: schemas.BookingAdminCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time debe ser mayor que start_time")

    student = db.query(models.User).filter(models.User.id == payload.student_user_id).first()
    tutor = db.query(models.User).filter(models.User.id == payload.tutor_user_id, models.User.role == models.RoleEnum.TUTOR).first()
    if not student:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor no encontrado")
    if payload.subject_id and not db.query(models.Subject).filter(models.Subject.id == payload.subject_id).first():
        raise HTTPException(status_code=404, detail="Materia no encontrada")

    booking = models.Booking(
        student_user_id=payload.student_user_id,
        tutor_user_id=payload.tutor_user_id,
        subject_id=payload.subject_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        notes=payload.notes,
        status=payload.status,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.put("/bookings/{booking_id}", response_model=schemas.BookingOut)
def update_admin_booking(
    booking_id: int,
    payload: schemas.BookingAdminUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    if payload.student_user_id is not None:
        booking.student_user_id = payload.student_user_id
    if payload.tutor_user_id is not None:
        booking.tutor_user_id = payload.tutor_user_id
    if payload.subject_id is not None:
        booking.subject_id = payload.subject_id
    if payload.start_time is not None:
        booking.start_time = payload.start_time
    if payload.end_time is not None:
        booking.end_time = payload.end_time
    if payload.notes is not None:
        booking.notes = payload.notes
    if payload.status is not None:
        booking.status = payload.status
    if booking.end_time <= booking.start_time:
        raise HTTPException(status_code=400, detail="end_time debe ser mayor que start_time")
    db.commit()
    db.refresh(booking)
    return booking


@router.delete("/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role(models.RoleEnum.ADMIN)),
):
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    db.delete(booking)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
