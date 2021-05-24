from apscheduler.schedulers.blocking import BlockingScheduler
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from datetime import datetime
import subprocess
import requests
import hashlib
import base64
import time
import json
import fire
import sys
import re
import os


OTP_SITE_URL = None
''' 
Add Worker Domain here example : https://db.domain.workers.dev
Check this :  https://github.com/truroshan/CloudflareCoWinDB
'''
ua = UserAgent()
scheduler = BlockingScheduler()

def line_break(): print("-"*25)

def clear_screen(): os.system("clear")

class CoWinBook():

    def __init__(self,mobile_no,pincode,age,dose,otp):
        self.mobile_no = str(mobile_no)
        self.pincode = pincode # Area Pincode
        self.center_id = []  # Selected Vaccination Centers
        self.user_id = []  # Selected Users for Vaccination 

        # Vaccination Center id and Session id for Slot Booking
        self.vacc_center = None
        self.vacc_session = None
        self.slot_time = None

        # Dose 1 or Dose 2 ( default : 1)
        self.dose = dose

        # OTP Fetching method 
        self.otp = otp

        # User Age 18 or 45
        self.age =  age

        # Request Session
        self.session =  requests.Session() 

        # Data for sending request
        self.data = {} 

        # Token Recieved from CoWIN
        self.bearerToken = None  # Session Token

        self.todayDate = datetime.now().strftime("%d-%m-%Y")
      
        # Login and Save Token in file( filename same as mobile no)
        self.getSession()

        # Selecting Center and User
        self.setup_details()

    # Set Header in self.session = requests.Session()
    def set_headers(self):
        self.session.headers.update({
            'User-Agent': ua.random,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/json',
            'Origin': 'https://selfregistration.cowin.gov.in',
            'Connection': 'keep-alive',
            'Referer': 'https://selfregistration.cowin.gov.in/',
            'TE': 'Trailers',
        })

    # returning self.data 
    def get_data(self):
        return json.dumps(self.data).encode('utf-8')

    # Save Token after login to CoWIN
    def putSession(self):
        with open(self.mobile_no, "w") as f:
            f.write(self.bearerToken)

    # Get Token saved in file for relogin and use
    def getSession(self):
        self.set_headers()
        try:
            with open(self.mobile_no, "r") as f:
                self.bearerToken = f.read()
            self.session.headers.update({
                    'Authorization': 'Bearer {}'.format(self.bearerToken)
                })
            self.session.get('https://cdn-api.co-vin.in/api/v2/appointment/beneficiaries').json()
        except (FileNotFoundError,json.decoder.JSONDecodeError):
            self.login_cowin()
            

    # Login to selfregistration.cowin.gov.in/
    def login_cowin(self):

        self.data = {
        "secret":"U2FsdGVkX1+gGN13ULaCVtLSWmsyZwAdXXTIAvLQp2HOXrIBCcq0yyOZQqzzfiFiEYs7KoAOTK2j4qPF/sEVww==",
        "mobile": self.mobile_no
            }

        response = self.session.post('https://cdn-api.co-vin.in/api/v2/auth/generateMobileOTP',data=self.get_data())

        otpSha265 = self.get_otp()

        txn_id = response.json()['txnId']

        self.data = {
                        "otp":otpSha265,
                        "txnId": txn_id
                                    }
        
        response = self.session.post('https://cdn-api.co-vin.in/api/v2/auth/validateMobileOtp',data=self.get_data())
        
        self.bearerToken = response.json()['token']

        self.session.headers.update({
            'Authorization': 'Bearer {}'.format(self.bearerToken)
        })
        self.putSession() 

    # Request for OTP 
    def get_otp(self):
        
        otp_fetching_mode = ""
        if self.otp == 'a':
            otp_fetching_mode = 'AutoMode'
        if self.otp == 's':
            otp_fetching_mode = 'SiteMode'
        else:
            otp_fetching_mode = "ManualMode"

        print(f"OTP Sent ({otp_fetching_mode}) 📲 ... ")

        otp = ""

        try:    
            curr_msg = self.get_msg().get("body")

            for i in reversed(range(15)):
            
                last_msg = self.get_msg().get("body",'')
            
                print(f'Waiting for OTP {i} sec')
                sys.stdout.write("\033[F")

                if curr_msg != last_msg and "cowin" in last_msg.lower():
                    otp = re.findall("(\d{6})",last_msg)[0]
                    print("\nOTP Recieved : ",otp)
                    break

                time.sleep(3)
        except Exception as e:
            print(e)
       
        if not otp: otp = input("\nEnter OTP : ")

        return hashlib.sha256(otp.encode('utf-8')).hexdigest()

    # Get Mobile last msg for otp Checking  
    def get_msg(self):
        msg = {}

        # Get OTP using Termux:API v0.31 
        if self.otp == 'a':
            msg = subprocess.Popen(
                                '   ',
                                stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,shell=True).communicate()[0].decode('utf-8')

            try:
                if msg != '':
                    msg = json.loads(msg)[0]
                    return msg
            finally:
                raise Exception("Install Termux:API v0.31")
        
        # Get OTP using DB hosted on Cloudflare and Attached with https://play.google.com/store/apps/details?id=com.gawk.smsforwarder
        elif self.otp == 's':

            if OTP_SITE_URL is None:
                raise Exception("First Setup DB on Cloudflare \nhttps://github.com/truroshan/CloudflareCoWinDB ")

            res = requests.get(f"{OTP_SITE_URL}/{self.mobile_no}",timeout=3).json()
                
            if res.get("status"):
                msg['body'] = res.get('data').get("message")
                requests.delete(f"{OTP_SITE_URL}/{self.mobile_no}")
            return msg

        # Lastly enter OTP Manually
        raise Exception
        
    # Request for Current Slot Deatails ( Private Request )
    def request_slot(self):
        todayDate = datetime.now().strftime("%d-%m-%Y")
        response = self.session.get(f'https://cdn-api.co-vin.in/api/v2/appointment/sessions/calendarByPin?pincode={self.pincode}&date={todayDate}')

        if response.ok:
            self.check_slot(response.json())
        elif response.status_code == 401:
            print("Re-login Account : " + datetime.now().strftime("%H:%M:%S") + " 🤳")
            self.login_cowin()
            self.request_slot()

    # Check Slot availability 
    def check_slot(self,response):

        for center in response.get('centers',[]):
            
            for session in center.get('sessions')[1:]:  # Starting from Next Day
                
                self.vacc_center = center.get('center_id')
                self.vacc_session = session.get("session_id")
                self.slot_time = session.get('slots')[0]

                center_name = center.get('name')
                capacity = session.get('available_capacity')
                session_date = session.get('date')
                
                vaccine_name = session.get('vaccine')

                if session.get('min_age_limit') == self.age and capacity > 1 and center.get('center_id') in  self.center_id:
                    MSG = f'💉 {capacity} #{vaccine_name} / {session_date} / {center_name} 📍{self.pincode}'

                    # Send Notification via Termux:API App
                    os.system(f"termux-notification --content '{MSG}'")
                
                    BOOKED = self.book_slot()
                    if BOOKED:
                        scheduler.shutdown(wait=False)
                        print("Shutting Down CoWin Script 👩‍💻 ")
                        return

        # When last Checked
        print("Last Checked  ✅ : " + datetime.now().strftime("%H:%M:%S") + " 🕐")
        sys.stdout.write("\033[F")

    # Get Solved Captcha in String
    def get_captcha(self):

        model = "eyJNTExRTExRTExRTExMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTExRTExRWk1MTFFMTFFMTFFMTFFaIjogIjAiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTFoiOiAiMSIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExMUUxMTFFMTFFaIjogIjIiLCAiTUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTExMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExMUUxMUUxMUUxMUUxMUUxMUUxMTExRTExRTExRTExRTExRTExRTExMTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiMyIsICJNTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRWk1MTFFMTExRTExRTExRTExRTExRTExRTExMUUxMTFFMTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRWiI6ICI0IiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMTExMUUxMTFFMTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTExRTExRTExRTExRTExRWiI6ICI1IiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogIjYiLCAiTUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRTExRTExMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFaTUxMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMTExRTExRTExRTExRTExRTExMUUxMTFFMTFFMTFFMTExRWiI6ICI3IiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExMUUxMUUxMUUxMUUxMTExMUUxMUUxMUUxMUUxMTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExMUUxMUUxMUUxMUUxMUUxMUVoiOiAiOCIsICJNTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogIjkiLCAiTUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUVpNTExMUUxMUUxMUUxMUUxMUUxMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTExRWiI6ICJBIiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUVpNTExRTExRTExRTExRTExMUUxMUUxMUUxMUVpNTExMUUxMTExMUUxMTFFMTFFMTFFMTFFMTFFMTFFaIjogIkIiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiQyIsICJNTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogIkQiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogIkUiLCAiTUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUVoiOiAiRiIsICJNTExRTExRTExRTExMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMWiI6ICJHIiwgIk1MTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWiI6ICJIIiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAibCIsICJNTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWiI6ICJKIiwgIk1MTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMTExMUVpNTExRTExRTExRTExMUUxMUUxMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWiI6ICJLIiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiTCIsICJNTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRWiI6ICJNIiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMWk1MTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiTiIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExRWiI6ICJPIiwgIk1MTFFMTFFMTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFaIjogIlAiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTExRTExMUUxMUUxMUUxMUUxMUVpNTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTExMTFFMTFFMTFFaIjogIlEiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMTFFMTFFMTFFaTUxMTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFaTUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogIlIiLCAiTUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiUyIsICJNTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWiI6ICJUIiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogIlUiLCAiTUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogIlYiLCAiTUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiVyIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFaIjogIlgiLCAiTUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFoiOiAiWSIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMTFFMTFFMTFFMTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRWiI6ICJaIiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRWk1MTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogImEiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRWiI6ICJiIiwgIk1MTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExMUUxMUUxMUVoiOiAiYyIsICJNTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiZCIsICJNTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTExRWk1MTFFMTFFMTFFMTFFMTFFaTUxMUUxMTExRTExRTExRWiI6ICJlIiwgIk1MTFFMTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFaTUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRTExRTExMUUxMTExRTExRTExMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogImYiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMTFFMTExRTExRTExRTExMUUxMUUxMUUxMUUxMTExRTExRTExRTExRTExRTExMUUxMTFFMTFFMTExRTExMUVpNTExRTExRTExRTExRTExRTExRTExRTExRWiI6ICJnIiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExMUUxMUVoiOiAiaCIsICJNTExRTExMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTFpNTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUVpNTExMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogImkiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExMUUxMUUxMUUxMUUxMUUxMTFFMTExMUUxMUVpNTExMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiaiIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAiayIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTExRTExRWk1MTExaIjogIm0iLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAibiIsICJNTExRTExRTExRTExRTExRTExRTExRWk1MTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAibyIsICJNTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExMUUxMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMTExMUUxMTFFMTFFMTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxaTUxMUUxMUUxMUUxMUUxMTFFMTExRTExMUUxMUVoiOiAicCIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFaTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVoiOiAicSIsICJNTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExaTUxMTFoiOiAiciIsICJNTExMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMTExRTExRTExRTExMUUxMUVoiOiAicyIsICJNTExRTExRTExRTExRTExMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFaTUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTExRTExRTExRWiI6ICJ0IiwgIk1MTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMTExMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogInUiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTExRTExMUVoiOiAidiIsICJNTExRTExMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFMTFFMTFFMTFFMTExRWk1MTFFMTFFMTFFMTFFMTFFMTExRTExRTExRTExRTExMUUxMTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMWiI6ICJ3IiwgIk1MTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRWk1MTFFMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMTFFaIjogIngiLCAiTUxMUUxMUUxMUUxMUUxMUUxMUUxMUUxMTFFMTFFaTUxMUUxMTFFMTFFMTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMUVoiOiAieSIsICJNTExRTExRTExRTExRTExRTExRTExRTExMUUxMUUxMUUxMUUxMUUxMUVpNTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExRTExMUUxMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFMTFFaIjogInoifQ=="
        
        # Send request for Captcha    
        data = '{}'
        response = self.session.post('https://cdn-api.co-vin.in/api/v2/auth/getRecaptcha', data=data)

        if not response.ok:
            self.login_cowin()
            return self.get_captcha()

        # Get Captcha Data from Json
        svg_data = response.json()['captcha']


        soup = BeautifulSoup(svg_data,'html.parser')

        model = json.loads(base64.b64decode(model.encode('ascii')))
        CAPTCHA = {}

        for path in soup.find_all('path',{'fill' : re.compile("#")}):

            ENCODED_STRING = path.get('d').upper()
            INDEX = re.findall('M(\d+)',ENCODED_STRING)[0]

            ENCODED_STRING = re.findall("([A-Z])", ENCODED_STRING)
            ENCODED_STRING = "".join(ENCODED_STRING)

            CAPTCHA[int(INDEX)] =  model.get(ENCODED_STRING)

        CAPTCHA = sorted(CAPTCHA.items())
        CAPTCHA_STRING = ''

        for char in CAPTCHA:
            CAPTCHA_STRING += char[1]

        return CAPTCHA_STRING

    # Book Slot for Vaccination
    def book_slot(self):
        
        captcha = self.get_captcha()

        self.data = {
            "center_id":self.vacc_center ,
            "session_id":self.vacc_session,
            "beneficiaries":self.user_id,
            "slot":self.slot_time,
            "captcha": captcha,
            "dose": self.dose
            }

        response = self.session.post('https://cdn-api.co-vin.in/api/v2/appointment/schedule',data=self.get_data())

        status =  response.status_code
        
        if status == 200:
            print("🏥 Appointment scheduled successfully! 🥳 ")
            return True
        elif status == 409:
            print("This vaccination center is completely booked for the selected date 😥")
        elif status == 401:
            self.login_cowin()
            self.book_slot()
        else:
            print("Error in Booking Slot")
            print(f'{status} : {response.json()}')

    # Booking Method
    def book_now(self):
        self.request_slot()

    # Set details about Vaacination Center and User Id
    def setup_details(self):
        
        self.select_center()
        self.select_beneficiaries()

    # Select Center for Vaccination
    def select_center(self):

        response = self.session.get(
            'https://cdn-api.co-vin.in/api/v2/appointment/sessions/calendarByPin?pincode={}&date={}'.format(self.pincode,self.todayDate),
            ).json()

        CENTERS = {}
        INDEX_S = []

        print(f"Select Vaccination Center ({self.pincode}) 💉 \n")
        counter = 1
        for center in response.get('centers',[]):
            for session in center.get('sessions'):
                if session.get('min_age_limit') == self.age:
                    print(f'{counter} : {center.get("name")}')
                    CENTERS[counter] = center.get('center_id')
                    INDEX_S.append(counter)
                    counter += 1
                    break
            

        print()
        line_break()
        print("""
    * Select One Center
        input : 1
    * Select Mutiple with Space
        input : 1 2 3 4
    * Select All Center
        Hit Enter without Input\n""")

        line_break()

        input_index = input("Enter Index's : ")

        if input_index != '':
            INDEX_S = re.findall("(\d)",input_index)
            
        clear_screen()

        CENTER_ID = []
        for  index in INDEX_S:
            if CENTERS.get(int(index)):
                CENTER_ID.append(CENTERS.get(int(index)))
        self.center_id = CENTER_ID

    # Select User to Book Slot
    def select_beneficiaries(self):

        response = self.session.get('https://cdn-api.co-vin.in/api/v2/appointment/beneficiaries').json()

        USERS = {}
        INDEX_S = []

        print(f"Select User for Vaccination 👩‍👦‍👦 \n")

        if not response.get('beneficiaries',[]):
            print("No user added in beneficiaries")
            return

        counter = 1
        for user in response.get('beneficiaries'):
            if not user.get(f'dose{self.dose}_date'):
                print(f'{counter} : {user.get("name")}')
                USERS[counter] = user.get('beneficiary_reference_id')
                INDEX_S.append(counter)
                counter += 1

        print()
        line_break()
        print("""
    * Select One User
        input : 1
    * Select Mutiple User with Space
        input : 1 2 3 4
    * Select All User
        Hit Enter without Input\n""")

        line_break()

        input_index = input("Enter Index's : ")

        if input_index != '':
            INDEX_S = re.findall("(\d)",input_index)
            
        clear_screen()

        USER_ID = []
        for index in INDEX_S:
            if USERS.get(int(index)):
                USER_ID.append(USERS.get(int(index)))

        self.user_id = USER_ID

 
def main(mobile_no,pincode, age = 18,dose = 1,time = 30,otp = 'a'):

    # Correct Age
    age =  18 if age < 45 else 45

    # Max 30 Seconds
    time = 30 if time > 30 else time

    global cowin
    cowin = CoWinBook(mobile_no,pincode,age,dose,otp)

    scheduler.add_job(cowin.book_now, 'cron', second = f'*/{time}')
    print(f" 📍 {pincode} 💉 {age}+ ⌛️ {time} Seconds")


if __name__ == '__main__':

    clear_screen()

    fire.Fire(main)

    print("CoWin Auto Slot Booking 🔃\nfor Tomorrow and Day After 📆 ...")
    line_break()

    scheduler.start()

