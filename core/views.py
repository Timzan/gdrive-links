import aiohttp_jinja2
import re
import time
from aiohttp import web
from aiohttp_security import authorized_userid, forget, remember
from bson import ObjectId
from settings import redirect, validate_register_form, validate_password_form
from core.security import generate_password_hash, check_password_hash, auth_required
import urllib.parse as url_parser
from settings import config
import requests
import zipfile
import tempfile
from aiojobs.aiohttp import spawn


async def background_download(request, mongo):
    user_id = await authorized_userid(request)
    api_key = config['api_key']
    file_ids = await mongo.link.find({'user_id': ObjectId(user_id)}, {'_id': 0, 'file_id': 1}).to_list(300)
    urls = []
    metadata_urls = []
    for f in file_ids:
        f_id = f['file_id']
        urls.append(f'https://www.googleapis.com/drive/v3/files/{f_id}?key={api_key}&alt=media')
        metadata_urls.append(f'https://www.googleapis.com/drive/v3/files/{f_id}?key={api_key}')
    with tempfile.SpooledTemporaryFile() as tmp:
        for meta, url in zip(metadata_urls, urls):
            r = requests.get(meta)
            filename = r.json()['name']
            time.sleep(2)
            r = requests.get(url, stream=True)
            r.raise_for_status()
            raw_file = r.raw.data
            with zipfile.ZipFile(tmp, 'a', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(filename, raw_file)
            tmp.seek(0)
            time.sleep(2)

        return web.Response(body=tmp.read(), content_type='application/zip')


class MyHandler:

    def __init__(self, mongo):
        self._mongo = mongo

    @property
    def mongo(self):
        return self._mongo

    @aiohttp_jinja2.template('index.html')
    async def index(self, request):
        user_id = await authorized_userid(request)
        if user_id is None:
            router = request.app.router
            location = router['public_homepage'].url_for()
            raise web.HTTPFound(location=location)
        user = await self.mongo.user.find_one({'_id': ObjectId(user_id)})
        links = await self.mongo.link.find({'user_id': ObjectId(user_id)}).to_list(300)
        form = await request.post()
        error_msg = None
        if request.method == 'POST':
            if form['url']:
                url_pattern = re.compile(r"^(https://drive\.google\.com/open\?id=.+)")
                url = form['url']
                if url_pattern.match(string=url):
                    file_id = url_parser.parse_qsl(url)[0][1]
                    await self.mongo.link.insert_one({
                        'user_id': ObjectId(user_id),
                        'url': form['url'],
                        'filename': form['filename'],
                        'file_id': file_id
                    })
                    return redirect(request, 'index')
                else:
                    error_msg = "It seems like URL doesnt match the pattern"

        endpoint = request.match_info.route.name
        return {
            'endpoint': endpoint,
            'user': user,
            'links': links,
            'form': form,
            'error_msg': error_msg,
        }

    @aiohttp_jinja2.template('index.html')
    async def public_homepage(self, request):
        user_id = await authorized_userid(request)
        if user_id:
            return redirect(request, 'index')
        return {'endpoint': request.match_info.route.name}

    @aiohttp_jinja2.template('login.html')
    async def login(self, request):
        user_id = await authorized_userid(request)
        if user_id:
            return redirect(request, 'index')
        form = await request.post()
        user = await self.mongo.user.find_one({'username': form['username']})

        if user is None:
            error = 'Invalid username'
        elif not check_password_hash(user['pw_hash'], form['password']):
            error = 'Invalid password'
        else:
            response = redirect(request, 'index')
            await remember(request, response, str(user['_id']))
            return response

        return {'error': error, 'form': form}

    @aiohttp_jinja2.template('login.html')
    async def login_page(self, request):
        user_id = await authorized_userid(request)
        if user_id:
            return redirect(request, 'index')
        return {'error': None, 'form': None}

    async def logout(self, request):
        response = redirect(request, 'index')
        await forget(request, response)
        return response

    @aiohttp_jinja2.template('register.html')
    async def register(self, request):
        user_id = await authorized_userid(request)
        if user_id:
            return redirect(request, 'index')

        form = await request.post()
        error = await validate_register_form(self.mongo, form)

        if error is None:
            await self.mongo.user.insert_one(
                {'username': form['username'],
                 'pw_hash': generate_password_hash(form['password'])})
            return redirect(request, 'login')
        return {'error': error, 'form': form}

    @aiohttp_jinja2.template('register.html')
    async def register_page(self, request):
        user_id = await authorized_userid(request)
        if user_id:
            return redirect(request, 'index')
        return {'error': None, 'form': None}

    @auth_required
    async def remove_link(self, request):
        link_id = request.match_info['link_id']
        if request.method == 'POST':
            await self.mongo.link.delete_one({'_id': ObjectId(link_id)})

        return redirect(request, 'index')

    @auth_required
    async def remove_user(self, request):
        user_id = request.match_info['user_id']
        if request.method == 'POST':
            response = redirect(request, 'index')
            await forget(request, response)
            await self.mongo.user.delete_one({'_id': ObjectId(user_id)})
            await self.mongo.link.delete_many({'user_id': ObjectId(user_id)})
            return response

    @aiohttp_jinja2.template('change_password.html')
    async def change_password(self, request):
        user_id = await authorized_userid(request)
        if not user_id:
            return redirect(request, 'index')

        form = await request.post()
        error = await validate_password_form(form)
        if request.method == 'POST':

            if error is None:
                await self.mongo.user.update_one(
                    {'_id': ObjectId(user_id)},
                    {'$set': {'pw_hash': generate_password_hash(form['password'])}})
                return redirect(request, 'index')

        return {'form': form, 'error': error}

    @aiohttp_jinja2.template('change_password.html')
    async def change_password_page(self, request):
        user_id = await authorized_userid(request)
        if not user_id:
            return redirect(request, 'index')
        return {'error': None, 'form': None}

    @auth_required
    async def download_file(self, request):
        api_key = config['api_key']
        file_id = request.match_info['file_id']
        return web.HTTPFound(f'https://www.googleapis.com/drive/v3/files/{file_id}?key={api_key}&alt=media')

    async def background_handler(self, request):
        job = await spawn(request, background_download(request, self.mongo))
        return await job.wait()

























