from .users import get_referrer, mark_referral_rewarded
from .cashback import add_transaction

REFERRER_REWARD=300.0
FRIEND_REWARD=300.0

def reward_referral_if_needed(new_customer_id, order_id):
    referrer=get_referrer(new_customer_id)
    if not referrer: return None
    if not mark_referral_rewarded(new_customer_id): return None
    add_transaction(referrer, REFERRER_REWARD, 'referral', order_id, 'Бонус за приглашение друга')
    add_transaction(new_customer_id, FRIEND_REWARD, 'referral', order_id, 'Бонус за первую покупку по приглашению')
    return referrer
