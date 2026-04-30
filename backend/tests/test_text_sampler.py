"""
文本采样工具测试
"""

from app.core.text_sampler import sample_text


def test_sample_text_short():
    """测试短文本不需要采样"""
    text = "短文本"
    result = sample_text(text, max_chars=100)
    assert result == text


def test_sample_text_head_strategy():
    """测试 head 策略"""
    text = "A" * 100
    result = sample_text(text, max_chars=10, strategy="head")
    assert result == "A" * 10


def test_sample_text_head_tail_strategy():
    """测试 head_tail 策略"""
    text = "A" * 100
    result = sample_text(text, max_chars=20, strategy="head_tail")
    assert "省略中间部分" in result
    assert len(result) < 100


def test_sample_text_spread_strategy():
    """测试 spread 策略"""
    text = "ABCDEFGHIJ" * 1000  # 10000 字符
    result = sample_text(text, max_chars=1000, strategy="spread")
    assert len(result) <= 1100  # 允许一些分隔符的余量
    assert len(result) < len(text)
