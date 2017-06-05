# promocash_sync
install
-------

$ sudo apt-get install libssl-dev libffi-dev python-pip virtualenv
$ sudo apt-get install xvfb zenity
# update firefox to 53.0
$ sudo apt-get install firefox
$ virtualenv --system-site-packages ~/promocash

add db_login.txt and promologin.txt in ~/promocash with proper credentials

$ . ~/promocash/bin/activate

then

$ pip install protobuf
$ pip install unidecode
$ pip install lxml
$ pip install mysql-connector==2.1.4
$ pip install pyopenssl --upgrade
$ pip install scrapy
$ pip install selenium
$ pip install pyvirtualdisplay


Use:
----
$ . ~/promocash/bin/activate

then goto promocash_sync clone then

*__got article from promocash site based on Laurux article__*  

$ scrapy runspider promocash_sync/spiders/promocash_article.py

*__create a commande on Laurux based on article from promocash site completed commande__*  

Parametre a fournir ===  "4 dernier num de la commande sur le site ex: 1780"
$ scrapy runspider promocash_sync/spiders/promocash_commande_complete.py --nolog -a commande=1780
