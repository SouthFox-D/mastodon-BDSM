长毛象嘟文备份及管理工具

Mastodon Backup Data & Sqlite Management Tool

简称  Mastodon BDSM Tool 。

## 安装
用到了以下包

`pip install mastodon.py flask flask-sqlalchemy python-dotenv` ，理论上 Python 3.6+ 版本都可使用。


## 运行
安装完前置包后，在根目录下打开控制台：

- `flask initdb` 初始化数据库

- `flask --debug run` 运行，浏览器打开 `http://127.0.0.1:5000/settings` 进入设置页面，输入帐号后根据提示打开授权链接授权本应用，其实现在真正起作用的是域名，现在实际操作的是授权所用的帐号，设置里的前半段帐号理论来说可以乱填（

- 之后进入 `http://127.0.0.1:5000/archive` 抓取所授权帐号的全部嘟文，现在没做网页端进度条，所以请查看控制台获取进度

- 完成后前往主页即可浏览备份了

## 参见

[mastodon-backup](https://github.com/kensanata/mastodon-backup)

[mastodon-data-viewer.py](https://github.com/blackle/mastodon-data-viewer.py)

[Flask 入门教程](https://tutorial.helloflask.com/)
