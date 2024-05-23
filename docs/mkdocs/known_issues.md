# Known Issues

## Windows Time Zone

**Error Message:**
:   `[ERROR]: unknown locale: en_001`

**Behavior:** 
:   After the extraction of a build, the progress bar will be stuck at 100%.

**Cause:** 
:   This error will appear on Windows if your Time Zone is set to English World.

**Workaround:**
:   Set the time zone to something else.