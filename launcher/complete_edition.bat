@echo off
rem M2TW Complete Edition launcher - requires M2EX installed in the game root.
rem M2EX mod launching follows its own convention (see Americas.bat shipped with M2EX):
rem   M2EX.exe --features.mod=mods/<name>
rem The @cfg switch is the classic engine convention; M2EX claims OG-mod compatibility,
rem so we pass both. If M2EX rejects @cfg, remove it and set log/io options in
rem medieval2.preference.cfg instead.
cd /d "%~dp0"
if exist "M2EX.exe" (
    start "" "%~dp0M2EX.exe" --features.mod=mods/complete_edition @mods/complete_edition/complete_edition.cfg
) else (
    echo M2EX.exe not found - falling back to medieval2.exe [stock engine, 31-faction cap!]
    start "" "%~dp0medieval2.exe" @mods/complete_edition/complete_edition.cfg
)
