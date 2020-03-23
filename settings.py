import pathlib
import yaml
from aiohttp import web
import motor.motor_asyncio as aiomotor
from core import db


BASE_DIR = pathlib.Path(__file__).parent
config_path = BASE_DIR / 'config' / 'config.yaml'
templates_path = pathlib.Path(__file__).parent / 'templates'


def get_config(path):
    with open(path) as f:
        conf = yaml.safe_load(f)
    return conf


async def init_mongo(conf, loop):
    host = '127.0.0.1'
    conf['host'] = host
    mongo_uri = f"mongodb://{conf['host']}:{conf['port']}"
    connection = aiomotor.AsyncIOMotorClient(
        mongo_uri,
        io_loop=loop)
    db_name = conf['database']
    return connection[db_name]


def redirect(request, name, **kwargs):
    router = request.app.router
    location = router[name].url_for(**kwargs)
    return web.HTTPFound(location=location)


async def validate_register_form(mongo, form):
    error = None
    user_id = await db.get_user_id(mongo.user, form['username'])

    if not form['username']:
        error = 'You have to enter a username'
    elif not form['password']:
        error = 'You have to enter a password'
    elif form['password'] != form['password2']:
        error = 'The passwords do not match'
    elif user_id is not None:
        error = 'The username is already taken'
    return error


async def validate_password_form(form):
    error = None

    if not form['password']:
        error = 'You have to enter a password'
    elif form['password'] != form['password2']:
        error = 'The passwords do not match'
    return error


config = get_config(config_path)
