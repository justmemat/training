# OSF Training App

## Windows setup

Open Command Prompt in the application directory and install the required packages
with the same Python interpreter used to run the application:

```bat
python -m pip install -r requirements.txt
```

Then start the application:

```bat
python main.py
```

If `python` is not recognized, use the Windows Python launcher instead:

```bat
py -m pip install -r requirements.txt
py main.py
```

The PDF-generation feature requires `pypdf`. Installing `requirements.txt` installs
both Flet and pypdf and is preferred over installing packages one at a time.

The application targets Flet 0.80.0 and uses its current routing and asynchronous
file-picker APIs. If another Flet version is installed, restore the matching Flet
and Flet Desktop packages and restart the app from the same application directory:

```bat
python -m pip uninstall -y flet flet-desktop
python -m pip install -r requirements.txt
python main.py
```

You can confirm the active version with:

```bat
python -m pip show flet
```

Application JSON data is stored in separate feature files under:

```text
T:\BAE\Training\Onboarding\Masters\App\Assets
```
