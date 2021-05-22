#  CoWIN Auto Booking Slot ( Updated on 22/05/2021 )

Auto Slot Booking when there is a vaccine slot available at your location, by running a script on your phone. 

[Group in Telegram](https://t.me/CoWIN_Termux)
![](https://gist.githubusercontent.com/m8rge/4c2b36369c9f936c02ee883ca8ec89f1/raw/c03fd44ee2b63d7a2a195ff44e9bb071e87b4a40/telegram-single-path-24px.svg)

  # Demo Video
  https://user-images.githubusercontent.com/45506201/118438178-8b02d100-b701-11eb-873c-8521def5b1a0.mp4

  ## Getting Started
  By using Tremux you can run script and recieve the notification on your phone.
  - ### Setting Up Termux

    - Install Termux App  [Link](https://play.google.com/store/apps/details?id=com.termux&hl=en_IN&gl=US).

    - Install Termux:API ( Required v 0.31 to read SMS ) [Apkpure Link](https://m.apkpure.com/termux-api/com.termux.api/download/31-APK).
 - ### Installing Packages and Requirements

   - Step 1 : ( Install git and Clone repo )

         pkg install git && git clone https://github.com/truroshan/cowin-termux.git
        
   - Step 2 : Open Cloned Folder and run install.sh 
        
         cd cowin-termux && bash install.sh


## Running Main Script for CoWin Booking

Command for script :

    python cowin.py --m <MOBILE-NO> --p <PIN-CODE> --a <YOUR-AGE> --t <INTERVAL-SECOND> --d <DOSE-COUNT> --fast
    
    python cowin.py --m 9966996699 --p 110011 --a 45 --t 1 --d 1 --fast
    
Required values like mentioned below

  - Replace `--m = MOBILE-NO` with your mobile no.
  - Replace `--p = PIN-CODE` with your pincode.

Optional arguments accepted:

  - Pass `--a = YOUR-AGE ` with your age (default is 18).
  - Pass `--d = DOSE_COUNT` Vaccine First Dose or Second Dose (default dose is 1).
  - Pass `--t = INTERVAL-IN-SECOND` to change the frequency of calling Cowin API  (default is 30 sec).
  - Only Pass `--fast` for direct booking no scheduling.
