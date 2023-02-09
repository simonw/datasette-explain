from datasette import hookimpl, Response


async def explain(request, datasette):
    sql = request.args.get("sql")
    if not sql:
        return Response.json({"ok": False, "error": "No SQL query"})
    database = request.url_vars["database"]
    try:
        db = datasette.get_database(database)
    except KeyError:
        return Response.json({"ok": False, "error": "No such database"})
    try:
        explain_result = await db.execute("explain " + sql)
        explain_query_result = await db.execute("explain query plan " + sql)
    except Exception as e:
        return Response.json({"ok": False, "error": str(e)})

    # Build the explain_tree
    explain_tree = []
    node_lookup = {}
    for row in explain_query_result.rows:
        detail = row["detail"]
        node = {
            "detail": detail,
            "children": [],
        }
        node_lookup[row["id"]] = node
        if row["parent"] == 0:
            explain_tree.append(node)
        else:
            node_lookup[row["parent"]]["children"].append(node)

    # To figure out the tables referenced by the query, look at the rootpage
    # values in the EXPLAIN output for any OpenRead opcodes
    rootpages = set()
    for row in explain_result.rows:
        if row["opcode"] == "OpenRead":
            rootpages.add(row["p2"])
    # Look up the table names for those rootpages
    table_names = [
        r["name"]
        for r in await db.execute(
            "select name from sqlite_master where type = 'table' and rootpage in ({})".format(
                ", ".join("?" * len(rootpages))
            ),
            list(rootpages),
        )
    ]
    tables = [
        {
            "name": name,
            "columns": await db.table_columns(name),
        }
        for name in table_names
    ]
    return Response.json(
        {
            "ok": True,
            "explain_tree": explain_tree,
            "tables": tables,
        },
        default=repr,
    )


@hookimpl
def register_routes():
    return [
        ("^/(?P<database>[^/]+)/-/explain$", explain),
    ]


JS = """
(() => {
    const buildTree = (root) => {
        const li = document.createElement('li');
        // li.style.marginTop = '0.5em';
        // li.style.marginBottom = '0.5em';
        li.innerText = root.detail;
        if (root.children.length) {
            const ul = document.createElement('ul');
            ul.style.paddingLeft = '2em';
            root.children.forEach(child => {
                ul.appendChild(buildTree(child));
            });
            li.appendChild(ul);
        }
        return li;
    }
    let previousSql = '';
    const sqlForm = document.querySelector('form.sql');
    const div = document.createElement('div');
    div.style.marginTop = '1em';
    div.style.marginBottom = '1em';
    sqlForm.appendChild(div);
    setInterval(() => {
        const sql = editor.state.doc.toString();
        if (sql !== previousSql) {
            previousSql = sql;
            fetch('/DBNAME/-/explain?sql=' + encodeURIComponent(sql)).then(response => response.json()).then(data => {
                if (data.ok) {
                    const explainTree = data.explain_tree;
                    const tables = data.tables;
                    div.innerHTML = '';
                    const listWrapper = document.createElement('div');
                    let h3Explain = document.createElement('h3');
                    h3Explain.innerText = 'Explain query plan';
                    div.appendChild(h3Explain);
                    listWrapper.style.fontFamily = 'courier';
                    listWrapper.style.fontSize = '0.85em';
                    const ul = document.createElement('ul');
                    explainTree.forEach(root => {
                        ul.appendChild(buildTree(root));
                    });
                    listWrapper.appendChild(ul);
                    div.appendChild(listWrapper);
                    let tablesDiv = document.createElement('div');
                    tablesDiv.style.marginTop = '1em';
                    let h3 = document.createElement('h3');
                    h3.innerText = 'Tables used by this query';
                    tablesDiv.appendChild(h3);
                    tables.forEach(table => {
                        let tableDiv = document.createElement('div');
                        let h4 = document.createElement('h4');
                        h4.innerText = table.name;
                        tableDiv.appendChild(h4);
                        let tableColumns = table.columns.join(', ');
                        let p = document.createElement('p');
                        p.style.fontSize = '0.85em';
                        p.innerText = tableColumns;
                        tableDiv.appendChild(p);
                        tablesDiv.appendChild(tableDiv);
                    });
                    div.appendChild(tablesDiv);
                }
                else {
                    let error = document.createElement('p');
                    error.innerText = data.error;
                    div.innerHTML = '';
                    if (data.error != 'No SQL query') {
                        error.style.borderTop = '1px solid rgba(208,2,27,0.8)';
                        error.style.borderBottom = '1px solid rgba(208,2,27,0.8)';
                        error.style.backgroundColor = 'rgba(208,2,27,0.2)';
                        error.style.padding = '0.5em';
                        div.appendChild(error);
                    }
                }
            });
        }
    }, 200);
})();
"""


@hookimpl
def extra_body_script(request, view_name):
    if view_name == "database":
        return JS.replace("DBNAME", request.url_vars["database"])
