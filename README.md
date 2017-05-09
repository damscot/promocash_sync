# promocash_sync
install
-------

$ sudo apt-get install libssl-dev libffi-dev python-pip virtualenv
$ virtualenv --system-site-packages ~/promocash

add db_login.txt and promologin.txt in ~/promocash with proper credentials

$ . ~/promocash/bin/activate

then

$ pip install protobuf
$ pip install unidecode
$ pip install mysql-connector==2.1.4
$ pip install pyopenssl --upgrade
$ pip install scrapy


Use:
----
$ . ~/promocash/bin/activate

then goto promocash_sync clone then

*__got article from promocash site based on Laurux article__*  

$ scrapy runspider promocash_sync/spiders/promocash_article.py


