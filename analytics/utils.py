import hashlib


def get_client_ip(request):
    """Safely extract client IP from request headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # HTTP_X_FORWARDED_FOR can be a comma-separated list of IPs
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def get_visitor_hash(request):
    """
    Generate an anonymous 64-character SHA-256 hash of the visitor's IP and User-Agent.
    We NEVER persist the raw IP address in the database for privacy and security.
    """
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    raw_identifier = f"{ip}|{user_agent}"
    return hashlib.sha256(raw_identifier.encode('utf-8')).hexdigest()

