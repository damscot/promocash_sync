# -*- coding: utf-8 -*-
import scrapy
import time
import datetime
import sys
from unidecode import unidecode
from scrapy.http import FormRequest
from scrapy.http import Request
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.utils.response import open_in_browser
from scrapy.linkextractors.sgml import SgmlLinkExtractor
from scrapy.loader import ItemLoader
from scrapy.loader.processors import Join, MapCompose, TakeFirst
from w3lib.html import remove_tags
import re
import mysql.connector
from scrapy import signals


with open('/home/jeanne/promocash/promologin.txt') as f:
  credentials = [x.strip().split(':') for x in f.readlines()]
  
for username,password in credentials:
	promo_user = username
	promo_pass = password

with open('/home/jeanne/promocash/dblogin.txt') as f:
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
cbarre_list = []
for row in cursor_Laurux:
	cbarre_list.append(row.art_code)

print "*********************"
print cbarre_list
print "*********************"
print len(cbarre_list)
print "*********************"
#sys.exit(0)

def filter_price(value):
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
	non_decimal = re.compile(r'[^\d.]+')
	return non_decimal.sub('', value)

def is_css(value):
	if "securite sociale" in value:
		return value
	else:
		return None

def unicode_to_ascii(value):
	return unidecode(value)

class Article(scrapy.Item):
	cbarre = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric),
		output_processor=TakeFirst(),
	)
	code = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric),
		output_processor=TakeFirst(),
	)
	name = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii),
		output_processor=TakeFirst(),
	)
	prixht = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric),
		output_processor=Join(''),
	)
	prixht_promo = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric),
		output_processor=Join(''),
	)
	prixht_promo_act = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric),
		output_processor=Join(''),
	)
	prixht_cond = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric, filter_price),
		output_processor=TakeFirst(),
	)
	taxe_css = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, is_css, strip_non_numeric, filter_price),
		output_processor=TakeFirst(),
	)
	tva = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric ,strip_tva),
		output_processor=TakeFirst(),
	)
	marque = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii),
		output_processor=TakeFirst(),
	)
	cond = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric),
		output_processor=TakeFirst(),
	)
	image = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string),
		output_processor=TakeFirst(),
	)
	last_updated = scrapy.Field(serializer=str)
	
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
		if (not ('prixht_unite' in elem)):
			 elem['prixht_unite'] = "{:.2f}".format(float(elem['prixht']) / float(elem['cond']))
		today = datetime.datetime.today()
		elem['last_update'] = today.strftime("%Y-%m-%d %H:%M:%S")
		cursor.execute("""INSERT INTO Articles (cbarre, code, name, prixht, prixht_promo, prixht_promo_act, prixht_unite, prixht_cond, taxe_css, tva, marque, cond, image, last_update) 
			VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
			cond = VALUES(cond),
			marque = VALUES(marque),
			image = VALUES(image),
			last_update = VALUES(last_update) ;
			""",(elem['cbarre'], elem['code'], elem['name'], elem['prixht'],
			elem['prixht_promo'], elem['prixht_promo_act'], elem['prixht_unite'], elem['prixht_cond'],
			elem['taxe_css'], elem['tva'], elem['marque'], elem['cond'],
			elem['image'], elem['last_update']))
		conn.commit()

class PromocashArticleSpider(CrawlSpider):
	name = 'promocash_article'
	allowed_domains = ['grenoble.promocash.com']
	start_urls = ['https://grenoble.promocash.com/authentification.php?popup=1']

	rules = (
		Rule(SgmlLinkExtractor(allow=('authentification')), callback='parse_start_url', follow=True),
		Rule(SgmlLinkExtractor(allow=('\\?page=\\d')), callback='parse_item', follow=True),
	)
	
	@classmethod
	def from_crawler(cls, crawler, *args, **kwargs):
		spider = super(PromocashArticleSpider, cls).from_crawler(crawler, *args, **kwargs)
		crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
		return spider
	
	def parse_start_url(self, response):
		return [FormRequest.from_response(response,
			formdata={'CLI_NUMERO': promo_user},
			dont_click=True,
			callback=self.after_user)]
	
	def after_user(self, response):
		time.sleep(0.2)
		return [FormRequest.from_response(response,
			formdata={'CLI_NUMERO': promo_user,'CLI_PASSWORD': promo_pass},
			callback=self.after_login)]
	
	def after_login(self, response):
		time.sleep(0.2)
		if "Merci de vérifier notre numéro de carte" in response.body:
			self.logger.warning("logging Failed")
			return
		else:
			self.logger.warning("logging Successfull")
			return Request(url="https://grenoble.promocash.com/",
				callback=self.start_page)
	
	def start_page(self, response):
		self.logger.warning("Start Page")
		for cbarre in cbarre_list:
			request = scrapy.FormRequest.from_response(response,
				formdata={'searchString': cbarre},
				callback=self.parse_item)
			request.meta['cbarre'] = cbarre
			yield request
	
	def parse_item(self, response):
		#open_in_browser(response)
		try:
			url_detail = response.xpath('//p[@class="pdt-libelle"]/a/@href').extract()
			url_detail = u'https://grenoble.promocash.com/' + url_detail[0]
		except:
			cbarre_notfound.append(response.meta['cbarre'])
			return None
		#print url_detail
		request = scrapy.Request(url_detail, callback=self.parse_detail)
		request.meta['cbarre'] = response.meta['cbarre']
		return request
		
	def parse_detail(self, response):
		#open_in_browser(response)
		time.sleep(1)
		l = ItemLoader(item=Article(), response=response)
		l.add_value('cbarre', response.meta['cbarre'])
		l.add_xpath('code','//p[@class="pdt-ifls"]/text()')
		l.add_xpath('name','//div[@class="grp-titre"]/h2/text()')
		l.add_xpath('cond','//p[@class="pdt-cond"]/text()')
		l.add_xpath('marque','//p[@class="pdt-mar"]/text()')
		l.add_xpath('prixht','//p[@class="prix"]/span/span[@*]/text()')
		l.add_xpath('prixht_promo','//div[@class="blocPrix"]/del/text()')
		l.add_xpath('prixht_promo_act','//div[@class="blocPrix"]/ins/span/span[@*]/text()')
		l.add_xpath('prixht_cond','//p[@class="pdt-pxUnit"]/text()')
		l.add_xpath('taxe_css','//div[@class="grp-info"]/p[3]/text()')
		l.add_xpath('tva','//div[@class="tva"]/span/text()')
		l.add_xpath('image','//div[@class="imgContainer"]/a/@href')
		l.load_item()
		l.item.insert()
		l.item.show()
		
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



