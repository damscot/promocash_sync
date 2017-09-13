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

def filter_float_str(value):
	value = re.sub(',','.',value)
	try:
		f = float(value)
		return str(f)
	except ValueError:
		return ""
		
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
	name = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii),
		output_processor=TakeFirst(),
	)
	code = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric),
		output_processor=TakeFirst(),
	)
	qte = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric),
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
	prixht_cond = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric, filter_float_str),
		output_processor=Join(''),
	)
	prixht_cond_promo = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, strip_non_numeric, filter_float_str),
		output_processor=Join(''),
	)
	unite_achat = scrapy.Field(
		input_processor=MapCompose(remove_tags, strip_string, unicode_to_ascii, check_unite_achat, strip_non_numeric, filter_float_str),
		output_processor=TakeFirst(),
	)
		
	def show(self):
		print "***********************"
		print dict(self)
		print "***********************"
	
	def insert(self, spider):
		elem=dict(self)

		if (not ('unite_achat' in elem)):
			elem['unite_achat'] = "1"

		art = None
		spider.cursor_Laurux.execute("""SELECT * FROM Fiches_Art where art_four = %s and art_cfour = %s ;""", ('401002', elem['code'],))
		#only one match supported
		for row in spider.cursor_Laurux:
			art = row
		if (art == None):
			print "!!!! Unable to find %s: %s (qte: %s ; ua: %s)" % (elem['code'], elem['name'], elem['qte'], elem['unite_achat'])
			spider.article_notfound.append(elem['code'])
			if (float(elem['qte']) != 0.0):
				spider.montant_notfound = spider.montant_notfound + float(re.sub(',','.',str(elem['prixht'])))
			return
		elif (float(elem['qte']) == 0.0):
			print "!!!! Quantity null for %s(%s): %s" % (art.art_code, elem['code'],  elem['name'])
			spider.article_withnullqte.append(elem['code'])
			return
		else:
			spider.article_found.append(elem['code'])
			if (not ('prixht' in elem)):
				 elem['prixht'] = float(re.sub(',','.',elem['prixht_promo']))
				 elem['prixht_cond'] =  float(re.sub(',','.',elem['prixht_cond_promo']))
			 	
			print "**** Quantity %s (ua:%s) for %s(%s): %s" % (elem['qte'], elem['unite_achat'], art.art_code, elem['code'], elem['name'])
			spider.montant_found = spider.montant_found + float(re.sub(',','.',str(elem['prixht'])))
			if (art.art_com != None):
				art_com = art.art_com + (float(elem['qte']) * float(elem['unite_achat']))
			else:
				art_com = (float(elem['qte']) * float(elem['unite_achat']))
				
			spider.cursor_Laurux.execute("""UPDATE Fiches_Art SET art_com = %s where art_four = %s and art_cfour = %s ;""", (art_com, '401002', elem['code']))

		spider.cursor_Laurux.execute("""INSERT INTO Fiches_Ligcom (code, design, numcom, four, qte, pbht, rm, paht, datecom, frais, prvt, nligne, coda) 
			VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
			code = VALUES(code),
			design = VALUES(design),
			numcom = VALUES(numcom),
			four = VALUES(four),
			qte = VALUES(qte),
			pbht = VALUES(pbht),
			rm = VALUES(rm),
			paht = VALUES(paht),
			datecom = VALUES(datecom),
			frais = VALUES(frais),
			prvt = VALUES(prvt),
			nligne = VALUES(nligne),
			coda = VALUES(coda) ;
			""",(art.art_code, art.art_design, spider.laurux_commande, '401002',
			re.sub('\.',',',str((float(elem['qte']) * float(elem['unite_achat'])))),
			re.sub('\.',',',str(elem['prixht_cond'])), 0, re.sub('\.',',',str(elem['prixht_cond'])),
			spider.ddate, re.sub('\.',',',str(art.art_frais)), re.sub('\.',',',str(art.art_prvt)), str(int(spider.nligne)).zfill(4), art.art_code))
		spider.conn_Laurux.commit()
		spider.nligne = spider.nligne + 1;

class PromocashCmdCompleteSpider(CrawlSpider):
	name = 'promocash_article'
	allowed_domains = ['grenoble.promocash.com']
	start_urls = ['https://grenoble.promocash.com/authentification.php']

	def __init__(self, commande=None, *args, **kwargs):
		super(PromocashCmdCompleteSpider, self).__init__(*args, **kwargs)
		
		if commande == None :
			print "ERREUR! le numero de la commande doit etre fourni '-a commande=XXXXX"
			sys.exit(-1)
		print "COMMANDE = " + commande
		self.commande = commande
		
		with open(os.environ['HOME'] + '/promocash/promologin.txt') as f:
			credentials = [x.strip().split(':') for x in f.readlines()]
  
		for username,password in credentials:
			self.promo_user = username
			self.promo_pass = password
		
		with open(os.environ['HOME'] + '/promocash/dblogin.txt') as f:
		  credentials = [x.strip().split(':') for x in f.readlines()]
		  
		for host,username,password in credentials:
			db_host = host
			db_user = username
			db_pass = password
		
		try:
			self.conn = mysql.connector.connect(host=db_host,user=db_user,password=db_pass, database="Promocash")
			self.conn_Laurux = mysql.connector.connect(host=db_host,user=db_user,password=db_pass, database="Laurux01")
			self.cursor = self.conn.cursor()
			self.cursor_Laurux = self.conn_Laurux.cursor(named_tuple=True)
			
		except mysql.connector.Error as err:
			if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
				print "Something is wrong with your user name or password"
			elif err.errno == errorcode.ER_BAD_DB_ERROR:
				print "Database does not exist"
			else:
				print err
				
		self.article_notfound = []
		self.article_found = []
		self.article_withnullqte = []
	
	@classmethod
	def from_crawler(cls, crawler, *args, **kwargs):
		spider = super(PromocashCmdCompleteSpider, cls).from_crawler(crawler, *args, **kwargs)
		crawler.signals.connect(spider.spider_opened, signal=signals.spider_opened)
		crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
		return spider
	
	def parse_start_url(self, response):
		self.logger.warning("Starting Connection with User : " + self.promo_user)
		#open_in_browser(response)
		request = scrapy.FormRequest.from_response(response,formnumber=1,
			formdata={'CLI_NUMERO': self.promo_user,'CLI_PASSWORD': self.promo_pass},
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
			return Request(url="https://grenoble.promocash.com/clientMesCommandesDetail.php?idC=" + self.commande,
				callback=self.parse_commande)
	
	def parse_commande(self, response):
		self.logger.warning("Parse Commande " + self.commande)
		time.sleep(2)
		#open_in_browser(response)
		headercom = response.xpath('//div[@class="entetePage"]/p[@class="etat"]/text()').extract()
		if (((len(headercom) == 4) and (unidecode(headercom[3]).strip() == ("Terminee"))) or
			((len(headercom) == 4) and (unidecode(headercom[3]).strip() == ("En cours de livraison")))):
			print "**** Commande " + self.commande + " trouvé."
		else:
			print "!!!! Commande " + self.commande + " NON trouvé."
			return

		self.cursor_Laurux.execute("""SELECT * FROM Fiches_Parametres ;""", ())
		for row in self.cursor_Laurux:
			self.laurux_commande = str(int(row.dncom) + 1).zfill(5) 
		
		date = unidecode(headercom[1]).strip().split('/')
		#today = datetime.datetime.today()
		#self.ddate = today.strftime("%Y-%m-%d %H:%M:%S")
		self.ddate = "20%s-%s-%s 00:00:00" % (date[2],date[1],date[0])
		commentaire = "Genere depuis WWW => commande Promo " + self.commande + " du " + self.ddate
		self.nligne = 0
		self.montant_notfound = 0.0
		self.montant_found = 0.0
		montant = response.xpath('//span[@class="td-montant"]/text()').extract()
		
		self.cursor_Laurux.execute("""INSERT INTO Fiches_Entcom (four, numcom, ddate, montant, reliquat, montantttc, anomalie, commentaire) 
			VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
			four = VALUES(four),
			numcom = VALUES(numcom),
			ddate = VALUES(ddate),
			montant = VALUES(montant),
			reliquat = VALUES(reliquat),
			montantttc = VALUES(montantttc),
			anomalie = VALUES(anomalie),
			commentaire = VALUES(commentaire) ;
			""",('401002', self.laurux_commande, self.ddate, filter_float_str(strip_non_numeric(montant[0].strip())),
			0, re.sub('\.',',',filter_float_str(strip_non_numeric(montant[3].strip()))), 0, commentaire))
		self.conn_Laurux.commit()
		
		divs = response.xpath('//div[@class="table-info"]')
		for div in divs:
			l = ItemLoader(item=Article(), selector=div, response=response)
			l.add_xpath('name','.//div[@class="pdt-libelle"]/a/text()')
			l.add_xpath('code','.//span[@class="pdt-ifls"]/text()')
			l.add_xpath('qte', './/input[@class="inputQuantite"]/@value')
			l.add_xpath('prixht','.//div[@class="prix"]/span/span[@*]/text()')
			l.add_xpath('prixht_promo','.//div[@class="prix promo"]/span/span[@*]/text()')
			l.add_xpath('prixht_cond','.//div[@class="pdt-pxUnit"]/text()')
			l.add_xpath('prixht_cond_promo','.//div[@class="pdt-pxUnit"]/span[@class="rouge"]/text()')
			l.add_xpath('unite_achat','.//div[@class="pdt-cond"]/text()')
			l.load_item()
			l.item.insert(spider=self)
			#l.item.show()
			
		self.cursor_Laurux.execute("""UPDATE Fiches_Parametres SET dncom = %s ;""", (self.laurux_commande,))

		
	def spider_opened(self, spider):
		self.logger.info('Promocash spider opened: %s', spider.name)
		self.montant_notfound = 0.0
		self.montant_found = 0.0
		
	def spider_closed(self, spider):
		self.logger.info('Promocash spider closed: %s', spider.name)
		print "////// %s ARTICLE NOT FOUND //////" % len(self.article_notfound)
		print self.article_notfound
		print "////// %s ARTICLE WITH NULL //////" % len(self.article_withnullqte)
		print self.article_withnullqte
		print "////// %s ARTICLE FOUND //////" % len(self.article_found)
		print self.article_found
		print "------------------------------"
		print "Montant HT not found: %s" % self.montant_notfound
		print "Montant HT found: %s" % self.montant_found
		print "///////////////////////"
		try:
			self.cursor.close()
			self.conn.close()
			self.cursor_Laurux.close()
			self.conn_Laurux.close()
		except:
			print "failure during close connection"



