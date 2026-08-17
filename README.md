# Roblox Avatar Rotator - MacOS native version
A lightweight system tray application that automatically rotates your Roblox avatar between preset outfits, to create the effect that your avatar changes every time you reload.

## Features
* **Stays in the background:** Runs silently in the system tray.
* **Easy use:** You can create outfits in the Roblox avatar creator to cycle through.
* **Custom Intervals:** You can set the rotation speed.
* **Minimal Resources:** Uses less than 40MB of RAM and virtually 0% CPU (could be optimized but I wrote ts in python).
* **Logging:** Built in logging for troubleshooting API requests.

---
## Installation
Choose one of the following methods to install and run the application.

### Run as Python Script (Developer) (Recommended)
1. Install [Python]([https://www.python.org/downloads/](https://docs.brew.sh/Language-Runtimes-and-Packages#python)).
2. Clone or download this repository.
3. Open a terminal in the `src` folder.
4. Install dependencies:
```bash
pip install -r requirements.txt

```
5. Run the script:
```bash
pythonw main.pyw

```



## Usage

1. **Run the script** You will see a red dot at the top bar with your time and battery
2. **Open settings** Click it then press settings
3. **Set it** Input your `.ROBLOSECURITY` cookie and click Fetch outfits, you will have to wait for it to fetch.
4. **Run it** Now you have selected your outfits you could resize the window if you cant see Save and Close. Once you press it. click the red dot at the top bar again and press Start.
5. **All done!** Once you are done, click End Program or shut down as usual. You can set it to autostart too.

## Security Warning
>[!WARNING]
>This application requires your `.ROBLOSECURITY` cookie to function. This cookie grants full access to your Roblox account.
>* **Never** share your cookie with anyone.
>* This application stores your configuration locally in a `config.json` file on your computer, so do NOT open this file when others can see your screen.
>* The source code is provided in this repository for full transparency. You are encouraged to review `src/main.pyw` to ensure it is safe before use.
>* We do not use your cookie for any malicious use. Review `src/main.pyw`/`src/main.py` for proof.
