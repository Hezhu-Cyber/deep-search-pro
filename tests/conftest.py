import pytest


@pytest.fixture(autouse=True)
def _isolate_monitor():
    """每个测试前后重置 monitor 的 WebSocket 绑定，避免测试间相互影响。"""
    from api.monitor import monitor

    monitor.websocket_manager = None
    yield
    monitor.websocket_manager = None