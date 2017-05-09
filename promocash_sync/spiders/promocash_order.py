# -*- coding: utf-8 -*-
import scrapy
import time
import datetime
import sys
import os
from unidecode import unidecode
from scrapy.http import FormRequest
from scrapy.http import Request
from scrapy.selector import Selector
from scrapy.http import HtmlResponse
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.utils.response import open_in_browser
from scrapy.loader import ItemLoader
from scrapy.loader.processors import Join, MapCompose, TakeFirst
from w3lib.html import remove_tags
import re
import mysql.connector
from scrapy import signals


with open(os.environ['HOME'] + '/promocash/promologin.txt') as f:
  credentials = [x.strip().split(':') for x in f.readlines()]
  
for username,password in credentials:
	promo_user = username
	promo_pass = password

with open(os.environ['HOME'] + '/promocash/dblogin.txt') as f:
  credentials = [x.strip().split(':') for x in f.readlines()]
  
for username,password in credentials:
	db_user = username
	db_pass = password

try:
	conn = mysql.connector.connect(host="localhost",user=db_user,password=db_pass, database="Promocash")
	conn_Laurux = mysql.connector.connect(host="localhost",user=db_user,password=db_pass, database="Laurux01")
	cursor = conn.cursor()
	cursor_Laurux = conn_Laurux.cursor(named_tuple=True)
	
except mysql.connector.Error as err:
	if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
		print "Something is wrong with your user name or password"
	elif err.errno == errorcode.ER_BAD_DB_ERROR:
		print "Database does not exist"
	else:
		print err

cursor.execute("""
CREATE TABLE IF NOT EXISTS Articles (
	cbarre varchar(20) NOT NULL,
	code varchar(10) NOT NULL,
	name varchar(100) DEFAULT NULL,
	prixht varchar(8) DEFAULT NULL,
	prixht_promo varchar(8) DEFAULT NULL,
	prixht_promo_act varchar(8) DEFAULT NULL,
	prixht_unite varchar(8) DEFAULT NULL,
	prixht_cond varchar(8) DEFAULT NULL,
	taxe_css varchar(8) DEFAULT NULL,
	tva varchar(5) DEFAULT NULL,
	marque varchar(20) DEFAULT NULL,
	unite_achat varchar(5) DEFAULT NULL,
	cond varchar(5) DEFAULT NULL,
	image varchar(200) DEFAULT NULL,
	last_update varchar(20) DEFAULT NULL,
	PRIMARY KEY(cbarre)
);
""")

cursor_Laurux.execute("""SELECT * FROM Laurux01.Fiches_Art where
			art_four = 401002 and art_code = art_cbarre and art_stocke = 1 and art_suspendu = 0;
			""")

cbarre_notfound = []

#change to True for testing
if (True):
	cbarre_list = ["3560070756100","5410228230441"]
else:
	cbarre_list = []
	for row in cursor_Laurux:
		cbarre_list.append(row.art_code)

print "*********************"
print cbarre_list
print "*********************"
print len(cbarre_list)
print "*********************"
#sys.exit(0)

def filter_float(value):
	value = re.sub(',','.',value)
	try:
		f = float(value)
		return f
	except ValueError:
		return False
		
def strip_tva(value):
	return re.sub('%','',value)
	
def strip_string(value):
	#print "VALUE1=" + value
	#print "VALUE2=" + re.sub('\s+',' ',value).strip()
	return re.sub('\s+',' ',value).strip()

def strip_non_numeric(value):
	non_decimal = re.compile(r'[^\d.,]+')
	return non_decimal.sub('', value)

def is_css(value):
	if "securite sociale" in value:
		return value
	else:
		return None

def unicode_to_ascii(value):
	return unidecode(value)

def check_unite_achat(value):
	if "Vendu par" in value:
		return value
	else:
		return "1"

def show_field(value):
	print "Field: " + value
	return value

class Article(scrapy.Item):
	
	def show(self):
		print "***********************"
		print dict(self)
		print "***********************"
	
	def insert(self):
		elem=dict(self)
		if (not ('taxe_css' in elem)):
			 elem['taxe_css'] = "0"
		if (not ('cond' in elem)):
			 elem['cond'] = "1"
		if (not ('unite_achat' in elem)):
			 elem['unite_achat'] = "1"
		if (not ('marque' in elem)):
			 elem['marque'] = ""
		if (not ('prixht' in elem)):
			 elem['prixht'] = elem['prixht_promo']
		else:
			if (not ('prixht_promo' in elem)):
				elem['prixht_promo'] = elem['prixht']
			if (not ('prixht_promo_act' in elem)):
				elem['prixht_promo_act'] = elem['prixht']
		if (not ('image' in elem)):
			elem['image'] = ""
		if (('prixht_cond' in elem) and (float(elem['cond']) != "{:.3f}".format(float(elem['prixht']) / float(elem['prixht_cond'])))):
			elem['cond'] = "{:.3f}".format(float(elem['prixht']) / float(elem['prixht_cond']))
		if (not ('prixht_unite' in elem)):
			elem['prixht_unite'] = "{:.2f}".format(float(elem['prixht']) / float(elem['unite_achat']))
		today = datetime.datetime.today()
		elem['last_update'] = today.strftime("%Y-%m-%d %H:%M:%S")
		cursor.execute("""INSERT INTO Articles (cbarre, code, name, prixht, prixht_promo, prixht_promo_act, prixht_unite, prixht_cond, taxe_css, tva, marque, unite_achat, cond, image, last_update) 
			VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
			code = VALUES(code),
			name = VALUES(name),
			prixht = VALUES(prixht),
			prixht_promo = VALUES(prixht_promo),
			prixht_promo_act = VALUES(prixht_promo_act),
			prixht_unite = VALUES(prixht_unite),
			prixht_cond = VALUES(prixht_cond),
			taxe_css = VALUES(taxe_css),
			tva = VALUES(tva),
			marque = VALUES(marque),
			unite_achat = VALUES(unite_achat),
			cond = VALUES(cond),
			marque = VALUES(marque),
			image = VALUES(image),
			last_update = VALUES(last_update) ;
			""",(elem['cbarre'], elem['code'], elem['name'], elem['prixht'],
			elem['prixht_promo'], elem['prixht_promo_act'], elem['prixht_unite'], elem['prixht_cond'],
			elem['taxe_css'], elem['tva'], elem['marque'], elem['unite_achat'], elem['cond'],
			elem['image'], elem['last_update']))
		conn.commit()

class PromocashArticleSpider(CrawlSpider):
	name = 'promocash_article'
	allowed_domains = ['grenoble.promocash.com']
	start_urls = ['https://grenoble.promocash.com/authentification.php']

	rules = (
	    Rule(LinkExtractor(allow=('https://grenoble.promocash.com/authentification.php')), callback='parse_start_url', follow=False),
	    Rule(LinkExtractor(allow=('produitListe.php')), callback='parse_item', follow=True),
	)
	
	@classmethod
	def from_crawler(cls, crawler, *args, **kwargs):
		spider = super(PromocashArticleSpider, cls).from_crawler(crawler, *args, **kwargs)
		crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
		return spider
	
	def parse_start_url(self, response):
		self.logger.warning("Starting Connection with User : " + promo_user)
		request = scrapy.FormRequest.from_response(response,formnumber=1,
			formdata={'CLI_NUMERO': promo_user,'CLI_PASSWORD': promo_pass},
			clickdata={'name':'logClient'},
			callback=self.after_login)
		request.meta['dont_redirect'] = True
		yield request
	
	#def after_user(self, response):
	#	time.sleep(1)
	#	open_in_browser(response)
	#	self.logger.warning("Enter Password " + promo_user)
	#	req = FormRequest.from_response(response,formnumber=1,
	#		formdata={'CLI_NUMERO': promo_user,'CLI_PASSWORD': promo_pass},
	#		clickdata={'name':'logClient'},
	#		callback=self.after_login)
	#	puts req
	#	yield req
	
	def after_login(self, response):
		self.logger.warning("Check logging")
		time.sleep(0.2)
		#open_in_browser(response)
		if "Merci de vérifier notre numéro de carte" in response.body:
			self.logger.warning("logging Failed")
			return
		else:
			self.logger.warning("logging Successfull")
			return Request(url="https://grenoble.promocash.com/",
				callback=self.start_page)
	
	def start_page(self, response):
		time.sleep(1)
		self.logger.warning("Start Page")
		for cbarre in cbarre_list:
			request = scrapy.FormRequest.from_response(response,
				formdata={'searchString': cbarre},
				callback=self.parse_item)
			request.meta['cbarre'] = cbarre
			yield request
	
	def parse_item(self, response):
		self.logger.warning("Parse Item " + response.meta['cbarre'])
		time.sleep(0.5)
		open_in_browser(response)
		#request = scrapy.FormRequest.from_response(response,
		#		formxpath=
		#		formdata={'searchString': cbarre},
		#		callback=self.parse_item)
		#request.meta['cbarre'] = response.meta['cbarre']
		#return request
		
	def order_article(self, response):
		time.sleep(0.5)
		open_in_browser(response)
		
	def spider_closed(self, spider):
		self.logger.info('Promocash spider closed: %s', spider.name)
		print "////// NOT FOUND //////"
		print cbarre_notfound
		print "///////////////////////"
		try:
			cursor.close()
			conn.close()
			cursor_Laurux.close()
			conn_Laurux.close()
		except:
			print "failure during close connection"



