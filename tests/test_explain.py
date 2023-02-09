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
    ),
)
async def test_explain(ds, sql, expected):
    response = await ds.client.get("/test/-/explain", params={"sql": sql})
    assert response.status_code == 200
    data = response.json()
    assert data == expected
