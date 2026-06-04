import sys


def import_isolated_app():
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]

    import httpx

    from app.main import app
    from app.extensions import Base, db_session, engine

    return app, Base, db_session, engine, httpx
