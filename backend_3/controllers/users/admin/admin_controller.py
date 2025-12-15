from models.users.admin import (
    get_all_users,
    get_user_detail,
    update_user_role,
    delete_user_admin
)
from models.users.subscriptions import set_subscription


def admin_get_users(db):
    return get_all_users(db)


def admin_get_user(db, user_id: str):
    return get_user_detail(db, user_id)


def admin_delete_user(db, user_id: str):
    delete_user_admin(db, user_id)
    return True


def admin_update_role(db, user_id: str, role: str):
    return update_user_role(db, user_id, role)


def admin_update_subscription(db, user_id: str, is_subscribed: bool):
    return set_subscription(db=db, email=None, is_subscribed=is_subscribed)
