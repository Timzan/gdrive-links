import asyncio
import logging
import jinja2
import aiohttp_jinja2
from aiohttp import web
from aiojobs.aiohttp import setup as setup_jobs
from aiohttp_security import setup as setup_security
from aiohttp_security import CookiesIdentityPolicy
from core.security import AuthorizationPolicy
from core.routes import setup_routes
from settings import config, init_mongo, templates_path, BASE_DIR
from core.views import MyHandler


async def setup_mongo(app, conf, loop):
    mongo = await init_mongo(conf['mongo'], loop)

    async def close_mongo(app):
        mongo.client.close()

    app.on_cleanup.append(close_mongo)
    return mongo


def setup_jinja(app):
    aiohttp_jinja2.setup(
        app, loader=jinja2.FileSystemLoader(str(templates_path))
    )


async def init(loop):
    app = web.Application(loop=loop)
    mongo = await setup_mongo(app, config, loop)

    setup_jobs(app)

    setup_jinja(app)
    setup_security(app, CookiesIdentityPolicy(), AuthorizationPolicy(mongo))

    handler = MyHandler(mongo)

    setup_routes(app, handler, BASE_DIR)
    host, port = config['host'], config['port']
    return app, host, port


def main():
    # logging.basicConfig(level=logging.DEBUG)

    loop = asyncio.get_event_loop()
    app, host, port = loop.run_until_complete(init(loop))
    web.run_app(app, host=host, port=port)


if __name__ == '__main__':
    main()
