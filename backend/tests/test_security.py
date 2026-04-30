"""
安全模块测试
"""

import os
import pytest
from app.core.security import is_path_allowed, validate_scan_path


def test_validate_scan_path_blocks_system_dirs():
    """测试阻止扫描系统目录"""
    import platform
    if platform.system() == "Windows":
        with pytest.raises(ValueError, match="不允许扫描系统目录"):
            validate_scan_path("C:\\Windows\\System32\\config")
    else:
        with pytest.raises(ValueError, match="不允许扫描系统目录"):
            validate_scan_path("/etc/passwd")


def test_validate_scan_path_allows_normal_path(monkeypatch):
    """测试允许正常路径（未配置白名单时）"""
    # 默认未配置 SCAN_ALLOWED_ROOTS，允许所有路径
    path = validate_scan_path("/home/user/novels")
    assert os.path.isabs(path)


def test_is_path_allowed_no_config():
    """测试未配置白名单时允许所有路径"""
    # 默认 SCAN_ALLOWED_ROOTS 为空
    assert is_path_allowed("/any/path") is True
