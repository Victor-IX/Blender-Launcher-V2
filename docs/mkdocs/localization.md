# Localizing Blender Launcher

Blender Launcher supports localization, allowing the application to reflect your computer's language settings. This includes the translation of settings, error messages, and other UI elements into your preferred language. In instances where a specific translation is unavailable, English will be used as the default language.

**We welcome contributions to expand our translation efforts!** For details on how to contribute, please refer to the [Contributing Translations](localization.md#Contributing Translations) section.

## How to change your language:

=== "Windows"

    Navigate to **Settings > Time & language > Language & region**. Under "Windows display language," select or install the desired language, then sign out to apply the changes.

=== "Linux"

    For common desktop environments, language settings are typically available within the system settings. Alternatively, you can update your locale using `localectl` or by setting the `LANG` environment variable.

    Example for `fr_FR` locale:

    ```bash
    # Generate locale data if not already present
    # (modification of `/etc/locale.gen` may also be required):
    sudo locale-gen fr_FR
    sudo locale-gen fr_FR.UTF-8

    localectl set-locale fr_FR.UTF-8

    # Alternatively, set the LANG environment variable before running Blender Launcher V2,
    # or add it to your shell configuration file:

    export LANG=fr_FR.UTF-8
    ```

=== "MacOS"

    Access **System Settings > General > Language & Region** to modify the primary language.

    If these steps are insufficient, consider applying the Linux command-line instructions.

## Contributing Translations

We highly encourage pull requests that introduce new language support for Blender Launcher V2! This section outlines our translation workflow and guides you through adding new languages.

### Adding a language

For everything in the UI you want to change, there's a respective string in our localization folder.

To add a new language, duplicate an existing translation file, update the language tag in its filename, and then translate the content. It is recommended to copy an existing file rather than creating a new one from scratch to maintain consistent key ordering across versions, which simplifies future updates.

It is crucial that the **translation keys remain unchanged**. Inconsistent keys will prevent the program from retrieving the correct translations, resulting in English text being displayed by default.

### How they are used in the code

Blender Launcher utilizes YAML files for translations, located in `source/resources/localization/`. The file naming convention is `<namespace>.<language>.yml`. The `namespace` serves as the primary identifier when referencing translations in the code, followed by the `language` tag, and the `.yml` file extension.

For example, a (possibly out-of-date) snippet of the `wizard.en.yml` file, and its respective usage in the program's onboarding setup:

```yaml

...
appearance:
    title: Blender Launcher appearance
    subtitle: Configure how Blender Launcher Looks

    titlebar: Use System Titlebar
    titlebar_label: This disables the custom title bar and ...
    titlebar_label_linux: This disables the custom title bar and ...

    dpi_scaling: This changes the DPI factor of the program. ...
...
```

```py
class AppearancePage(BasicOnboardingPage):
    def __init__(self, prop_settings: PropogatedSettings, parent: BlenderLauncher):
        super().__init__(prop_settings, parent=parent)
        self.setTitle(t("wizard.appearance.title"))
        self.setSubTitle(t("wizard.appearance.subtitle"))
        self.layout_ = QVBoxLayout(self)
        self.titlebar = QCheckBox(t("wizard.appearance.titlebar"), self)
        ...
        if get_platform() == "Linux":
            titlebar_label = QLabel(t("wizard.appearance.titlebar_label_linux"), self)
        else:
            titlebar_label = QLabel(t("wizard.appearance.titlebar_label"), self)
        self.dpi_scale_factor = QDoubleSpinBox(self)
        ...
        if DPI_OVERRIDDEN:
            label = "settings.appearance.dpi_scale_factor_overridden"
            self.dpi_scale_factor.setEnabled(False)
        else:
            label = "settings.appearance.dpi_scale_factor"
        self.dpi_scale_label = QLabel(t(label))
        dpi_scale_desc = QLabel(t("wizard.appearance.dpi_scaling"), self)
```

### Minor Conventions

To ensure consistency, please adhere to these conventions when contributing translations:

*   **Strings with Colons**: YAML syntax interprets a colon (`:`) as a key-value separator. Therefore, any string containing a colon that is part of the translatable text (and not a key itself) **must be enclosed in double quotes** to prevent parsing errors. For example:
    ```yaml
    example_string: "Time: 10:30 AM"
    another_example: "Item description: A very useful tool."
    ```
    If a string doesn't require a colon, it doesn't need and shouldn't have surrounding quotes.
*   **Multiline Strings**: When handling multiline strings, using the YAML multiline block scalar style should always be preferred over one line with newline `\n` characters. The block scalar style is typically indicated by `|` for a literal block or `>` for a folded block. This allows for clear formatting of longer descriptions. For example:
    ```yaml
    paragraph: |
        I'm a paragraph!
        I span several lines because I need to stay readable and consistent.
    ```
    Tooltips should also be placed right under their respective key if they are related.
    ```yaml
    key: Some string in our program
    key_tooltip: |
        This is a multiline tooltip explaining something.
        It can span several lines for detailed information.
    ```
    



### Locale file capabilities

Translations are managed using the `python-i18n` library, which provides features such as templating and pluralization. Templating enables the dynamic insertion of program-specific strings into translations, and pluralization allows different strings to be used depending on a `count`.

#### Templating:

Variables are enclosed in curly braces with a `%` at the start, e.g., `%{name}`.

```yaml
greeting: "Hello, %{name}! Welcome to Blender Launcher."
total_items: "You have %{item_count} items in your cart."
```

```py
print(t('example.greeting', name='Alice'))
print(t('example.total_items', item_count=3))
print(t('example.total_items', item_count=0))
print(t('example.total_items', item_count=1))

```

Output:

```
Hello, Alice! Welcome to Blender Launcher.
You have 3 items in your cart.
You have 0 items in your cart.
You have 1 items in your cart.
```

#### Pluralization:

In a plural scenario, `count` is the special keyword argument. Of course, `count` can be used as a normal argument, but if `many`, `one`, or `zero` are included as subkeys, they will be referenced instead.

```yaml
files_downloaded:
    zero: No files downloaded yet.
    one: 1 file downloaded.
    many: "%{count} files downloaded."
```

```py
print(t('example.files_downloaded', count=0))
for count, file in enumerate(list_of_downloads, start=1):
    download(file)
    print(t('example.files_downloaded', count=count))
```

Output:

```
No files downloaded yet.
1 file downloaded.
2 files downloaded.
3 files downloaded.
```
