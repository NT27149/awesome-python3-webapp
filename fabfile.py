#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Nancy Ting'  #-- fabfile.py --

'''
Deployment toolkit in windows envirement.
'''

import os, re, tarfile

from datetime import datetime
from fabric.api import *

env.user = 'user'  # 改成你服务器的用户名
env.sudo_user = 'user'
# env.hosts = ['123.123.123.123']
env.host_string = '123.123.123.123'  # 改成你的服务器ip
env.password = 'password'  # 服务器密码，可不输入密码，直接部署

db_user = 'www-data'
db_password = 'www-data'

_TAR_FILE = 'dist-awesome.tar.gz'

_REMOTE_TMP_TAR = '/tmp/%s' % _TAR_FILE

_REMOTE_BASE_DIR = '/srv/awesome'

################################################################################

def __ready1__():
    with cd('/root'):
        sudo('apt-get install gcc')
        sudo('sudo apt-get install zlib1g-dev libbz2-dev libssl-dev libncurses5-dev libsqlite3-dev libreadline-dev tk-dev libgdbm-dev libdb-dev libpcap-dev xz-utils libexpat1-dev liblzma-dev libffi-dev libc6-dev')
        sudo('wget https://www.python.org/ftp/python/3.7.3/Python-3.7.3.tgz')
        sudo('sudo tar -zxvf Python-3.7.3.tgz')

    with cd('/root/Python-3.7.3'): 
        sudo('pwd')  # pwd = print working directory
        sudo('./configure --prefix=/opt/python3.7')  # configure 配置，prefix 安装路径
        sudo('make')  # make 编译
        sudo('make install')  # make install 安装
        sudo('sudo ln -s /opt/python3.7/bin/python3.7 /usr/bin/python3.7')  # link soft 创建软链接
        sudo('python3.7 -V')

    with cd('/root'):
        sudo('apt-get install unzip')
        sudo('wget https://files.pythonhosted.org/packages/b5/96/af1686ea8c1e503f4a81223d4a3410e7587fd52df03083de24161d0df7d4/setuptools-46.1.3.zip')
        sudo('sudo unzip setuptools-46.1.3.zip')
    with cd('setuptools-46.1.3'):
        sudo('sudo python3.7 setup.py build')
        sudo('sudo python3.7 setup.py install')

    with cd('/root'): 
        sudo('wget https://files.pythonhosted.org/packages/8e/76/66066b7bc71817238924c7e4b448abdb17eb0c92d645769c223f9ace478f/pip-20.0.2.tar.gz')
        sudo('sudo tar -zxvf pip-20.0.2.tar.gz')
    with cd('pip-20.0.2'):
        sudo('sudo python3.7 setup.py build')
        sudo('sudo python3.7 setup.py install')
        sudo('sudo ln -s /opt/python3.7/bin/pip3 /usr/bin/pip3')
        sudo('pip3 -V')

# ------------------------------------------------------------------------------

    sudo('sudo apt-get install openssh-server')

    with cd('/srv'):
        sudo('mkdir awesome')

    with cd('/srv/awesome'):
        sudo('mkdir log')

    sudo('apt-get install dos2unix')

    sudo('sudo apt-get install nginx supervisor python3 mysql-server')

    sudo('sudo pip3 install jinja2 aiomysql aiohttp')

    put('www/schema.sql', '/root')
    with cd('/root'):
        sudo('mysql -u root -p < schema.sql')  # u = user，p = password

################################################################################

def _current_path():
    return os.path.abspath('.')

def _now():
    return datetime.now().strftime('%y-%m-%d_%H.%M.%S')

def build():
    # includes = ['static', 'templates', 'transwarp', 'favicon.ico', '*.py']
    # excludes = ['test', '.*', '*.pyc', '*.pyo']
    local('del dist\\%s' % _TAR_FILE)  # windows 删除 dist\dist-awesome.tar.gz 旧压缩包 (local 执行本地 windows 命令)，del = delete
    tar = tarfile.open("dist/%s" % _TAR_FILE, "w:gz")  # windows 新建 dist\dist-awesome.tar.gz 新压缩包,'w:gz' 以 gzip 的方式压缩并写入
    for root, _dir, files in os.walk("www/"):  # 打包 www 文件夹  根目录、文件夹、文件
        for f in files:
            if not (('.pyc' in f) or ('.pyo' in f)):  # 排除开发过程调试产生的文件
                fullpath = os.path.join(root, f)
                tar.add(fullpath)  # 压缩包添加文件
    tar.close()

def deploy():
    newdir = 'www-%s' % _now()  # 获取形如 www-20-04-24_10.33.48 的文件名
    run('rm -f %s' % _REMOTE_TMP_TAR)  # 删除 /tmp/dist-awesome.tar.gz (run 执行服务器 ubuntu 命令)，rm = remove，f = force, rm -rf 即强制删除
    put('dist/%s' % _TAR_FILE, _REMOTE_TMP_TAR)  # 将 windows 的 dist\dist-awesome.tar.gz 推送到 ubuntu 的 /tmp/dist-awesome.tar.gz (put 上传本地 windows 中的文件到远程的 ubuntu 主机)
    with cd(_REMOTE_BASE_DIR):  # 切换目录到 /srv/awesome (cd 是 ubuntu 中切换到指定目录)
        sudo('mkdir %s' % newdir)  # 创建新目录 www-20-04-24_10.33.48 (sudo 在 ubuntu 中执行需要 sudo 权限的命令)，mkdir = make directory
    with cd('%s/%s' % (_REMOTE_BASE_DIR, newdir)):  # 切换目录到 /srv/awesome/www-20-04-24_10.33.48
        sudo('tar -xzvf %s' % _REMOTE_TMP_TAR)  # 解压 tar -xzvf /tmp/dist-awesome.tar.gz，
        sudo('mv www/* .')  # 解压后多一层www文件夹，将 /srv/awesome/www-20-04-24_10.33.48/www 中的所有内容移动到 /srv/awesome/www-20-04-24_10.33.48
        sudo('rm -rf www')  # 删除空文件夹 /srv/awesome/www
        sudo('dos2unix app.py')  # 解决 windows 和 linux 行尾换行不同问题
        sudo('chmod a+x app.py')  # 使 app.py 可直接执行，给所有的用户添加执行，chmod = change mode，a = all 是指所有的用户组，+x x = executable 是指添加执行权限。
    with cd(_REMOTE_BASE_DIR):  # 切换目录到 /srv/awesome
        sudo('rm -f www')  # 删除旧软链接 www > www-20-04-23_09.01.11
        sudo('ln -s %s www' % newdir)  # 创建新链接   www > www-20-04-24_10.33.48，ln = link，s = soft
        sudo('chown root:root www')  # user 改为你的 linux 服务器上的用户名
        sudo('chown -R root:root %s' % newdir)  # chown = change owner 修改文件目录属主，-R 处理指定目录以及其子目录下的所有文件
    with settings(warn_only=True):  # 临时修改 env 变量来修改指定设置
        sudo('supervisorctl restart awesome')  # supervisor 重启 app
        sudo('/etc/init.d/nginx reload')  # nginx重启

RE_FILES = re.compile('\r?\n')

def rollback():
    '''
    rollback to previous version
    '''
    with cd(_REMOTE_BASE_DIR):  # 切换目录到 /srv/awesome
        r = run('ls')  # 列出 /srv/awesome 内所有目录，ls = list
        files = [s[:-1] for s in RE_FILES.split(r) if s.startswith('www-') and s.endswith('/')]
        files.sort(reverse=True)  # 对所有文件夹名进行排序
        r = run('ls -l www')  # 列出 /srv/awesome/www 的软链接指向，除文件名称外，亦将文件型态、权限、拥有者、文件大小等资讯详细列出
        ss = r.split(' -> ')  # lrwxrwxrwx 1 root root 21 4月  24 12:08 www -> www-20-04-24_12.08.05
        if len(ss) != 2:
            print('ERROR: \'www\' is not a symbol link.')
            return
        current = ss[1]  # www-20-04-24_12.08.05
        print('Found current symbol link points to: %s\n' % current)
        try:
            index = files.index(current)  # 找到 current 文件的索引
        except ValueError as e: 
            print('ERROR: symbol link is invalid.')
            return
        if len(files) == index + 1:
            print('ERROR: already the oldest version.')
        old = files[index + 1]
        print('==================================================')
        for f in files:
            if f == current:
                print('      Current ---> %s' % current)
            elif f == old:
                print('  Rollback to ---> %s' % old)
            else:
                print('                   %s' % f)
        print('==================================================')
        print('')
        yn = input ('continue? y/N ')
        if yn != 'y' and yn != 'Y':
            print('Rollback cancelled.')
            return
        print('Start rollback...')
        sudo('rm -f www')
        sudo('ln -s %s www' % old)
        sudo('chown www-data:www-data www')
        with settings(warn_only=True):
            sudo('supervisorctl restart awesome')
            sudo('/etc/init.d/nginx reload')
        print('ROLLBACKED OK.')

def backup():
    '''
    Dump entire database on server and backup to local.
    '''
    dt = _now()
    f = 'backup-awesome-%s.sql' % dt
    with cd('/tmp'):
        run('mysqldump --user=%s --password=%s --skip-opt --add-drop-table --default-character-set=utf8 --quick awesome > %s' % (db_user, db_password, f))  # 创建文件 backup-awesome-20-04-24_12.08.05.sql
        run('tar -czvf %s.tar.gz %s' % (f, f))  # 将 backup-awesome-20-04-24_12.08.05.sql 文件打包为 backup-awesome-20-04-24_12.08.05.tar.gz
        get('%s.tar.gz' % f, '%s/backup/' % _current_path())  # 将 ubuntu 的 backup-awesome-20-04-24_12.08.05.tar.gz 文件下载到 windows 的文件夹 awesome-python3-webapp\backup (从远程 ubuntu 主机下载文件到本地 windows)
        run('rm -f %s' % f)  # 删除 backup-awesome-20-04-24_12.08.05.sql
        run('rm -f %s.tar.gz' % f)  # 删除 backup-awesome-20-04-24_12.08.05.tar.gz

def extract(tar_path, target_path):
    '''
    解压tar.gz文件到目标目录
    '''
    try:
        tar = tarfile.open(tar_path, "r:gz")  # windows 中采用gzip格式解压并打开文件(r:gz) awesome-python3-webapp\backup\backup-awesome-20-04-24_12.54.14.sql.tar.gz
        file_names = tar.getnames()  # windows 中获取文件名，以列表的形式显示 ['backup-awesome-20-04-24_12.54.14.sql']
        for file_name in file_names:
            tar.extract(file_name, target_path)  # 将文件解压到目标文件夹 awesome-python3-webapp\backup
        tar.close()
    except Exception as e:
        raise e
# extract(r'backup\backup-awesome-20-04-24_12.54.14.sql.tar.gz', 'backup')

def restore2local():
    '''
    Restore db to local
    '''
    backup_dir = os.path.join(_current_path(), 'backup')
    fs = os.listdir(backup_dir)
    files = [f for f in fs if f.startswith('backup-') and f.endswith('.sql.tar.gz')]  # 获取备份文件列表
    files.sort(reverse = True)  # 最近的文件排在前面
    if len(files)==0:
        print('No backup files found.')
        return
    print('Found %s backup files:' % len(files))
    print('==================================================')
    n = 0
    for f in files:
        print('%s: %s' % (n, f))
        n = n + 1
    print('==================================================')
    print('')
    try:
        num = int(input ('Restore file: '))  # 选择恢复哪个备份
    except ValueError:
        print('Invalid file number.')
        return
    restore_file = files[num]
    yn = input('Restore file %s: %s? y/N ' % (num, restore_file))  # 确定开始恢复
    if yn != 'y' and yn != 'Y':
        print('Restore cancelled.')
        return
    print('Start restore to local database...')
    p = input('Input mysql root password: ')
    sqls = [
        'drop database if exists awesome;',
        'create database awesome;', 
        'alter database awesome default character set utf8 collate utf8_general_ci;',  # 修改为utf8字符集
        'grant select, insert, update, delete on awesome.* to \'%s\'@\'localhost\';' % (db_user)  # 原 'grant select, insert, update, delete on awesome.* to \'%s\'@\'localhost\' identified by \'%s\';' % (db_user, db_password)
    ]
    for sql in sqls:
        local(r'mysql -uroot -p%s -e "%s"' % (p, sql))  # 删除旧数据库，新建数据库，授权给用户
    extract('backup\\%s' % restore_file, 'backup\\')  # 解压
    with lcd('backup'):
        # linux系统和windows系统之间数据库导入导出，可能因为字符集不同出现'unknown command \\'错误
        # 通过在创建数据库后修改为utf8字符集，以及导入时指定--default-character-set=utf8，解决这个问题
        local(r'mysql -uroot -p%s --default-character-set=utf8 awesome < %s' % (p, restore_file[:-7])) # 导入数据库
        local('del %s' % restore_file[:-7]) # 删除解压出的文件

################################################################################

def __ready2__():
    put('conf/supervisor/awesome.conf', '/etc/supervisor/conf.d/')
    sudo('sudo supervisorctl reload')
    sudo('sudo supervisorctl start awesome')
    sudo('sudo supervisorctl status')

    put('conf/nginx/awesome', '/etc/nginx/sites-available/')
    with cd('/etc/nginx/sites-enabled/'):
        sudo('sudo ln -s /etc/nginx/sites-available/awesome .')
        sudo('sudo /etc/init.d/nginx reload')

################################################################################

if __name__ == '__main__':
    __ready1__()
    build()
    deploy()
    # rollback()
    # backup()
    # restore2local()
    # input()
    __ready2__()