[app]

# (str) Title of your application
title = GestionFondosM

# (str) Application versioning (should be a string)
version = 0.1.0

# (str) Package name
package.name = gestionfondos

# (str) Package domain (needed for Android package name)
package.domain = org.gestionfondos

# (str) Source code where the main.py live
source.dir = src

# (str) The entry point of the application
# OJO: esto es relativo a source.dir
entrypoint = gf_mobile/main.py

# (list) Application requirements
requirements = python3,kivy,kivymd,sqlalchemy,aiohttp,requests,pydantic<2,python-dateutil,cryptography,google-auth,google-auth-oauthlib

# (list) Permissions
android.permissions = INTERNET

# (str) Supported orientation (one of landscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# -------------------------
# ANDROID (IMPORTANTE)
# -------------------------

# (int) Target Android API
android.api = 34

# (int) Minimum API your APK will support
android.minapi = 23

# (str) Pin exact build-tools to prevent sdkmanager picking a newer one (e.g., 36.1.x)
android.sdk_build_tools = 34.0.0

# (bool) Accept SDK licenses automatically (important in CI / runners)
android.accept_sdk_license = True

# (str) Android NDK version to use
# NDK 25b te está dando problemas de macros; 23b suele ser más estable con p4a/buildozer.
android.ndk = 23b

# Workaround: define __GNUC_PREREQ macro if headers/toolchain don't provide it
android.cflags = -D__GNUC_PREREQ(x,y)=0


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2
