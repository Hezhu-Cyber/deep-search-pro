import asyncio

from api.context import (
    get_session_context,
    get_thread_context,
    reset_session_context,
    set_session_context,
    set_thread_context,
)


def test_defaults_are_none():
    assert get_session_context() is None
    assert get_thread_context() is None


def test_set_and_reset_restores_default():
    token = set_session_context("/sess/abc")
    assert get_session_context() == "/sess/abc"
    reset_session_context(token)
    assert get_session_context() is None


def test_context_isolation_between_tasks():
    async def worker(name):
        s_token = set_session_context(f"/sess/{name}")
        t_token = set_thread_context(f"thread-{name}")
        await asyncio.sleep(0)
        assert get_session_context() == f"/sess/{name}"
        assert get_thread_context() == f"thread-{name}"
        reset_session_context(s_token, t_token)

    async def main():
        await asyncio.gather(worker("A"), worker("B"))

    asyncio.run(main())