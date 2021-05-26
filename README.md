#  CoWIN Auto Booking Slot (24/05/2021 )

Auto Slot Booking when there is a vaccine slot available at your location, by running a script on your phone. 

[Group in Telegram](https://t.me/CoWIN_Termux)
![](https://gist.githubusercontent.com/m8rge/4c2b36369c9f936c02ee883ca8ec89f1/raw/c03fd44ee2b63d7a2a195ff44e9bb071e87b4a40/telegram-single-path-24px.svg)

  # Demo Video
  https://user-images.githubusercontent.com/45506201/118438178-8b02d100-b701-11eb-873c-8521def5b1a0.mp4

  ## Getting Started
  By using Tremux you can run script and recieve the notification on your phone.
  - ### Install Termux

    - Install Termux App  [Playstore](https://play.google.com/store/apps/details?id=com.termux&hl=en_IN&gl=US).

    
 - ### Installing Packages and Requirements

   - Step 1 : Install git

         pkg install git

   - Step 2 : Clone repo 

         git clone https://github.com/truroshan/cowin-termux.git
        
   - Step 3 : Open Cloned Folder
        
         cd cowin-termux

   - Step 4: run install.sh 
         
         bash install.sh
  - ### OTP Fetching Methods
      // Three Options //
    - AutoMode (`a`) : Fetch OTP using Termux:API App 
      - Install Termux:API ( Required v 0.31 to read SMS ) [Apkpure Link](https://m.apkpure.com/termux-api/com.termux.api/download/31-APK).
          
    - SiteMode (`s`) :  Fetch OTP from Database Hosted on Cloudflare Worker
      - setup Database on [Cloudflare.](https://github.com/truroshan/CloudflareCoWinDB)
      - Install Automatically forward SMS to your PC/phone App. [Playstore](https://play.google.com/store/apps/details?id=com.gawk.smsforwarder)
    - ManualMode (`m`) : Input method

## Running Main Script for CoWin Booking

Command for script :

    python cowin.py --m <MOBILE-NO> --p <PIN-CODE> 
    
    python cowin.py --m 9966996699 --p 110011 
    
### :warning: Required values like mentioned below:

  - Replace `--m = MOBILE-NO` with your mobile no.
  - Replace `--p = PIN-CODE or DISTRICT-ID` with your Pincode or District Id.

### :bulb: Optional arguments accepted:
  - Pass `--o` = OTP fetching mode.`a` = AutoMode `s` = SiteMode `m` = ManualMode
    ( deault AutoMode )
  - Pass `--a = YOUR-AGE ` with your age (default is 18).
  - Pass `--d = DOSE_COUNT` Vaccine First Dose or Second Dose (default dose is 1).
  - Pass `--t = INTERVAL-IN-SECOND` to change the frequency of calling Cowin API  (default is 30 sec).
