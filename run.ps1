& ./.venv/Scripts/python.exe ./build_style.py
if ($args -contains "-debug") {
    & ./.venv/Scripts/python.exe ./source/main.py -debug
} else {
    & ./.venv/Scripts/python.exe ./source/main.py
}