import structlog

logger = structlog.get_logger("classifier")

# Comprehensive list of keywords indicating a complex task that should be routed to Cloud
COMPLEX_KEYWORDS = [
    # Programming & Tech
    "code", "python", "javascript", "java", "c++", "golang", "react", "html", "css",
    "sql", "database", "lập trình", "viết script", "debug", "lỗi", "error", "api", "thuật toán",
    # Math & Logic
    "toán", "giải bài", "phương trình", "logic", "chứng minh", "tính toán",
    # Creative & Long-form
    "thơ", "poem", "bài văn", "tiểu luận", "essay", "câu chuyện", "kịch bản", "story",
    "viết một đoạn", "sáng tác",
    # Analysis & Reasoning
    "phân tích", "so sánh", "giải thích", "explain", "tóm tắt", "summarize", "đánh giá",
    "tại sao", "như thế nào", "how to",
    # Formatting
    "bảng", "table", "markdown", "json", "csv"
]

# Compile a regex pattern for fast matching (case-insensitive, whole word or substring)
# Using a simple substring match is usually fast enough, but we want to avoid matching parts of short unrelated words if possible.
# Actually, simple substring match with .lower() is extremely fast and robust for this use case.

def classify_prompt_complexity(prompt: str) -> str:
    """
    Dynamically classify the prompt into a routing tag based on complexity.
    Returns: 'fast_ok', 'high_quality', or 'default'.
    Execution time target: < 1ms
    """
    if not prompt:
        return "fast_ok"

    prompt_lower = prompt.lower()
    prompt_length = len(prompt_lower)

    # 1. Very short prompts are usually simple greetings or basic questions
    if prompt_length < 25:
        # Check if even a short prompt has a complex keyword (e.g. "viết code python")
        if any(kw in prompt_lower for kw in ["code", "toán", "thơ", "lập trình"]):
            return "high_quality"
        return "fast_ok"

    # 2. Keyword matching for high complexity
    # We use simple substring matching which is highly optimized in Python's C core
    for kw in COMPLEX_KEYWORDS:
        if kw in prompt_lower:
            logger.debug("Prompt classified as high_quality due to keyword", keyword=kw)
            return "high_quality"

    # 3. Long prompts naturally require larger context windows and better attention mechanisms
    if prompt_length > 250:
        logger.debug("Prompt classified as high_quality due to length", length=prompt_length)
        return "high_quality"

    # Default fallback for medium length prompts without complex keywords
    return "default"
