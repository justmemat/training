# ATLAS

Assessment, Training, Logging, and Analytics System

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

The application targets Flet 0.86.3 and uses its current routing and asynchronous
file-picker APIs. All installed Flet components must use the same version. Remove
older CLI, web, and desktop components before reinstalling from this application
directory:

```bat
python -m pip uninstall -y flet flet-cli flet-desktop flet-web
python -m pip install --no-cache-dir -r requirements.txt
python main.py
```

The landing view is rendered immediately at startup rather than waiting for a
client-side route-change notification. This is important when the desktop client
already starts at `/`, because pushing the same route does not guarantee another
route-change event.

## Packaging for Windows

Place the application icon at `assets/icon.ico`, then run the pack command from
the directory containing `main.py`:

```bat
flet pack main.py -i assets/icon.ico -n ATLAS --add-data "assets; assets" --file-version 1.2.1
```

The application resolves the assets directory both beside the Python sources
and inside PyInstaller's temporary bundle directory, so the packaged icon and
other bundled assets remain available at runtime.

You can confirm the active version with:

```bat
python -m pip show flet flet-desktop
```

Application JSON data is stored in separate feature files under:

```text
T:\BAE\Training\Onboarding\Masters\App\Assets
```
