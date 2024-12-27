
def table_exists(cn, table_name):
    c = cn.cursor()
    c.execute(f"""
        select count(*)
        from sqlite_master
        where type="table" and name="{table_name}"
    """)
    return c.fetchone()[0] > 0


def column_exists(cn, table_name, column_name):
    c = cn.cursor()
    c.execute(f"""
        select count(*)
        from pragma_table_info("{table_name}")
        where name="{column_name}"
    """)
    return c.fetchone()[0] > 0


def index_exists(cn, table_name, index_name):
    c = cn.cursor()
    c.execute(f"""
        select count(*)
        from sqlite_master
        where type="index" and name="{index_name}"
    """)
    return c.fetchone()[0] > 0


def current_version(cn):
    try:
        c = cn.cursor()
        c.execute("""
            select version
            from migrations
            order by id desc
            limit 1
        """)
        return c.fetchone()[0]
    except Exception:
        return 0
