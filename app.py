# -*- coding: utf-8 -*-

from flask import Flask, request, json, redirect, send_file
from flask_httpauth import HTTPBasicAuth
from datetime import datetime
from shutil import move
from werkzeug.routing import BaseConverter
# from werkzeug.utils import secure_filename

import logging
import os

class RegexConverter(BaseConverter):
    def __init__(self, url_map, *args):
        super(RegexConverter, self).__init__(url_map)
        self.regex = args[0]

app = Flask(__name__)
auth = HTTPBasicAuth()
# 将自定义转换器添加到转换器字典中，并且指定转换器使用时的名字为：regex
app.url_map.converters['regex'] = RegexConverter
BASE_PATH = "/tmp/downloads"

def _init_logger():
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler("./logs/%s.log" % datetime.now().strftime("%Y%m%d"), encoding='utf-8')
    # handler.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s][%(filename)s - %(funcName)s][%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    console = logging.StreamHandler()
    # console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(handler)
    logger.addHandler(console)
    logger.info("logger was initialization completed.")

logger = logging.getLogger(__name__)
_init_logger()

users = [
    {'username': "nginx", 'password': "upload_module"},
]

@auth.get_password
def get_password(username):
    for user in users:
        if user.get('username') == username:
            return user.get('password')
    return None

@app.route('/downloads/<regex(".+\.[a-zA-Z0-9]+"):path>', methods=['GET'])
@auth.login_required
def downloads(path):
    filename = "%s/%s" % (BASE_PATH, path)
    if os.path.exists(filename):
        logger.info("\"%s\" was downloaded by [%s]" % (filename,
                                                       request.remote_addr))
        return send_file(filename)
    else:
        logger.info("\"%s\" is not exists for [%s]" % (filename,
                                                       request.remote_addr))
        return "\"%s\" is not exists" % path

@app.route('/unlink', methods=['POST'])
@auth.login_required
def unlink():
    response = {}
    try:
        url = request.json.get('download_url')
        filepath = url.replace("%sdownloads" % request.url_root, BASE_PATH)
        os.remove(filepath)
        logger.info("\"%s\" was deleted by [%s]" % (filepath,
                                                    request.remote_addr))
        response['code'] = 1
    except Exception as err:
        logger.error("\"%s\" form [%s]" % (str(err),
                                           request.remote_addr))
        response['code'], response['info'] = -1, {'error': str(err)}
    return json.dumps(response, ensure_ascii=False)

@app.route('/upload', methods=['POST'])
def upload():
    response = {}
    try:
        dirpath = os.path.join(BASE_PATH, datetime.now().strftime('%Y%m%d'))
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)

        # python 接收http提交post的文件
        '''file = request.files.get('file')
        处理多个文件
        files = request.files.getlist('file')
        for file in files:
            # file.save(os.path.join(dirpath, secure_filename(file.filename)))'''

        # 处理nginx upload_module模块转发的post内容,!!!注意:上传文件报文里'name'必须为'file'
        upload_params = request.values
        filename = upload_params.get('file.name')
        temppath = upload_params.get('file.path')
        tempname = temppath[temppath.rfind("/") + 1 :]
        move(temppath, dirpath)
        os.rename("%s/%s" % (dirpath, tempname), "%s/%s" % (dirpath, filename))
        logger.info("\"%s\" was saved by [%s]" % (filename,
                                                  request.remote_addr))
        response['code'], response['info'] = 1, {
            'url': "%s%s%s/%s" % (request.url_root, "downloads", dirpath.replace(BASE_PATH, ""), filename),
            # 'path': dirpath,
            'md5': upload_params.get('file.md5'),
            'size': upload_params.get('file.size')
        }
    except Exception as err:
        logger.error("\"%s\" form [%s]" % (str(err),
                                           request.remote_addr))
        response['code'], response['info'] = -1, {'error': str(err)}
    return json.dumps(response, ensure_ascii=False)


if __name__ == '__main__':
    app.run(host='0.0.0.0')