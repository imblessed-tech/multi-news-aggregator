import hashlib

def generate_article_id(url: str) -> str:
    return hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()