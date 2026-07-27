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

The application currently targets Flet 0.28.3. Newer Flet releases changed the
routing and file-picker APIs used by this application. If another Flet version is
installed, restore the compatible version and restart the app from the same
application directory:

```bat
python -m pip install --force-reinstall -r requirements.txt
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
