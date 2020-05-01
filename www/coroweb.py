#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Nancy Ting'  #-- coroweb.py --

import asyncio, os, inspect, logging, functools

from urllib import parse

from aiohttp import web

from apis import APIError

def get(path):  # 建立 UR L处理函数的装饰器，用来存储 GET 和 URL 路径信息
    '''
    Define decorator @get('/path')
    '''
    def decorator(func):
        @functools.wraps(func)  # 更正函数签名
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET'  # 存储方法信息
        wrapper.__route__ = path  # 存储路径信息,注意这里属性名叫 route
        return wrapper
    return decorator

def post(path):  # 建立 UR L处理函数的装饰器，用来存储 POST 和 URL 路径信息
    '''
    Define decorator @post('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator

# 运用inspect模块，创建几个函数用以获取URL处理函数与request参数之间的关系
def get_required_kw_args(fn):  # 获取没有默认值的仅限关键字参数 (*args, d, **kw)
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

def get_named_kw_args(fn):  # 获取仅限关键字参数 (*args, d, e=3, **kw)
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

def has_named_kw_args(fn):  # 判断有无仅限关键字参数 (*args, d, e=3, **kw)
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

def has_var_kw_arg(fn):  # 判断有无关键字参数 (**kw)
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def has_request_arg(fn):  # 判断有无名为 'request' 参数，且该参数是否为最后一个参数
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found

class RequestHandler(object):  # 定义RequestHandler,正式向request参数获取URL处理函数所需的参数

    def __init__(self, app, fn):  # 接受 app 参数和函数例如 handler_url_blog
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)  # 是否有 request 参数
        self._has_var_kw_arg = has_var_kw_arg(fn)  # 是否有关键字参数(**kw)
        self._has_named_kw_args = has_named_kw_args(fn)  # 是否有仅限关键字参数(*args, d, e=3, **kw)
        self._named_kw_args = get_named_kw_args(fn)  # 获取所有仅限关键字参数(*args, d, e=3, **kw)
        self._required_kw_args = get_required_kw_args(fn)  # 获取所有没有默认值的仅限关键字参数(*args, d, **kw)

    async def __call__(self, request):
        kw = None
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:  # 如果有关键字参数(**kw)或仅限关键字参数(*args, d, e=3, **kw)或没有默认值的仅限关键词参数(*args, d, **kw)
            if request.method == 'POST':
                if not request.content_type:  # 查询有没提交数据的格式（EncType）
                    return web.HTTPBadRequest(text='Missing Content-Type.')  # 这里被廖大坑了，要有text
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = await request.json()  # 读取 requst body 并解码为 json
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():  # 解析 query_string 为字符串变量，数据作为字典返回，字典的键是唯一的查询变量名，而值是每个变量名的值列表。
                        kw[k] = v[0]
        if kw is None:  # 如果没有在 GET 或 POST 取得参数，直接把 match_info 的所有参数提取到kw
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:  # 如果没有关键字参数(**kw)且有仅限关键字参数(*args, d, e=3, **kw)
                # remove all unamed kw:  # 把所有仅限关键字参数(*args, d, e=3, **kw)提取出来，忽略所有关键字参数(**kw)
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # check named arg:
            for k, v in request.match_info.items():  # 把 match_info 的参数提取到 kw，检查 URL 参数和 HTTP 方法得到的参数是否有重合
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self._has_request_arg:
            kw['request'] = request
        # check required kw:
        if self._required_kw_args:  # 假如命名关键字参数(没有附加默认值)，request没有提供相应的数值，报错
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

def add_static(app):  # 添加静态文件夹的路径
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))

def add_route(app, fn):  # 编写一个 add_route 函数，用来注册一个 URL 处理函数
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):  # 判断是否为协程且生成器,
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))

def add_routes(app, module_name):  # 直接导入文件，批量注册一个 URL 处理函数
    n = module_name.rfind('.')
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)  # 获取函数，例如 handler_url_blog
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:  # 这里要查询 path以及 method 是否存在而不是等待 add_route 函数查询，因为那里错误就要报错了
                add_route(app, fn) 