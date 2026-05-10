def cart_hot_cache_key(user_id):
    return f"hot:carts:cart:{int(user_id)}"
