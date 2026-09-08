from tools.db_tools import execute_sql_query, get_table_data


def test_table_name_guard_blocks_injection():
    result = get_table_data.invoke({"table_name": "users; DROP TABLE users"})
    assert "非法表名" in result


def test_write_sql_rejected():
    result = execute_sql_query.invoke({"query": "DELETE FROM users"})
    assert "已拒绝执行" in result


def test_multi_statement_rejected():
    result = execute_sql_query.invoke({"query": "SELECT 1; SELECT 2"})
    assert "已拒绝执行" in result


def test_select_allowed_format_only():
    result = execute_sql_query.invoke({"query": "update users set name='x'"})
    assert "已拒绝执行" in result