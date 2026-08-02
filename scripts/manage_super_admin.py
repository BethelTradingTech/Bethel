"""Create or reset the single real Bethel Super Admin account.

Run interactively from the repository root. Password input is hidden and is
never written to source code, shell history, or application logs.
"""

from getpass import getpass
import re
import sys

from api.auth.models.user import User
from api.auth.models.super_admin_profile import SuperAdminProfile
from api.auth.services.security import hash_password
from api.database import Base, SessionLocal, engine


def valid_password(password: str) -> bool:
    return (
        len(password) >= 14
        and bool(re.search(r"[a-z]", password))
        and bool(re.search(r"[A-Z]", password))
        and bool(re.search(r"\d", password))
        and bool(re.search(r"[^A-Za-z0-9]", password))
    )


def main() -> int:
    email = input("Real Super Admin email: ").strip().casefold()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        print("Enter a valid email address.")
        return 1

    mobile = input("Mobile number in international format (example +12465551234): ").strip()
    mobile = "".join(char for char in mobile if char.isdigit() or char == "+")
    if not re.fullmatch(r"\+[1-9]\d{7,14}", mobile):
        print("Use international E.164 format beginning with + and country code.")
        return 1

    password = getpass("Create password (14+ characters): ")
    if not valid_password(password):
        print("Use 14+ characters with uppercase, lowercase, number, and symbol.")
        return 1
    if password != getpass("Confirm password: "):
        print("Passwords do not match.")
        return 1

    confirmation = input(f'Type CREATE SUPER ADMIN {email}: ').strip()
    if confirmation != f"CREATE SUPER ADMIN {email}":
        print("Cancelled.")
        return 1

    Base.metadata.create_all(bind=engine, tables=[SuperAdminProfile.__table__])
    db = SessionLocal()
    try:
        for other in db.query(User).filter(User.role == "super_admin").all():
            if other.email.casefold() != email:
                other.role = "admin"

        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(email=email)
            db.add(user)

        user.password_hash = hash_password(password)
        user.role = "super_admin"
        user.active = True
        db.flush()

        duplicate_mobile = db.query(SuperAdminProfile).filter(
            SuperAdminProfile.mobile_number == mobile,
            SuperAdminProfile.user_id != user.id,
        ).first()
        if duplicate_mobile is not None:
            print("That mobile number already belongs to another account.")
            db.rollback()
            return 1

        profile = db.query(SuperAdminProfile).filter(
            SuperAdminProfile.user_id == user.id
        ).first()
        if profile is None:
            profile = SuperAdminProfile(user_id=user.id, mobile_number=mobile)
            db.add(profile)
        else:
            profile.mobile_number = mobile
        profile.mobile_verified = False
        db.commit()
        print(f"Super Admin ready: {email} / {mobile}")
        print("Mobile verification status: pending OTP provider configuration.")
        print("All other Super Admin accounts were reduced to regular admin.")
        return 0
    except Exception:
        db.rollback()
        print("Super Admin setup failed. No password was logged.")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
