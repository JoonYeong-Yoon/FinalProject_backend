from models.users.subscriptions import set_subscription


def start_subscription(email: str, db):
    if not email:
        raise ValueError("INVALID_EMAIL")

    return set_subscription(
        db=db,
        email=email,
        is_subscribed=True
    )


def cancel_subscription(email: str, db):
    if not email:
        raise ValueError("INVALID_EMAIL")

    return set_subscription(
        db=db,
        email=email,
        is_subscribed=False
    )
