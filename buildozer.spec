[app]

# (str) Title of your application
title = GestionFondosM

# (str) Package name
package.name = gestionfondos

# (str) Package domain (needed for Android package name)
package.domain = org.gestionfondos

# (str) Source code where the main.py live
source.dir = src

# (str) The entry point of the application
entrypoint = gf_mobile/main.py

# (list) Application requirements
requirements = python3,kivy,kivymd,sqlalchemy,aiohttp,requests,pydantic,python-dateutil,cryptography,keyring,google-auth,google-auth-oauthlib

# (list) Permissions
android.permissions = INTERNET

# (str) Supported orientation (one of landscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (int) Target Android API, leave empty for default
# android.api = 33

# (int) Minimum API your APK will support
# android.minapi = 23

# (int) Android SDK version to use
# android.sdk = 33

# (str) Android NDK version to use
# android.ndk = 25b

# (bool) Use --private data directory for assets
# android.private_storage = True

# (str) Fix the build process to allow pygame support
# android.p4a_dir =

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# (str) Path to buildozer cache directory
# build_dir = .buildozer
