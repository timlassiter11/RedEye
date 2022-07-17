

def calculate_taxes(base_fare: float, segments: int) -> float:
    # https://taxfoundation.org/understanding-the-price-of-your-plane-ticket/#:~:text=The%20U.S.%20government%20charges%20an,(and%20almost%20all%20do).
    # Excise tax
    taxes = base_fare * 0.075
    # Flight segment tax of $4.5 per segment
    taxes += 4.5 * segments
    # September 11th tax
    taxes += 5.6
    # Passenger facility charge (PFC)
    taxes += 4.5 * segments + 1
    return round(taxes, 2)