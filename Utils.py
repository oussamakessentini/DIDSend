def format_hex(n):
    return f"0x{n:02X}"

def is_hex(s):
    try:
        int(s, 16)  # Try converting to an integer with base 16
        return True
    except ValueError:
        return False