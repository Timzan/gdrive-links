import trafaret as t
from trafaret.contrib.object_id import MongoId


user = t.Dict({
    t.Key('_id'): MongoId(),
    t.Key('username'): t.String(max_length=50),
    t.Key('pw_hash'): t.String(),
})


link = t.Dict({
    t.Key('_id'): MongoId(),
    t.Key('user_id'): MongoId(),
    t.Key('url'): t.String(),
    t.Key('filename'): t.String(),
    t.Key('file_id'): t.String(),
})


async def get_user_id(user_collection, username):
    rv = await (user_collection.find_one(
        {'username': username},
        {'_id': 1}))
    return rv['_id'] if rv else None
