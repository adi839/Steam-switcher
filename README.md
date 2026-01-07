Steam Account Switcher — Pro Edition :rocket:

A professional, feature-rich desktop application designed to manage and switch between multiple Steam accounts effortlessly. Created by _gabyro.

:star2: Key Features

Smart Account Switching: Switch between accounts with one click. The app automatically handles Steam processes and registry updates for a seamless login.

Advanced Ban Detection: Real-time monitoring for:

VAC BANS

GAME BANS 

COMMUNITY BANS

TRADE BANS

Automatic Data Fetching: Automatically retrieves profile avatars and your top 3 most played games (including free-to-play titles) using Steam API or public XML fallback.

Web-Based Games List: View your full library of games in a professionally styled HTML page directly in your browser.

Secure Password Generator: Generate high-entropy 16-character passwords to secure your accounts.

Collapsible Categories: Organize your accounts into groups (Main, Smurf, Storage, etc.) and collapse them to keep your workspace clean.

Live Search: Filter through your account list instantly by name or username.

Steam Guard Support: Special verification flow that waits for mobile app approval.

System Tray Integration: Minimize the app to the taskbar notification area (System Tray) to keep it running in the background.

Auto-Refresh: Account data (bans, avatars, games) updates automatically every 7 days.

Privacy Detection: Detects if your profile or game details are set to Private.

:tools: Setup

Install dependencies:
Make sure you have Python installed, then run:

pip install customtkinter requests Pillow pystray


Run the application:

python steam_switcher.py


:book: How to Use

Add Account: Fill in your Steam credentials.

SteamID64 & API Key: Click the :tv: icons next to the input fields for video tutorials on how to find these values.

Note: API Key is required for game lists, but avatars/VAC status can work via public XML fallback.

Verification: When saving, the app will briefly launch Steam to ensure the credentials are correct. If you have Steam Guard, approve it on your phone during this step.

Login: Just hit LOGIN NOW on any account card to switch instantly.

:broom: Automatic Cleanup

The app is designed to stay clean. Every time it starts, it automatically deletes any temporary HTML files from your system's TEMP folder that are older than 24 hours.

:shield: Disclaimer

This tool is intended for personal use. While it uses standard Steam command-line arguments and registry keys, always ensure your account details are kept secure. The author is not responsible for any issues arising from the use of this software.

Created with :heart: by _gabyro
