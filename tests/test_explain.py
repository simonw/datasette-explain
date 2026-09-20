from datasette.app import Datasette
import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def ds():
    datasette = Datasette(memory=True)
    db = datasette.add_memory_database("test")
    await db.execute_write("create table if not exists t1 (id integer primary key)")
    await db.execute_write("create table if not exists t2 (id integer primary key)")
    return datasette


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sql,expected",
    (
        (
            "select 1",
            {
                "ok": True,
                "explain_tree": [{"detail": "SCAN CONSTANT ROW", "children": []}],
                "tables": [],
            },
        ),
        (
            "select * from t1",
            {
                "ok": True,
                "explain_tree": [{"detail": "SCAN t1", "children": []}],
                "tables": [{"name": "t1", "columns": ["id"]}],
            },
        ),
        (
            "select * from t1 where id > :id",
            {
                "ok": True,
                "explain_tree": [
                    {
                        "detail": "SEARCH t1 USING INTEGER PRIMARY KEY (rowid>?)",
                        "children": [],
                    }
                ],
                "tables": [{"name": "t1", "columns": ["id"]}],
            },
        ),
        (
            "select id, (select id from t2 where t2.id = t1.id) from t1",
            {
                "ok": True,
                "explain_tree": [
                    {"detail": "SCAN t1", "children": []},
                    {
                        "detail": "CORRELATED SCALAR SUBQUERY 1",
                        "children": [
                            {
                                "detail": "SEARCH t2 USING INTEGER PRIMARY KEY (rowid=?)",
                                "children": [],
                            }
                        ],
                    },
                ],
                "tables": [
                    {"name": "t1", "columns": ["id"]},
                    {"name": "t2", "columns": ["id"]},
                ],
            },
        ),
        (
            "select count(*) from t1 where id > :id",
            {
                "ok": True,
                "explain_tree": [
                    {
                        "detail": "SEARCH t1 USING INTEGER PRIMARY KEY (rowid>?)",
                        "children": [],
                    }
                ],
                "tables": [{"name": "t1", "columns": ["id"]}],
            },
        ),
        (
            "explain select count(*) from t1",
            {
                "ok": True,
                "explain_tree": [],
                "tables": [],
            },
        ),
    ),
)
async def test_explain(ds, sql, expected):
    params = {"sql": sql}
    response = await ds.client.get("/test/-/explain", params=params)
    assert response.status_code == 200
    data = response.json()
    assert data == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params,expected_detail",
    [
        (
            {"pattern": "hello%"},
            "SEARCH items USING COVERING INDEX items_name (name>? AND name<?)",
        ),
        ({"pattern": "%hello"}, "SCAN items"),
        ({"pattern": ""}, "SCAN items"),
        ({}, "SCAN items"),
    ],
)
async def test_explain_parameter_values(ds, params, expected_detail):
    db = ds.get_database("test")
    await db.execute_write("create table items (name text)")
    await db.execute_write("create index items_name on items (name collate nocase)")
    response = await ds.client.get(
        "/test/-/explain",
        params={"sql": "select * from items where name like :pattern", **params},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["explain_tree"] == [{"detail": expected_detail, "children": []}]
