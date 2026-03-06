:: check if we need to move back to the root of the project folder
for %%I in (.) do set CurrentDir=%%~nxI
if %CurrentDir%==scripts cd ..

cd docs
mkdocs serve --livereload